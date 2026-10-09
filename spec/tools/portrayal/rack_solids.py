"""What of a device a cable cannot pass through: its `solids`, for rack.json.

docs/cable-lay-design.md section 1.1. A route is checked against solid bodies
(the kit's rack/solids.js); most devices are their envelope, which the kit
already knows from `w`, `h` and `d`, and carry nothing here. Three kinds are
not, and are derived here from the compiled faces of the default
configuration, never stated in a manifest:

- A SHEET PART (`shell: sheet`) is its plates: the floor of each well (a
  placement carrying `data-depth`), at that depth behind the face the well is
  cut in and the sheet `thickness` thick; each node that stands proud of the
  body (`data-z-out`), between the floor it is lifted onto and its `out`,
  stepped along a `profile-y` or `profile`; and each ear the plan draws
  (`data-kind="ear"`), the full height. A ring (a node inside a `data-guide`
  placement) is an opening, never a plate. On a part that carries a duct, what
  is mounted on its base (`data-behaviour="mounts"`: the fingers and cover
  clips) bounds the channel, and a cable passes it through a finger gap, so it
  is not a plate either.
- A ZERO-U PART THAT CARRIES A LANE (a vertical duct) is a pathway, derived as
  a sheet part is: with its fingers and clips left out by the rule above, what
  is left is its walls and its back.
- A DEVICE WITH CABLE SPACE INSIDE ITS ENVELOPE (a box device whose plan view
  marks a pathway: rings or a pass-through inside its body) is its shell walls
  (top, bottom, both sides, the rear), the patch plate at its front, the
  bodies of the modules seated behind it, and the plates of any lacer inside,
  derived as a sheet part's are.

A pass-through (`pass--<id>`) on the front or rear view is a hole through the
solids it lies over: on a sheet part through the whole depth, on a device with
cable space through the wall of its own face only. A tie slot is never one.

The frame is the one the rack products note uses for hosts: x from the left of
the device as seen from its front, y up from its bottom, z back from its front
(for a rack-face part, its outward face). Every box is {x, y, z, w, h, d} in mm.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "{http://www.w3.org/2000/svg}"
# a wall or plate whose thickness the part does not state: only its plane
# matters to a crossing (section 1.1)
DEFAULT_T = 1.0
ROUND = 3


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── transforms ──────────────────────────────────────────────────────────
def _mul(a, b):
    """Affine a then b, as SVG nests them: the parent's matrix times the child's."""
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (a0 * b0 + a2 * b1, a1 * b0 + a3 * b1, a0 * b2 + a2 * b3, a1 * b2 + a3 * b3,
            a0 * b4 + a2 * b5 + a4, a1 * b4 + a3 * b5 + a5)


IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def parse_transform(text):
    """An SVG transform list as one affine matrix (a, b, c, d, e, f)."""
    import math
    m = IDENT
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", text or ""):
        v = [float(x) for x in re.findall(r"-?[\d.]+(?:e-?\d+)?", args)]
        if name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            r = math.radians(v[0])
            c, s = math.cos(r), math.sin(r)
            cx, cy = (v[1], v[2]) if len(v) > 2 else (0, 0)
            t = _mul(_mul((1, 0, 0, 1, cx, cy), (c, s, -s, c, 0, 0)), (1, 0, 0, 1, -cx, -cy))
        elif name == "matrix" and len(v) == 6:
            t = tuple(v)
        else:
            continue
        m = _mul(m, t)
    return m


def _apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


# ── paths ───────────────────────────────────────────────────────────────
def path_rings(d):
    """The subpaths of an SVG path as point lists. A curve keeps its control
    points and its end: a quadratic corner (a fillet or a rounded corner)
    becomes the sharp corner it rounds, so a rectilinear outline stays
    rectilinear. Arcs keep their end point only."""
    toks = re.findall(r"[MmLlHhVvQqCcAaZzTtSs]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", d or "")
    rings, cur, x, y, i, cmd = [], [], 0.0, 0.0, 0, None
    sx = sy = 0.0
    n = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "A": 7, "T": 2, "S": 4, "Z": 0}

    def take(k):
        nonlocal i
        v = [float(t) for t in toks[i:i + k]]
        i += k
        return v
    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    rings.append(cur)
                cur, x, y = [], sx, sy
                continue
        if cmd is None:
            break
        rel, C = cmd.islower(), cmd.upper()
        v = take(n[C])
        if len(v) < n[C]:
            break
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == "M":
            if cur:
                rings.append(cur)
            x, y = v[0] + ox, v[1] + oy
            sx, sy, cur = x, y, [(x, y)]
            cmd = "l" if rel else "L"
        elif C == "L" or C == "T":
            x, y = v[0] + ox, v[1] + oy
            cur.append((x, y))
        elif C == "H":
            x = v[0] + (x if rel else 0)
            cur.append((x, y))
        elif C == "V":
            y = v[0] + (y if rel else 0)
            cur.append((x, y))
        elif C == "Q" or C == "S":
            cur.append((v[0] + ox, v[1] + oy))
            x, y = v[2] + ox, v[3] + oy
            cur.append((x, y))
        elif C == "C":
            cur.append((v[0] + ox, v[1] + oy))
            cur.append((v[2] + ox, v[3] + oy))
            x, y = v[4] + ox, v[5] + oy
            cur.append((x, y))
        elif C == "A":
            x, y = v[5] + ox, v[6] + oy
            cur.append((x, y))
    if cur:
        rings.append(cur)
    return rings


def rect_pieces(ring, eps=1e-6):
    """A rectilinear outline as rectangles (x, y, w, h), banded along y; None
    when the outline is not rectilinear."""
    pts = [p for k, p in enumerate(ring) if k == 0 or abs(p[0] - ring[k - 1][0]) > eps or abs(p[1] - ring[k - 1][1]) > eps]
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < eps and abs(pts[0][1] - pts[-1][1]) < eps:
        pts = pts[:-1]
    if len(pts) < 4:
        return None
    edges = list(zip(pts, pts[1:] + pts[:1]))
    if any(abs(a[0] - b[0]) > eps and abs(a[1] - b[1]) > eps for a, b in edges):
        return None
    vert = [(a[0], min(a[1], b[1]), max(a[1], b[1])) for a, b in edges if abs(a[0] - b[0]) <= eps]
    ys = sorted({p[1] for p in pts})
    bands = []
    for y0, y1 in zip(ys, ys[1:]):
        ym = (y0 + y1) / 2
        xs = sorted(x for x, lo, hi in vert if lo < ym < hi)
        spans = tuple((xs[k], xs[k + 1]) for k in range(0, len(xs) - 1, 2))
        if bands and bands[-1][2] == spans and abs(bands[-1][1] - y0) < eps:
            bands[-1] = (bands[-1][0], y1, spans)
        else:
            bands.append((y0, y1, spans))
    return [(a, y0, b - a, y1 - y0) for y0, y1, spans in bands for a, b in spans]


def _shapes(el, m):
    """An element's footprint on its face as rectangles (x, y, w, h), through
    its transform: a rect; a path's outer outline, cut into rectangles where it
    is rectilinear, else its bounding box. Its other subpaths (tie slots, or
    the holes a pass-through declares) are not taken out."""
    tag = el.tag.replace(SVG, "")
    if tag == "rect":
        x, y, w, h = (_num(el.get(k)) for k in ("x", "y", "width", "height"))
        pieces = [(x, y, w, h)]
    elif tag == "path":
        rings = path_rings(el.get("d"))
        if not rings:
            return []
        pieces = rect_pieces(rings[0]) or [_bbox(rings[0])]
    else:
        return []
    out = []
    for x, y, w, h in pieces:
        corners = [_apply(m, x, y), _apply(m, x + w, y), _apply(m, x, y + h), _apply(m, x + w, y + h)]
        out.append(_bbox(corners))
    return out


def _walk(root):
    """Every element with its matrix and what its ancestors lend it: the
    summed z-lift, whether it is inside a ring, whether it is mounted."""
    out = []

    def go(el, m, lift, guide, mounts):
        m = _mul(m, parse_transform(el.get("transform")))
        lift = lift + _num(el.get("data-z-lift"))
        guide = guide or bool(el.get("data-guide"))
        mounts = mounts or el.get("data-behaviour") == "mounts"
        out.append((el, m, lift, guide, mounts))
        for c in el:
            go(c, m, lift, guide, mounts)
    go(root, IDENT, 0.0, False, False)
    return out


def _r(v):
    return round(v + 0.0, ROUND)


def _box(x, y, z, w, h, d):
    return {"x": _r(x), "y": _r(y), "z": _r(z), "w": _r(w), "h": _r(h), "d": _r(d)}


class _Frame:
    """Turns a footprint on one view, between two depths into it, into a box in
    the device frame."""

    def __init__(self, w, h, d):
        self.w, self.h, self.d = w, h, d

    def box(self, view, fx, fy, fw, fh, a, b):
        a, b = min(a, b), max(a, b)
        if view == "front":
            return _box(fx, self.h - fy - fh, a, fw, fh, b - a)
        if view == "rear":
            return _box(self.w - fx - fw, self.h - fy - fh, self.d - b, fw, fh, b - a)
        if view == "top":
            # a plan: x as seen from the front, y from the back
            return _box(fx, self.h - b, self.d - fy - fh, fw, b - a, fh)
        return None


def _profile(el):
    for key, along in (("data-z-profile-y", "y"), ("data-z-profile", "x")):
        raw = el.get(key)
        if raw:
            pairs = [tuple(float(v) for v in p.split(":")) for p in raw.split(",") if ":" in p]
            if len(pairs) >= 2:
                return along, pairs
    return None, None


def sheet_solids(faces, chassis, *, inside_only=False):
    """The plates of a sheet body (or of what is inside a body with cable
    space): wells, proud nodes and ears, per the module docstring. `faces` maps
    a view name to its parsed root."""
    w, h, d = (_num(chassis.get(k)) for k in ("w", "h", "d"))
    t = _num(chassis.get("thickness")) or DEFAULT_T
    fr = _Frame(w, h, d)
    has_duct = any(e.get("data-guide") == "duct" or (e.get("data-class") == "guide" and (e.get("id") or "").startswith("guide--"))
                   for root in faces.values() for e in root.iter())
    out = []
    for view in ("top", "front", "rear"):
        root = faces.get(view)
        if root is None or (inside_only and view != "top"):
            continue
        for el, m, lift, guide, mounts in _walk(root):
            if guide:
                continue
            name = el.get("id") or ""
            # a well: its floor, at its depth behind this face, the sheet thick
            dep = el.get("data-depth")
            if (dep is not None and el.get("data-cavity") is None and el.get("data-see-through") is None
                    and el.get("data-class") != "port" and el.get("data-ref")):
                D = _num(dep)
                for c in el:
                    if c.get("data-z-out") is not None:
                        continue
                    for fx, fy, fw, fh in _shapes(c, _mul(m, parse_transform(c.get("transform")))):
                        b = fr.box(view, fx, fy, fw, fh, D, D + t)
                        if b:
                            out.append({"part": c.get("data-path") or c.get("id") or name, "box": b})
                continue
            # a node standing proud of what it is lifted onto
            if el.get("data-z-out") is not None and not (has_duct and mounts):
                O = _num(el.get("data-z-out"))
                along, prof = _profile(el)
                for fx, fy, fw, fh in _shapes(el, m):
                    if not prof:
                        if -O < -lift:
                            b = fr.box(view, fx, fy, fw, fh, -O, -lift)
                            b and out.append({"part": el.get("data-path") or name, "box": b})
                        continue
                    # stepped along its profile: each step as high as its higher end
                    span = fh if along == "y" else fw
                    for (p0, o0), (p1, o1) in zip(prof, prof[1:]):
                        lo, hi = max(0.0, min(p0, p1)), min(span, max(p0, p1))
                        top = max(o0, o1)
                        if hi - lo <= 0 or -top >= -lift:
                            continue
                        sx, sy, sw, sh = (fx, fy + lo, fw, hi - lo) if along == "y" else (fx + lo, fy, hi - lo, fh)
                        b = fr.box(view, sx, sy, sw, sh, -top, -lift)
                        b and out.append({"part": el.get("data-path") or name, "box": b})
                continue
            # an ear the plan draws: the full height of the part
            if view == "top" and el.get("data-kind") == "ear":
                for fx, fy, fw, fh in _shapes(el, m):
                    out.append({"part": name, "box": fr.box("top", fx, fy, fw, fh, 0, h)})
    return out


def _passes(faces, fr, depth_of):
    """Each pass-through on the front or rear view as a hole box: its rect,
    through the depth `depth_of(view)` gives, (z0, z1)."""
    holes = []
    for view in ("front", "rear"):
        root = faces.get(view)
        if root is None:
            continue
        for el, m, *_ in _walk(root):
            i = el.get("id") or ""
            if el.get("data-class") != "pass" or not i.startswith("pass--"):
                continue
            z0, z1 = depth_of(view)
            for fx, fy, fw, fh in _shapes(el, m):
                b = fr.box(view, fx, fy, fw, fh, 0, 0)
                b["z"], b["d"] = _r(z0), _r(z1 - z0)
                holes.append({"via": i[len("pass--"):], "box": b, "size": [_r(fw), _r(fh)]})
    return holes


def _overlaps(a, b):
    return all(a[k] < b[k] + b[s] and b[k] < a[k] + a[s] for k, s in (("x", "w"), ("y", "h"), ("z", "d")))


def _with_holes(solids, holes):
    for s in solids:
        hs = [h for h in holes if _overlaps(s["box"], h["box"])]
        if hs:
            s["holes"] = hs
    return solids


def shell_solids(faces, chassis):
    """A device with cable space inside its envelope: its shell walls, its
    patch plate, the modules seated behind the plate, and the plates of what
    is inside, with its declared pass-throughs as the openings."""
    w, h, d = (_num(chassis.get(k)) for k in ("w", "h", "d"))
    t = _num(chassis.get("thickness")) or DEFAULT_T
    fr = _Frame(w, h, d)
    out = [
        {"part": "shell/top", "box": _box(0, h - t, 0, w, t, d)},
        {"part": "shell/bottom", "box": _box(0, 0, 0, w, t, d)},
        {"part": "shell/left", "box": _box(0, 0, 0, t, h, d)},
        {"part": "shell/right", "box": _box(w - t, 0, 0, t, h, d)},
        {"part": "shell/rear", "box": _box(0, 0, d - t, w, h, t)},
        {"part": "plate", "box": _box(0, 0, 0, w, h, t)},
    ]
    front = faces.get("front")
    if front is not None:
        for el, m, *_ in _walk(front):
            bd = el.get("data-body-depth")
            if bd is None:
                continue
            pieces = [s for c, cm, *_ in _walk(el) if c is not el for s in _shapes(c, cm)] or []
            if not pieces:
                continue
            x0 = min(p[0] for p in pieces)
            y0 = min(p[1] for p in pieces)
            x1 = max(p[0] + p[2] for p in pieces)
            y1 = max(p[1] + p[3] for p in pieces)
            out.append({"part": el.get("data-path") or el.get("id"),
                        "box": fr.box("front", x0, y0, x1 - x0, y1 - y0, t, t + _num(bd))})
    out += sheet_solids(faces, chassis, inside_only=True)
    holes = _passes(faces, fr, lambda v: (0.0, t) if v == "front" else (d - t, d))
    return _with_holes(out, holes)


def has_cable_space(faces):
    """A box device declares cable space inside its envelope when its plan
    marks a pathway: a ring, a duct or a pass-through seen from above, which is
    inside the body (section 1.1). One whose pathways are only on its front or
    rear faces stays its envelope."""
    top = faces.get("top")
    if top is None:
        return False
    for e in top.iter():
        i = e.get("id") or ""
        if (e.get("data-guide") or e.get("data-class") in ("guide", "pass", "tray")
                or (e.get("data-kind") == "ring" and i.endswith("-end"))):
            return True
    return False


def solids(faces, chassis, *, lane=False):
    """The `solids` of one device, or None when its envelope is enough.
    `faces` maps a view to the parsed root of its compiled face; `lane` says the
    device is a zero-U part that carries a lane."""
    w, h, d = (_num(chassis.get(k)) for k in ("w", "h", "d"))
    if not (w > 0 and h > 0 and d > 0):
        return None
    if chassis.get("shell") == "sheet" or lane:
        fr = _Frame(w, h, d)
        out = _with_holes(sheet_solids(faces, chassis), _passes(faces, fr, lambda v: (0.0, d)))
        return out or None
    if has_cable_space(faces):
        return shell_solids(faces, chassis)
    return None


def read_faces(paths):
    """{view: parsed root} for the face files that exist."""
    out = {}
    for view, p in paths.items():
        if Path(p).is_file():
            out[view] = ET.parse(p).getroot()
    return out
