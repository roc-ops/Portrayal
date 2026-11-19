"""The plan outline cut against the section: what is left of the body, drawn and judged.

`plan_outline.py` reads `chassis.plan-outline` as bands of polygons; `section.py` reads the end
profile as rows of depth intervals. This module cuts the one against the other, in the top
face's frame (x along the width from the left, y down the drawing with the rear at the top, so a
section depth `sx` from the front is `y = depth - sx`), and is what the compiler and lint share.
kit/plan.js (a later order) is the same maths written again in JavaScript; both read
`spec/tests/fixtures/plan_outline/sweep-cases.json`, which holds the answers worked by hand.

THE SWEEP. Every region here is a union of polygons, and the maths is one x-sweep:

  1. The abscissae are the x of every vertex of every polygon taken in, plus the x where two of
     their edges cross. Between two consecutive abscissae no edge begins, ends or crosses another,
     so the edges that span the slab keep their order and every chord between a pair of them is a
     trapezoid, which is convex.
  2. THE MERGE RULE: the abscissae are sorted; the smallest is kept, and any value within
     MERGE (0.001 mm) of the last one kept is dropped, so a cluster is its smallest member. A
     sliver slab narrower than that is never built.
  3. In a slab each polygon gives the y intervals between its edges taken in pairs from the top.
     A group of polygons is the union of those intervals; the groups are then intersected (and, for
     the end faces, one is taken away from another).
  4. THE ROUNDING RULE: a coordinate is computed in floating point and written to 6 decimals.

A piece is `(xl, xr, lo_left, lo_right, hi_left, hi_right)`: the trapezoid between two
abscissae, `lo` the edge nearer the top of the drawing. As a polygon it is clockwise with y down,
starting at `(xl, lo_left)`, a point dropped where two coincide (a triangle).

THE SNAP. A plan vertex within SNAP (0.5 mm) of a side of the box, or of a wall of the section at
the band's own heights, is moved onto it before anything is cut, one coordinate at a time to the
nearest such line, so a measured run a few tenths inside a wall is the wall and no sliver is made.
"""
import math

from portrayal import plan_outline as _plan
from portrayal import section as _section

# millimetres
MERGE = 0.001
SNAP = 0.5
TOL = 0.01
DECIMALS = 6
_EPS = 1e-9


def _r(v):
    v = round(v, DECIMALS)
    return 0.0 if v == 0 else v


# --- the sweep -------------------------------------------------------------------------------

def merge_abscissae(xs):
    """The merge rule: sorted, the smallest of each cluster kept, a value within MERGE of the last
    one kept dropped."""
    out = []
    for x in sorted(xs):
        if not out or x - out[-1] > MERGE:
            out.append(x)
    return out


def _edges(polys):
    """The edges of the polygons that are not vertical, as `(x0, y0, x1, y1)` with `x0 < x1`."""
    out = []
    for poly in polys:
        n = len(poly)
        for i in range(n):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
            if abs(bx - ax) <= _EPS:
                continue
            out.append((ax, ay, bx, by) if ax < bx else (bx, by, ax, ay))
    return out


def _y(e, x):
    return e[1] + (e[3] - e[1]) * (x - e[0]) / (e[2] - e[0])


def _crossings(edges):
    """The x where two edges cross strictly inside both. The edges are walked in order of their
    left end, and an edge stops being compared once it ends before the next begins."""
    xs = []
    order = sorted(edges)
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            if b[0] >= a[2]:
                break
            ma, mb = (a[3] - a[1]) / (a[2] - a[0]), (b[3] - b[1]) / (b[2] - b[0])
            if abs(ma - mb) <= _EPS:
                continue            # parallel: they never cross, whether or not they coincide
            x = (b[1] - mb * b[0] - a[1] + ma * a[0]) / (ma - mb)
            if max(a[0], b[0]) + _EPS < x < min(a[2], b[2]) - _EPS:
                xs.append(x)
    return xs


def _chords(polygon_edges, xm):
    """The y intervals of one polygon at `xm`: its edges that span it, paired from the top.
    Each interval is `(lo_edge, hi_edge)`."""
    spans = sorted((e for e in polygon_edges if e[0] <= xm < e[2]), key=lambda e: _y(e, xm))
    return list(zip(spans[0::2], spans[1::2]))


def _union(intervals, xm):
    out = []
    for lo, hi in sorted(intervals, key=lambda iv: _y(iv[0], xm)):
        if out and _y(lo, xm) <= _y(out[-1][1], xm) + _EPS:
            if _y(hi, xm) > _y(out[-1][1], xm):
                out[-1] = (out[-1][0], hi)
        else:
            out.append((lo, hi))
    return out


def _meet(a, b, xm):
    out = []
    for lo_a, hi_a in a:
        for lo_b, hi_b in b:
            lo = lo_a if _y(lo_a, xm) >= _y(lo_b, xm) else lo_b
            hi = hi_a if _y(hi_a, xm) <= _y(hi_b, xm) else hi_b
            if _y(hi, xm) - _y(lo, xm) > _EPS:
                out.append((lo, hi))
    return out


def _minus(a, b, xm):
    out = []
    for lo, hi in a:
        cur = lo
        for lo_b, hi_b in b:
            if _y(hi_b, xm) <= _y(cur, xm) + _EPS or _y(lo_b, xm) >= _y(hi, xm) - _EPS:
                continue
            if _y(lo_b, xm) > _y(cur, xm) + _EPS:
                out.append((cur, lo_b))
            cur = hi_b if _y(hi_b, xm) > _y(cur, xm) else cur
        if _y(hi, xm) - _y(cur, xm) > _EPS:
            out.append((cur, hi))
    return out


def sweep(groups, minus=(), x_range=None):
    """The pieces of the region that lies in every group of `groups` and in none of `minus`.

    A group is a list of polygons (`[(x, y), ...]`) and stands for their union. `x_range`, a pair,
    keeps only the part of the region between those x. Returns the pieces, left to right."""
    every = [p for g in list(groups) + list(minus) for p in g]
    edges = _edges(every)
    if x_range is not None:
        lo, hi = x_range
        edges = [e for e in edges if e[2] > lo and e[0] < hi]
    xs = [e[0] for e in edges] + [e[2] for e in edges]
    for p in every:
        xs += [x for x, _y2 in p]
    xs += _crossings(edges)
    if x_range is not None:
        xs = [x for x in xs if x_range[0] < x < x_range[1]] + [x_range[0], x_range[1]]
    xs = merge_abscissae(xs)
    per_group = [[_edges([p]) for p in g] for g in groups]
    per_minus = [[_edges([p]) for p in g] for g in minus]
    pieces = []
    for xl, xr in zip(xs, xs[1:]):
        xm = (xl + xr) / 2.0
        region = None
        for g in per_group:
            iv = _union([c for pe in g for c in _chords(pe, xm)], xm)
            region = iv if region is None else _meet(region, iv, xm)
            if not region:
                break
        if not region:
            continue
        for g in per_minus:
            region = _minus(region, _union([c for pe in g for c in _chords(pe, xm)], xm), xm)
        for lo, hi in region:
            pieces.append((_r(xl), _r(xr), _r(_y(lo, xl)), _r(_y(lo, xr)),
                           _r(_y(hi, xl)), _r(_y(hi, xr))))
    return pieces


def polygon(piece):
    """A piece as a clockwise polygon, a point dropped where two coincide."""
    xl, xr, a, b, c, d = piece
    out = []
    for p in ((xl, a), (xr, b), (xr, d), (xl, c)):
        if not out or abs(out[-1][0] - p[0]) > _EPS or abs(out[-1][1] - p[1]) > _EPS:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) <= _EPS and abs(out[0][1] - out[-1][1]) <= _EPS:
        out.pop()
    return out


def area(piece):
    xl, xr, a, b, c, d = piece
    return (xr - xl) * ((c - a) + (d - b)) / 2.0


# --- the outline of a union ------------------------------------------------------------------

def gaps(a, b):
    """The intervals of `a` that `b` does not cover; both sorted lists of `(lo, hi)`."""
    out = []
    for lo, hi in a:
        cur = lo
        for lo_b, hi_b in b:
            if hi_b <= cur + _EPS or lo_b >= hi - _EPS:
                continue
            if lo_b > cur + _EPS:
                out.append((cur, lo_b))
            cur = max(cur, hi_b)
        if hi - cur > _EPS:
            out.append((cur, hi))
    return out


def _simplify(loop):
    """A point dropped where it lies on the straight run between its neighbours."""
    out = list(loop)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            ahead = (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])
            # b is off the line ac by cross / |ac|; coordinates are written to 6 decimals, so a
            # point on a straight run is off it by about a millionth
            if abs(cross) <= 1e-5 * math.hypot(c[0] - a[0], c[1] - a[1]) and ahead >= 0:
                del out[i]
                changed = True
                break
    return out


def _rotate(loop):
    """The loop starting at its smallest x, then smallest y, so one outline has one spelling."""
    i = min(range(len(loop)), key=lambda k: (loop[k][0], loop[k][1]))
    return loop[i:] + loop[:i]


def loops(pieces):
    """The boundary of the region the pieces of one sweep fill, as closed loops of `(x, y)`,
    clockwise with y down for an outer boundary and the other way round for a hole. The loops
    start at their smallest x, then y, carry no point on a straight run and are listed by their
    first point."""
    edges = []                               # (start, end) directed, interior on the right
    by_left, by_right = {}, {}
    for p in pieces:
        xl, xr, a, b, c, d = p
        edges.append(((xl, a), (xr, b)))
        edges.append(((xr, d), (xl, c)))
        by_left.setdefault(xl, []).append((a, c))
        by_right.setdefault(xr, []).append((b, d))
    for x in sorted(set(by_left) | set(by_right)):
        left = sorted(by_right.get(x, []))       # intervals of pieces ending at x
        right = sorted(by_left.get(x, []))       # intervals of pieces starting at x
        for lo, hi in gaps(left, right):
            edges.append(((x, lo), (x, hi)))      # a wall facing right: goes down
        for lo, hi in gaps(right, left):
            edges.append(((x, hi), (x, lo)))      # a wall facing left: goes up
    key = lambda pt: (round(pt[0], 5), round(pt[1], 5))
    starts = {}
    for e in edges:
        if key(e[0]) != key(e[1]):
            starts.setdefault(key(e[0]), []).append(e)
    used, out = set(), []
    for e in edges:
        if key(e[0]) == key(e[1]) or id(e) in used:
            continue
        loop, cur = [], e
        while cur is not None and id(cur) not in used:
            used.add(id(cur))
            loop.append(cur[0])
            nxt = [n for n in starts.get(key(cur[1]), []) if id(n) not in used]
            cur = nxt[0] if nxt else None
        if len(loop) >= 3:
            out.append(_rotate(_simplify([(_r(x), _r(y)) for x, y in loop])))
    return sorted(out)


def loop_area2(loop):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]))


def outer_loops(pieces):
    """The loops of `loops` that are outer boundaries (clockwise with y down): one for each
    connected piece of the region."""
    return [lp for lp in loops(pieces) if loop_area2(lp) > 0]


def union_loops(polys, clip=None):
    """The outline of the union of `polys` as loops (see `loops`), cut to the rectangle
    `clip = (x0, y0, x1, y1)` when given."""
    if not polys:
        return []
    if clip is None:
        return loops(sweep([polys]))
    x0, y0, x1, y1 = clip
    rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return loops(sweep([polys, [rect]], x_range=(x0, x1)))


def path_d(lps, mirror=None):
    """The loops as one SVG path. `mirror` is a width: x becomes `mirror - x` and each loop is
    wound the other way, so it stays clockwise."""
    parts = []
    for lp in lps:
        if mirror is not None:
            lp = [(mirror - x, y) for x, y in reversed(lp)]
        parts.append("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in lp) + " Z")
    return " ".join(parts)


def polyline_d(run, mirror=None):
    """An open run of points as an SVG path, x mirrored across a width where `mirror` is one."""
    return "M" + " L".join(f"{(mirror - x) if mirror is not None else x:.3f},{y:.3f}" for x, y in run)


# --- the snap --------------------------------------------------------------------------------

def _row_edges(section_pts, depth, lo, hi):
    """The y of the section's walls, in the plan's frame, over the heights `lo` to `hi`."""
    ys = set()
    for y0, y1, intervals in _section._bands(section_pts):
        if min(y1, hi) - max(y0, lo) > _EPS:
            for a, b in intervals:
                ys.update((depth - a, depth - b))
    return sorted(ys)


def snap_polygon(points, targets_x, targets_y):
    """The polygon with each coordinate moved onto the nearest target within SNAP, a point that
    repeats its neighbour then dropped. Returns `(points, snaps)`, a snap being
    `(index, axis, from, to)` for each move of more than TOL (the ones lint names)."""
    out, snaps = [], []
    for i, (x, y) in enumerate(points):
        new = []
        for axis, v, targets in (("x", x, targets_x), ("y", y, targets_y)):
            near = min(targets, key=lambda t: abs(t - v), default=None)
            if near is not None and abs(near - v) <= SNAP + _EPS:
                if abs(near - v) > TOL:
                    snaps.append((i, axis, v, near))
                v = near
            new.append(v)
        out.append(tuple(new))
    kept = [p for i, p in enumerate(out) if p != out[i - 1]]
    return kept, snaps


def snapped(plan, section_pts, width, depth):
    """`plan` (the bands of `plan_outline.bands`) with every polygon snapped. Returns
    `(bands, snaps)`, a snap being `(band, index, axis, from, to)`."""
    out, snaps = [], []
    for i, b in enumerate(plan):
        lo, hi = b["heights"]
        ty = sorted({0.0, float(depth), *_row_edges(section_pts, depth, lo, hi)})
        pts, found = snap_polygon(b["points"], [0.0, float(width)], ty)
        out.append({"heights": b["heights"], "points": pts})
        snaps += [(i, *s) for s in found]
    return out, snaps


# --- the body that is left -------------------------------------------------------------------

def rows(section_pts, depth):
    """The section's rows as `(y0, y1, [(lo, hi), ...])`: heights, and the depth intervals that
    are solid there in the plan's frame (`depth - sx`), top of the drawing first."""
    out = []
    for y0, y1, intervals in _section._bands(section_pts):
        out.append((y0, y1, sorted((depth - b, depth - a) for a, b in intervals)))
    return out


def _band_rows(band, rws, heights):
    """`[(h0, h1, intervals)]`: the rows a band covers, cut to its half-open heights."""
    lo, hi = heights
    out = []
    for y0, y1, iv in rws:
        a, b = max(lo, y0), min(hi, y1)
        if b - a > _EPS:
            out.append((a, b, iv))
    return out


def _rect_polys(intervals, width):
    return [[(0.0, a), (width, a), (width, b), (0.0, b)] for a, b in intervals]


def body(plan, section_pts, width, depth):
    """What the plan leaves of the section's body: for each band and each row it covers,
    `{"band", "heights": (h0, h1), "pieces": [...]}` where the pieces are the band's polygon cut
    to the row's depth intervals. `plan` is already snapped. A band's heights within TOL of a
    row's edge are taken to be on it."""
    rws = rows(section_pts, depth)
    edges = sorted({y for y0, y1, _ in rws for y in (y0, y1)})
    out = []
    for i, b in enumerate(plan):
        heights = tuple(min(edges, key=lambda e: abs(e - h)) if min(abs(e - h) for e in edges) <= TOL
                        else h for h in b["heights"])
        for h0, h1, iv in _band_rows(b, rws, heights):
            pieces = sweep([[b["points"]], _rect_polys(iv, width)])
            out.append({"band": i, "heights": (h0, h1), "intervals": iv, "pieces": pieces})
    return out




def pieces_in(solid, h0, h1):
    """The polygons of `body`'s pieces that lie in the heights `h0` to `h1`."""
    return [polygon(p) for s in solid if min(s["heights"][1], h1) - max(s["heights"][0], h0) > _EPS
            for p in s["pieces"]]


def reach(solid):
    """`(min x, max x, min y, max y)` of everything the body fills, None when it fills nothing."""
    ps = [p for s in solid for p in s["pieces"]]
    if not ps:
        return None
    return (min(p[0] for p in ps), max(p[1] for p in ps),
            min(min(p[2], p[3]) for p in ps), max(max(p[4], p[5]) for p in ps))


class Plan:
    """A chassis whose plan outline is well formed, cut once and read many ways."""

    def __init__(self, chassis):
        self.width = float(chassis["width"])
        self.height = float(chassis["height"])
        self.depth = float(chassis["depth"])
        self.section = _section.points(chassis)
        raw = _plan.bands(chassis)
        self.bands, self.snaps = snapped(raw, self.section, self.width, self.depth)
        self.solid = body(self.bands, self.section, self.width, self.depth)
        self.rows = rows(self.section, self.depth)

    # -- the top and bottom faces

    def outline(self):
        """The outline of the union of the bands' polygons, as loops in the top face's frame."""
        return union_loops([b["points"] for b in self.bands])

    def steps(self):
        """The lines where one band's polygon runs inside the union of the others: the step
        between bands, as `[((x0, y0), (x1, y1)), ...]` in the top face's frame. A stretch of a
        band's edge that is on the outline is not a step."""
        boundary = [seg for lp in self.outline() for seg in zip(lp, lp[1:] + lp[:1])]
        out = []
        for b in self.bands:
            pts = b["points"]
            for p, q in zip(pts, pts[1:] + pts[:1]):
                cuts = {0.0, 1.0}
                dx, dy = q[0] - p[0], q[1] - p[1]
                length2 = dx * dx + dy * dy
                for s0, s1 in boundary:
                    for v in (s0, s1):
                        t = ((v[0] - p[0]) * dx + (v[1] - p[1]) * dy) / length2
                        if 0 < t < 1 and _dist(v, p, q) < TOL:
                            cuts.add(t)
                ts = sorted(cuts)
                for t0, t1 in zip(ts, ts[1:]):
                    m = (p[0] + dx * (t0 + t1) / 2, p[1] + dy * (t0 + t1) / 2)
                    if all(_dist(m, s0, s1) > TOL for s0, s1 in boundary):
                        out.append(((_r(p[0] + dx * t0), _r(p[1] + dy * t0)),
                                    (_r(p[0] + dx * t1), _r(p[1] + dy * t1))))
        return _join(out)

    def stripe(self, rect, h0, h1):
        """The loops of a rib's stripe: the rectangle `(x0, y0, x1, y1)` of the top face cut to
        what the plan leaves of the body in the heights `h0` to `h1`, the pieces of every band
        seen from above joined into one region."""
        polys = pieces_in(self.solid, h0, h1)
        if not polys:
            return []
        return union_loops(polys, clip=rect)

    def level_holding(self, side, rect):
        """The height of the one surface on the top (`side` "top") or the bottom that holds the
        rectangle `(x0, y0, x1, y1)` of the top face wholly, or None. Seen from above the surface
        at a point is the highest the body has there, so each piece of the body is visible where
        no piece higher up covers it; a part stands on one such level and not across a step."""
        top = side == "top"
        order = sorted(self.solid, key=lambda s: s["heights"][0] if top else -s["heights"][1])
        seen = []
        for s in order:
            mine = [polygon(p) for p in s["pieces"]]
            if mine and covers(mine, rect, minus=seen):
                return s["heights"][0] if top else s["heights"][1]
            seen += mine
        return None

    # -- the front and rear

    def elevation(self, silhouette=None):
        """The outline of the front, in its frame (x from the left, y down), as loops: the
        silhouette of the fins (the whole box where there are none) cut to the x extent of the
        body at each row. Where a row's body has several runs of x, each stays: the union of
        their projections, not the hull."""
        h = self.height
        sil = silhouette or [(0.0, 0.0), (self.width, 0.0), (self.width, h), (0.0, h)]
        ys = {0.0, h} | {y for _, y in sil} | {y for s in self.solid for y in s["heights"]}
        ys = sorted(ys)
        rects = []
        for ya, yb in zip(ys, ys[1:]):
            if yb - ya <= _EPS:
                continue
            ym = (ya + yb) / 2.0
            runs = _intersect_runs(_runs_at(sil, ym), self._x_runs(min(max(ym, 0.0), h - _EPS)))
            rects += [[(a, ya), (b, ya), (b, yb), (a, yb)] for a, b in runs]
        return union_loops(rects) if rects else []

    def _x_runs(self, ym):
        spans = sorted((p[0], p[1]) for s in self.solid if s["heights"][0] <= ym < s["heights"][1]
                       for p in s["pieces"])
        out = []
        for a, b in spans:
            if out and a <= out[-1][1] + MERGE:
                out[-1] = (out[-1][0], max(out[-1][1], b))
            else:
                out.append((a, b))
        return out

    def wall_runs(self, which, h0, h1):
        """The runs of x where the wall the section has at the front or the rear (`which`) is
        there over every height from `h0` to `h1`: where the body reaches the wall's own line,
        not only near it. `[]` when a height has no wall."""
        runs = None
        for y0, y1, iv in self.rows:
            if min(y1, h1) - max(y0, h0) <= TOL or not iv:
                continue
            line = iv[-1][1] if which == "front" else iv[0][0]
            here = []
            for s in self.solid:
                if min(s["heights"][1], y1) - max(s["heights"][0], y0) <= _EPS:
                    continue
                for xl, xr, a, b, c, d in s["pieces"]:
                    edge = (c, d) if which == "front" else (a, b)
                    if abs(edge[0] - line) <= TOL and abs(edge[1] - line) <= TOL:
                        here.append((xl, xr))
            here = _merge_runs(here)
            runs = here if runs is None else _intersect_runs(runs, here)
        return runs or []

    # -- the end faces

    def cap(self, end):
        """The cap at the left end (`end` 0) or the right end: the rectangles
        `(y0, y1, lo, hi)` of the heights and plan y where the body has a wall on that end."""
        x = 0.0 if end == "left" else self.width
        out = []
        for s in self.solid:
            for xl, xr, a, b, c, d in s["pieces"]:
                lo, hi = (a, c) if end == "left" and abs(xl - x) <= TOL else (b, d) \
                    if end == "right" and abs(xr - x) <= TOL else (None, None)
                if lo is not None and hi - lo > TOL:
                    out.append((s["heights"][0], s["heights"][1], lo, hi))
        return out

    def cap_polygons(self, face):
        """The cap of an end face as rectangles in that face's frame (x across the depth from
        its left edge, y down the height)."""
        end = "left" if face == "left" else "right"
        out = []
        for y0, y1, lo, hi in self.cap(end):
            a, b = (lo, hi) if face == "left" else (self.depth - hi, self.depth - lo)
            out.append([(a, y0), (b, y0), (b, y1), (a, y1)])
        return out

    def no_cap(self, face):
        """The loops of the end face where the body has no cap: the section's outline for the
        face less the cap."""
        outline = _section.outline(face, self.section, self.depth)
        return loops(sweep([[outline]], minus=[self.cap_polygons(face)]))

    # -- the seam

    def seam(self, halves, which):
        """The seam cap of the half `which` ('base' or 'lid') as `{"band", "row", "pieces"}`, or
        None where the halves state no seam. The band is the one on the half's own side of the
        seam row."""
        row = _section.seam_row(halves, self.height)
        if row is None:
            return None
        base = (halves or {}).get("base") or {}
        above = (which == "base") == (base.get("outer") == "top")
        probe = row - 1e-6 if above else row + 1e-6
        for i, b in enumerate(self.bands):
            if b["heights"][0] <= probe < b["heights"][1] + _EPS:
                for y0, y1, iv in self.rows:
                    if y0 < row < y1:
                        return {"band": i, "row": row, "intervals": iv,
                                "pieces": sweep([[b["points"]], _rect_polys(iv, self.width)])}
        return {"band": None, "row": row, "intervals": [], "pieces": []}


def _dist(p, a, b):
    """How far the point `p` is from the segment `ab`."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _join(segments):
    """Segments end to end drawn as one polyline where they meet, `[[(x, y), ...], ...]`."""
    left = [list(s) for s in segments]
    out = []
    while left:
        run = left.pop()
        grew = True
        while grew:
            grew = False
            for s in left:
                if s[0] == run[-1]:
                    run += s[1:]
                elif s[-1] == run[0]:
                    run = s[:-1] + run
                else:
                    continue
                left.remove(s)
                grew = True
                break
        out.append(run)
    return sorted(out)


def _merge_runs(runs):
    out = []
    for a, b in sorted(runs):
        if out and a <= out[-1][1] + MERGE:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _intersect_runs(a, b):
    out = []
    for a0, a1 in a:
        for b0, b1 in b:
            lo, hi = max(a0, b0), min(a1, b1)
            if hi - lo > _EPS:
                out.append((lo, hi))
    return sorted(out)


def _runs_at(rect_polygon, ym):
    """The x runs of a rectilinear polygon at the height `ym`, from its vertical edges."""
    xs = sorted(min(a[0], b[0]) for a, b in zip(rect_polygon, rect_polygon[1:] + rect_polygon[:1])
                if abs(a[0] - b[0]) <= _EPS and min(a[1], b[1]) < ym < max(a[1], b[1]))
    return list(zip(xs[0::2], xs[1::2]))


def covers(polys, rect, tolerance=TOL, minus=()):
    """Whether the rectangle `(x0, y0, x1, y1)` lies wholly inside the union of `polys` less the
    union of `minus`, to `tolerance` along its edges."""
    x0, y0, x1, y1 = rect
    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    got = sum(area(p) for p in sweep([[box], polys], minus=[minus] if minus else (), x_range=(x0, x1)))
    want = (x1 - x0) * (y1 - y0)
    return want - got <= tolerance * ((x1 - x0) + (y1 - y0)) + 1e-9


def ribs_clipped(plan_obj, rect, h0, h1):
    """The loops of one rib's stripe, and how much of the rectangle's area they keep (0 to 1)."""
    lps = plan_obj.stripe(rect, h0, h1)
    want = (rect[2] - rect[0]) * (rect[3] - rect[1])
    got = sum(loop_area2(lp) / 2.0 for lp in lps if loop_area2(lp) > 0)
    return lps, (got / want if want > 0 else 0.0)


def valid(chassis):
    """Whether the chassis has what `Plan` reads and every polygon is one a body can be cut
    from: a section a plan can be cut against, a well-formed plan, inside the box. Lint reports
    each of those that is wrong, and the compiler draws nothing from a plan that is not."""
    w, h, d = chassis.get("width"), chassis.get("height"), chassis.get("depth")
    if not all(_plan._number(v) for v in (w, h, d)):
        return False
    pts = _section.points(chassis)
    plan = _plan.bands(chassis)
    if pts is None or plan is None or _section.polygon_problems(pts) or _section.box_problems(pts, d, h):
        return False
    if _plan.cap_problems(plan) or _plan.tiling_problems(plan, h):
        return False
    return not any(_plan.polygon_problems(b["points"]) or _plan.box_problems(b["points"], w, d)
                   for b in plan)
