"""A chassis with bevelled edges, as one solid both renderers read (#735).

A device body was always a `width x height x depth` box. Industrial housings
are not: the AurCore AIS switches cut the long edges where the flat front
meets the finned sides back at about 45 degrees, so the flat front is narrower
than the body and the front elevation has cut corners. `chassis.bevel` names
the edges and their sizes:

    bevel:
      - {edges: [front-left, front-right], size: 11}
      - {edges: [top-left, top-right], size: 6}

AN EDGE IS NAMED BY THE TWO FACES THAT MEET AT IT, using the face names the
views already use, so twelve names and no new vocabulary. Order does not
matter: `left-front` is `front-left`.

ONE SOLID, TWO READERS. This module cuts the box by one plane per bevelled
edge and returns the polygons. The 2D face drawing projects them - its
outline is the solid's silhouette and each bevel facing the viewer is a strip
on it - and the 3D viewer builds its mesh from the very same polygons, which
`render.py` publishes in `<device>.configs.json`. Computing the solid twice, in
Python and in JavaScript, would be two answers waiting to disagree.

THE FRAME is the viewer's: the box is centred on the origin, x across the
front (+x is the device's right as you face its front), y up, z out of the
front. A face drawing's origin is its top-left as that face is seen from
outside, with the orientations the kit maps each face's texture with:

    front   right +x, down -y          rear    right -x, down -y
    right   right -z, down -y          left    right +z, down -y
    top     right +x, down +z          bottom  right -x, down +z

(the side views put the front at the image's outer edge, the top view puts
the front at the bottom of the image, and the bottom view is the top view
turned over).
"""
import math

FACES = {
    "right":  (1, 0, 0),
    "left":   (-1, 0, 0),
    "top":    (0, 1, 0),
    "bottom": (0, -1, 0),
    "front":  (0, 0, 1),
    "rear":   (0, 0, -1),
}

# How each face is drawn: (right, down) as unit axes in the solid's frame.
DRAW_AXES = {
    "front":  ((1, 0, 0), (0, -1, 0)),
    "rear":   ((-1, 0, 0), (0, -1, 0)),
    "right":  ((0, 0, -1), (0, -1, 0)),
    "left":   ((0, 0, 1), (0, -1, 0)),
    "top":    ((1, 0, 0), (0, 0, 1)),
    "bottom": ((-1, 0, 0), (0, 0, 1)),
}

OPPOSITE = {"right": "left", "left": "right", "top": "bottom",
            "bottom": "top", "front": "rear", "rear": "front"}

# Every pair of adjacent faces, spelled the canonical way round.
EDGES = sorted({"-".join(sorted((a, b))) for a in FACES for b in FACES
                if a != b and OPPOSITE[a] != b})

EPS = 1e-6


class BevelError(ValueError):
    """A bevel the box cannot have: an unknown edge, or one that cuts too much."""


def edge_key(name):
    """The canonical spelling of an edge name, or BevelError."""
    parts = str(name).split("-")
    if len(parts) != 2 or parts[0] not in FACES or parts[1] not in FACES:
        raise BevelError(f"{name!r} is not an edge: name the two faces that meet "
                         f"at it, one of {', '.join(EDGES)}")
    a, b = parts
    if a == b or OPPOSITE[a] == b:
        raise BevelError(f"{name!r} is not an edge: {a} and {b} do not meet")
    return "-".join(sorted((a, b)))


def parse(chassis):
    """{edge: size} from `chassis.bevel`, or BevelError. {} when there is none."""
    out = {}
    for entry in (chassis or {}).get("bevel") or []:
        size = entry.get("size")
        if not isinstance(size, (int, float)) or size <= 0:
            raise BevelError(f"a bevel size is a positive number of mm, not {size!r}")
        for name in entry.get("edges") or []:
            k = edge_key(name)
            if k in out:
                raise BevelError(f"edge {k} is bevelled twice")
            out[k] = float(size)
    return out


# ---- vector arithmetic, kept to the few operations a convex cut needs --------

def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return _mul(a, 1 / n)


def _area(points, normal):
    acc = (0.0, 0.0, 0.0)
    for i, p in enumerate(points):
        acc = _add(acc, _cross(p, points[(i + 1) % len(points)]))
    return abs(_dot(acc, normal)) / 2


def _clip(points, n, d):
    """Sutherland-Hodgman: the part of a convex polygon where n.p <= d, and the
    points where it crossed the plane."""
    out, cut = [], []
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        dp, dq = _dot(n, p) - d, _dot(n, q) - d
        if dp <= EPS:
            out.append(p)
        if (dp < -EPS and dq > EPS) or (dp > EPS and dq < -EPS):
            t = dp / (dp - dq)
            x = _add(p, _mul(_sub(q, p), t))
            out.append(x)
            cut.append(x)
        elif abs(dp) <= EPS:
            cut.append(p)
    return out, cut


def _ordered(points, normal):
    """Distinct points of a convex polygon, counter-clockwise seen from outside."""
    uniq = []
    for p in points:
        if all(math.dist(p, u) > 1e-5 for u in uniq):
            uniq.append(p)
    if len(uniq) < 3:
        return uniq
    c = _mul((sum(p[0] for p in uniq), sum(p[1] for p in uniq), sum(p[2] for p in uniq)),
             1 / len(uniq))
    t1 = _unit(_sub(uniq[0], c))
    t2 = _cross(normal, t1)
    return sorted(uniq, key=lambda p: math.atan2(_dot(_sub(p, c), t2), _dot(_sub(p, c), t1)))


def plane(edge, size, w, h, d):
    """The cutting plane of one bevelled edge: (unit normal, offset), keeping
    n.p <= offset. A symmetric bevel takes `size` off each of the two faces."""
    a, b = edge.split("-")
    half = {"right": w / 2, "left": w / 2, "top": h / 2, "bottom": h / 2,
            "front": d / 2, "rear": d / 2}
    na, nb = FACES[a], FACES[b]
    n = _unit(_add(na, nb))
    return n, (half[a] + half[b] - size) / math.sqrt(2)


def solid(w, h, d, bevels):
    """The bevelled box as polygons: [{"face": name | "bevel", "edge": edge or
    None, "normal": (x, y, z), "points": [(x, y, z), ...]}], each wound
    counter-clockwise seen from outside. BevelError when a bevel cuts a face
    away or is swallowed by its neighbours."""
    hw, hh, hd = w / 2, h / 2, d / 2
    corners = {
        "front":  [(-hw, -hh, hd), (hw, -hh, hd), (hw, hh, hd), (-hw, hh, hd)],
        "rear":   [(hw, -hh, -hd), (-hw, -hh, -hd), (-hw, hh, -hd), (hw, hh, -hd)],
        "right":  [(hw, -hh, hd), (hw, -hh, -hd), (hw, hh, -hd), (hw, hh, hd)],
        "left":   [(-hw, -hh, -hd), (-hw, -hh, hd), (-hw, hh, hd), (-hw, hh, -hd)],
        "top":    [(-hw, hh, hd), (hw, hh, hd), (hw, hh, -hd), (-hw, hh, -hd)],
        "bottom": [(-hw, -hh, -hd), (hw, -hh, -hd), (hw, -hh, hd), (-hw, -hh, hd)],
    }
    polys = [{"face": f, "edge": None, "normal": FACES[f], "points": pts}
             for f, pts in corners.items()]
    for edge in sorted(bevels):
        n, off = plane(edge, bevels[edge], w, h, d)
        cut, kept = [], []
        for poly in polys:
            pts, crossing = _clip(poly["points"], n, off)
            cut += crossing
            if len(pts) >= 3 and _area(pts, poly["normal"]) > EPS:
                kept.append({**poly, "points": pts})
        cap = _ordered(cut, n)
        if len(cap) < 3 or _area(cap, n) <= EPS:
            raise BevelError(f"the bevel on {edge} cuts nothing: a neighbouring bevel "
                             "already took that edge away")
        polys = kept + [{"face": "bevel", "edge": edge, "normal": n, "points": cap}]
    for f in FACES:
        if not any(p["face"] == f for p in polys):
            raise BevelError(f"the bevels cut the whole {f} face away")
    for p in polys:
        p["points"] = _ordered(p["points"], p["normal"])
        if _area(p["points"], p["normal"]) <= EPS:
            raise BevelError(f"a bevel leaves the {p['face']} face with no area")
    return polys


def draw_size(view, w, h, d):
    """(width, height) of a face drawing, from the chassis box."""
    return {"front": (w, h), "rear": (w, h), "left": (d, h), "right": (d, h),
            "top": (w, d), "bottom": (w, d)}[view]


def to_drawing(p, view, w, h, d):
    """A point of the solid in `view`'s drawing coordinates (mm, origin top-left)."""
    right, down = DRAW_AXES[view]
    dw, dh = draw_size(view, w, h, d)
    return (_dot(p, right) + dw / 2, _dot(p, down) + dh / 2)


def _hull(points):
    """Convex hull, Andrew's monotone chain, in drawing order."""
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in points))
    if len(pts) < 3:
        return pts

    def turn(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def elevation(view, w, h, d, bevels):
    """What a face drawing shows of the bevelled solid.

    {"outline": [(x, y), ...]} is the silhouette - the drawing's own rectangle
    unless a bevel runs ALONG this view's line of sight, which cuts a corner off
    it. {"strips": [{"edge": e, "points": [...]}, ...]} are the bevels that face
    the viewer, each the band a bevel on one of this face's own edges leaves
    beside the flat face. {"flat": [...]} is the flat face itself, the only part
    of the drawing a part may be placed on."""
    polys = solid(w, h, d, bevels)
    look = FACES[view]
    seen = [p for p in polys if _dot(p["normal"], look) > EPS]
    proj = lambda pts: [to_drawing(q, view, w, h, d) for q in pts]
    outline = _hull([xy for p in seen for xy in proj(p["points"])])
    flat = next(proj(p["points"]) for p in polys if p["face"] == view)
    strips = [{"edge": p["edge"], "points": proj(p["points"])}
              for p in seen if p["face"] == "bevel"]
    return {"outline": outline, "flat": flat, "strips": strips}


def is_rectangle(outline, dw, dh):
    """True when an outline is just the drawing's own rectangle."""
    return len(outline) == 4 and all(
        min(abs(x), abs(x - dw)) < 1e-6 and min(abs(y), abs(y - dh)) < 1e-6
        for x, y in outline)


def published(chassis):
    """What `<device>.configs.json` carries for the viewer, or None without a
    bevel: the polygons to build the body from, rounded to a micrometre."""
    bevels = parse(chassis)
    if not bevels:
        return None
    w, h, d = chassis["width"], chassis["height"], chassis["depth"]
    return {"color": chassis.get("color"), "polygons": [
        {"face": p["face"],
         "points": [[round(c, 4) for c in q] for q in p["points"]]}
        for p in solid(w, h, d, bevels)]}
