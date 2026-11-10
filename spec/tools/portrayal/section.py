"""The end profile of a housing that is an extrusion (docs/modelling-a-device.md,
"A housing with a stepped end").

`chassis.section` is a closed polygon in the RIGHT end face's drawing frame: x
across the depth, growing toward the rear (the right face is drawn with the front
at its left edge, bevel.DRAW_AXES), and y down the height, both in millimetres
from the top-left corner of the face. The left face is the same body seen from the
other end, so its outline is the polygon mirrored in x with the winding reversed
to keep it clockwise. This module is the one place that reads the key, so lint,
the compiler and the tests cannot disagree about what the polygon is, where it
is solid and which way round each face sees it.

Every edge is axis-aligned in this version, which lets "inside the outline" and
"a step of the body" be answered exactly with bands rather than by general
polygon clipping.
"""

# how close a vertex has to be to a side of the box to be on it, millimetres
TOL = 0.005
END_FACES = ("right", "left")
LEVEL_FACES = ("top", "bottom")


def points(chassis):
    """`chassis.section` as a list of (x, y) floats, or None where the chassis
    states none or states something that is not a list of number pairs."""
    raw = (chassis or {}).get("section")
    if not isinstance(raw, list) or not raw:
        return None
    out = []
    for p in raw:
        if (not isinstance(p, (list, tuple)) or len(p) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in p)):
            return None
        out.append((float(p[0]), float(p[1])))
    return out


def area2(pts):
    """Twice the signed area by the shoelace sum. With y down, a clockwise
    polygon (as it appears on the screen) is positive."""
    return sum(x0 * y1 - x1 * y0
               for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def outline(face, pts, depth):
    """The polygon as `face` draws it: as stated on the right, mirrored in x with
    the winding reversed on the left. None for a face the section does not draw."""
    if face == "right":
        return list(pts)
    if face == "left":
        return [(depth - x, y) for x, y in reversed(pts)]
    return None


def _edges(pts):
    return list(zip(pts, pts[1:] + pts[:1]))


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(a, b, p):
    return (min(a[0], b[0]) - TOL <= p[0] <= max(a[0], b[0]) + TOL
            and min(a[1], b[1]) - TOL <= p[1] <= max(a[1], b[1]) + TOL)


def _touch(a, b, c, d):
    """Whether segments ab and cd share any point."""
    d1, d2 = _cross(c, d, a), _cross(c, d, b)
    d3, d4 = _cross(a, b, c), _cross(a, b, d)
    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return True
    return ((abs(d1) < 1e-9 and _on_segment(c, d, a)) or (abs(d2) < 1e-9 and _on_segment(c, d, b))
            or (abs(d3) < 1e-9 and _on_segment(a, b, c)) or (abs(d4) < 1e-9 and _on_segment(a, b, d)))


def polygon_problems(pts):
    """What is wrong with the polygon as a polygon, in words, whatever box it is
    meant for: a repeated or collinear vertex, a self-crossing, the wrong winding,
    a slanted edge."""
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        if p in pts[:i]:
            out.append(f"point {i} {list(p)} is a repeated point: it is the same as an earlier one")
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        if b != a and b != c and abs(_cross(a, b, c)) < 1e-9:
            out.append(f"point {i} {list(b)} is collinear with its neighbours: a vertex lies where the edge goes straight on")
    for i, (a, b) in enumerate(_edges(pts)):
        if a[0] != b[0] and a[1] != b[1]:
            out.append(f"the edge from point {i} to point {(i + 1) % n} is not axis-aligned")
    edges = _edges(pts)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue               # the closing edge meets the first one at its own vertex
            if _touch(*edges[i], *edges[j]):
                out.append(f"the edge from point {i} crosses or touches the edge from point {j}")
    # the sign of the area means something only for a polygon that does not cross itself
    if not any("crosses" in m for m in out) and area2(pts) <= 0:
        out.append("the polygon is not clockwise with y down (its signed area is not positive)")
    return out


def box_problems(pts, depth, height):
    """What is wrong with the polygon against the `depth` by `height` box it is
    the end profile of."""
    out = []
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if min(xs) < -TOL or max(xs) > depth + TOL or min(ys) < -TOL or max(ys) > height + TOL:
        out.append(f"the polygon reaches outside the {depth:g} by {height:g} box "
                   f"(x {min(xs):g} to {max(xs):g}, y {min(ys):g} to {max(ys):g})")
    # a gap is how far the polygon stops short of a side; one that overshoots is reported above
    for side, gap in (("left", min(xs)), ("right", depth - max(xs)),
                      ("top", min(ys)), ("bottom", height - max(ys))):
        if gap > TOL:
            out.append(f"the polygon does not touch the {side} side of the box (it stops {gap:g} mm short)")
    top = sum(1 for a, b in _edges(pts) if a[1] == b[1] and abs(a[1]) <= TOL and a[0] != b[0])
    bottom = sum(1 for a, b in _edges(pts) if a[1] == b[1] and abs(a[1] - height) <= TOL and a[0] != b[0])
    if top != 1:
        out.append(f"{top} edges lie on the top side of the box, not exactly one")
    if bottom != 1:
        out.append(f"{bottom} edges lie on the bottom side of the box, not exactly one")
    return out


def _bands(pts):
    """Horizontal bands of an axis-aligned polygon: `[(y0, y1, [(x0, x1), ...])]`
    for each strip between consecutive vertex heights, with the x intervals that
    are solid in it (the vertical edges, paired left to right)."""
    ys = sorted({p[1] for p in pts})
    verticals = [(a[0], min(a[1], b[1]), max(a[1], b[1])) for a, b in _edges(pts) if a[0] == b[0]]
    out = []
    for y0, y1 in zip(ys, ys[1:]):
        mid = (y0 + y1) / 2.0
        xs = sorted(x for x, lo, hi in verticals if lo < mid < hi)
        out.append((y0, y1, list(zip(xs[0::2], xs[1::2]))))
    return out


def contains_box(pts, box):
    """Whether the rectangle `(x0, y0, x1, y1)` lies wholly inside the polygon.
    Exact for an axis-aligned polygon: in every band the rectangle reaches, its
    x range has to sit inside one solid interval."""
    x0, y0, x1, y1 = box
    for b0, b1, intervals in _bands(pts):
        if min(b1, y1) - max(b0, y0) <= TOL:
            continue
        if not any(lo - TOL <= x0 and x1 <= hi + TOL for lo, hi in intervals):
            return False
    return y0 >= min(p[1] for p in pts) - TOL and y1 <= max(p[1] for p in pts) + TOL


def level_steps(pts, side):
    """Where the body's highest surface changes, seen from the top (`side` is
    "top") or the bottom ("bottom"): the x values, across the depth, of each
    step. A column of the section is solid between the lowest and highest y the
    polygon has there, and the surface seen from above is the lowest y."""
    xs = sorted({p[0] for p in pts})
    heights = []
    for x0, x1 in zip(xs, xs[1:]):
        mid = (x0 + x1) / 2.0
        ys = []
        for b0, b1, intervals in _bands(pts):
            if any(lo < mid < hi for lo, hi in intervals):
                ys += [b0, b1]
        heights.append(min(ys) if side == "top" else max(ys))
    return [x for x, a, b in zip(xs[1:], heights, heights[1:]) if abs(a - b) > TOL]


def straddles_step(pts, side, depth, lo, hi):
    """Whether a part on the top or bottom face, whose box covers the drawing
    rows `lo` to `hi` (the face is drawn with the front at the bottom, so a row
    `r` is `depth - r` across the section), lies over a step of the body."""
    a, b = depth - hi, depth - lo
    return any(a + TOL < x < b - TOL for x in level_steps(pts, side))
