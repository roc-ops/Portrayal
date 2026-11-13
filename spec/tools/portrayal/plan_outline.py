"""The outline of a housing seen from above: `chassis.plan-outline`.

A cast housing has rounded corners and lobes when it is seen from above, and
`chassis.section`, one end profile run the whole width, can only make a
rectangle of it. `plan-outline` is a list of bands; each band is a range of
heights down from the top of the box and a closed polygon in the TOP face's
frame: x along the width from the left, y down the drawing with the rear at
the top and the front at the bottom (the bottom face is its mirror in x). This
module is the one place that reads the key's structure, so lint and the tests
cannot disagree about what a well-formed plan is.

Slanted edges are allowed here, which `section.polygon_problems` refuses, so
the polygon checker is this module's own. What it judges needs no clipping:
the polygon as a polygon, the bands against the height, the caps and the box.
The rules that need the plan cut against the section come with the code that
clips.
"""
import math

# millimetres: how far a height or a coordinate may be off and still be on the line
TOL = 0.01
# the shortest edge a polygon may have, millimetres
MIN_EDGE = 0.1
# the caps; raising one later is two-way, lowering one is not
MAX_POINTS = 512
MAX_BANDS = 16
MAX_TOTAL = 2048


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def bands(chassis):
    """`chassis.plan-outline` as `[{"heights": (from, to), "points": [(x, y), ...]}, ...]` in
    floats, or None where the chassis states none or states something that is not a list of
    bands (the schema reports that)."""
    raw = (chassis or {}).get("plan-outline")
    if not isinstance(raw, list) or not raw:
        return None
    out = []
    for b in raw:
        if not isinstance(b, dict):
            return None
        h, pts = b.get("heights"), b.get("points")
        if not isinstance(h, (list, tuple)) or len(h) != 2 or not all(_number(v) for v in h):
            return None
        if not isinstance(pts, list) or len(pts) < 3:
            return None             # fewer than three points is no polygon; the schema reports it
        poly = []
        for p in pts:
            if not isinstance(p, (list, tuple)) or len(p) != 2 or not all(_number(v) for v in p):
                return None
            poly.append((float(p[0]), float(p[1])))
        out.append({"heights": (float(h[0]), float(h[1])), "points": poly})
    return out


def area2(pts):
    """Twice the signed area by the shoelace sum. With y down, a clockwise polygon (as it
    appears on the screen) is positive."""
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def _orient(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _sign(v):
    return 0 if abs(v) < 1e-7 else (1 if v > 0 else -1)


def _on_segment(a, b, p):
    return (min(a[0], b[0]) - 1e-9 <= p[0] <= max(a[0], b[0]) + 1e-9
            and min(a[1], b[1]) - 1e-9 <= p[1] <= max(a[1], b[1]) + 1e-9)


def _touch(a, b, c, d):
    """Whether segments ab and cd share any point."""
    o1, o2 = _sign(_orient(a, b, c)), _sign(_orient(a, b, d))
    o3, o4 = _sign(_orient(c, d, a)), _sign(_orient(c, d, b))
    if o1 != o2 and o3 != o4:
        return True
    return ((o1 == 0 and _on_segment(a, b, c)) or (o2 == 0 and _on_segment(a, b, d))
            or (o3 == 0 and _on_segment(c, d, a)) or (o4 == 0 and _on_segment(c, d, b)))


def polygon_problems(pts):
    """What is wrong with one band's polygon as a polygon, in words: a repeated point, an edge
    shorter than 0.1 mm, an edge that crosses or touches another or doubles back on its
    neighbour, and the wrong winding. Slanted edges are fine."""
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        if p in pts[:i]:
            out.append(f"point {i} {list(p)} is a repeated point: it is the same as point {pts.index(p)}")
    edges = list(zip(pts, pts[1:] + pts[:1]))
    for i, (a, b) in enumerate(edges):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if 0 < length < MIN_EDGE - 1e-9:
            out.append(f"the edge from point {i} to point {(i + 1) % n} is {length:.3g} mm, "
                       f"shorter than the {MIN_EDGE:g} mm an edge has to be")
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        if b != a and b != c and _sign(_orient(a, b, c)) == 0 and \
                (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]) < 0:
            out.append(f"point {i} {list(b)} doubles back: the edge leaves the way it came")
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue               # the closing edge meets the first one at its own vertex
            if _touch(*edges[i], *edges[j]):
                out.append(f"the edge from point {i} crosses or touches the edge from point {j}")
    # the sign of the area means something only for a polygon that does not cross itself
    if not any("crosses" in m or "doubles" in m for m in out) and area2(pts) <= 0:
        out.append("the polygon is not clockwise with y down (its signed area is not positive)")
    return out


def tiling_problems(plan, height):
    """What is wrong with the bands' heights against the box height: a band that does not go
    forward, a first band that does not start at 0, a last that does not end at `height`, a gap
    or an overlap between two. Bands are half-open `[from, to)` and listed from the top."""
    out = []
    for i, b in enumerate(plan):
        lo, hi = b["heights"]
        if hi - lo <= TOL:
            out.append(f"band {i} runs from {lo:g} to {hi:g}: it has to go forward")
        if i == 0:
            if abs(lo) > TOL:
                out.append(f"the first band starts at {lo:g}, not at the top (0)")
        else:
            prev = plan[i - 1]["heights"][1]
            if lo - prev > TOL:
                out.append(f"band {i} starts at {lo:g} but band {i - 1} ends at {prev:g}: "
                           f"a gap of {lo - prev:g} mm")
            elif prev - lo > TOL:
                out.append(f"band {i} starts at {lo:g}, before band {i - 1} ends at {prev:g}: an "
                           "overlap (the bands are listed in order from the top)")
    last = plan[-1]["heights"][1]
    if abs(last - height) > TOL:
        out.append(f"the last band ends at {last:g}, not at the height {height:g}")
    return out


def cap_problems(plan):
    """The caps: at most 512 points a band, 16 bands and 2048 points in all."""
    out = []
    if len(plan) > MAX_BANDS:
        out.append(f"{len(plan)} bands: at most {MAX_BANDS}")
    for i, b in enumerate(plan):
        if len(b["points"]) > MAX_POINTS:
            out.append(f"band {i} has {len(b['points'])} points: at most {MAX_POINTS} a band")
    total = sum(len(b["points"]) for b in plan)
    if total > MAX_TOTAL:
        out.append(f"{total} points in all: at most {MAX_TOTAL}")
    return out


def box_problems(pts, width, depth):
    """Whether the polygon lies inside the `width` by `depth` box, in the top face's frame."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if min(xs) < -TOL or max(xs) > width + TOL or min(ys) < -TOL or max(ys) > depth + TOL:
        return [f"the polygon reaches outside the {width:g} by {depth:g} box "
                f"(x {min(xs):g} to {max(xs):g}, y {min(ys):g} to {max(ys):g})"]
    return []
