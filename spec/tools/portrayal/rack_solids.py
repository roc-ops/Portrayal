"""What of a device a cable cannot pass through: its `solids`, for rack.json.

docs/cable-lay-design.md section 1.1. A route is checked against solid bodies
(the kit's rack/solids.js); most devices are their envelope, which the kit
already knows from `w`, `h` and `d`, and carry nothing here. Two kinds are
not, and are derived here from the compiled faces of the default
configuration, never stated in a manifest:

- A SHEET PART (`shell: sheet`) is its plates: the floor of each well (the
  component elements, `data-class="bezel"`, of a placement carrying
  `data-depth`), at that depth behind the face the well is cut in and the
  sheet `thickness` thick; and each node that stands proud of the body
  (`data-z-out`), between the floor it is lifted onto and its `out`, stepped
  along a `profile-y` or `profile`. Drawn decor (a seam line, a window, the
  edge of an ear on the plan) is never a plate. A ring (a node inside a
  `data-guide` placement) is an opening, never a plate. A duct's channel is
  open: anything whose footprint lies inside a duct guide's footprint on that
  face is not a plate, whatever its behaviour; and on a part that carries a
  duct, what is mounted on its base (`data-behaviour="mounts"`: the fingers
  and the cover clips) bounds the channel and is passed through a finger gap,
  so it is not a plate either.
- A ZERO-U PART THAT CARRIES A LANE (a vertical duct) is a pathway, derived as
  a sheet part is: with its channel left open by the rules above, what is left
  is its walls and its back.

A device with cable space inside its envelope (the FHD enclosures, the third
kind of section 1.1) waits for step 6 of the note, with the library data that
says where its plate and its pass-throughs are; until then it is its
envelope, as every box device is.

A pass-through (`pass--<id>`) on the front or rear view is a hole through the
solids it lies over, the whole depth. A tie slot is never one.

The frame is the one the rack products note uses for hosts: x from the left of
the device as seen from its front, y up from its bottom, z back from its front
(for a rack-face part, its outward face). Every box is {x, y, z, w, h, d} in mm.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from portrayal.elements import _apply, _mul, parse_transform

SVG = "{http://www.w3.org/2000/svg}"
# a plate whose thickness the part does not state: only its plane matters to
# a crossing (section 1.1)
DEFAULT_T = 1.0
ROUND = 3
IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


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


def _ducts(root):
    """The footprints of the duct guides drawn on one face: its open channel."""
    out = []
    for el, m, *_ in _walk(root):
        if el.get("data-guide") == "duct" or (el.get("data-class") == "guide" and (el.get("id") or "").startswith("guide--")):
            out += _shapes(el, m)
    return out


def _in_duct(piece, ducts, eps=1e-6):
    x, y, w, h = piece
    return any(x >= dx - eps and y >= dy - eps and x + w <= dx + dw + eps and y + h <= dy + dh + eps
               for dx, dy, dw, dh in ducts)


def sheet_solids(faces, chassis):
    """The plates of a sheet body or a lane duct: wells and proud nodes, per
    the module docstring. `faces` maps a view name to its parsed root."""
    w, h, d = (_num(chassis.get(k)) for k in ("w", "h", "d"))
    t = _num(chassis.get("thickness")) or DEFAULT_T
    fr = _Frame(w, h, d)
    ducts_of = {v: _ducts(r) for v, r in faces.items()}
    has_duct = any(ducts_of.values())
    out = []
    for view in ("top", "front", "rear"):
        root = faces.get(view)
        if root is None:
            continue
        ducts = ducts_of[view]
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
                    if c.get("data-z-out") is not None or c.get("data-class") != "bezel":
                        continue
                    for piece in _shapes(c, _mul(m, parse_transform(c.get("transform")))):
                        if not _in_duct(piece, ducts):
                            out.append({"part": c.get("data-path") or c.get("id") or name,
                                        "box": fr.box(view, *piece, D, D + t)})
                continue
            # a node standing proud of what it is lifted onto
            if el.get("data-z-out") is None or (has_duct and mounts):
                continue
            O = _num(el.get("data-z-out"))
            along, prof = _profile(el)
            for fx, fy, fw, fh in _shapes(el, m):
                if _in_duct((fx, fy, fw, fh), ducts):
                    continue
                if not prof:
                    if -O < -lift:
                        out.append({"part": el.get("data-path") or name, "box": fr.box(view, fx, fy, fw, fh, -O, -lift)})
                    continue
                # stepped along its profile: each step as high as its higher end
                span = fh if along == "y" else fw
                for (p0, o0), (p1, o1) in zip(prof, prof[1:]):
                    lo, hi = max(0.0, min(p0, p1)), min(span, max(p0, p1))
                    top = max(o0, o1)
                    if hi - lo <= 0 or -top >= -lift:
                        continue
                    sx, sy, sw, sh = (fx, fy + lo, fw, hi - lo) if along == "y" else (fx + lo, fy, hi - lo, fh)
                    out.append({"part": el.get("data-path") or name, "box": fr.box(view, sx, sy, sw, sh, -top, -lift)})
    return [s for s in out if s["box"]]


def _passes(faces, fr):
    """Each pass-through on the front or rear view as a hole box: its rect,
    through the whole depth."""
    holes = []
    for view in ("front", "rear"):
        root = faces.get(view)
        if root is None:
            continue
        for el, m, *_ in _walk(root):
            i = el.get("id") or ""
            if el.get("data-class") != "pass" or not i.startswith("pass--"):
                continue
            for fx, fy, fw, fh in _shapes(el, m):
                b = fr.box(view, fx, fy, fw, fh, 0, fr.d)
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


def solids(faces, chassis, *, lane=False):
    """The `solids` of one device, or None when its envelope is enough.
    `faces` maps a view to the parsed root of its compiled face; `lane` says the
    device is a zero-U part that carries a lane."""
    w, h, d = (_num(chassis.get(k)) for k in ("w", "h", "d"))
    if not (w > 0 and h > 0 and d > 0):
        return None
    if chassis.get("shell") != "sheet" and not lane:
        return None
    out = _with_holes(sheet_solids(faces, chassis), _passes(faces, _Frame(w, h, d)))
    return out or None


# ── trays (docs/cable-lay-design.md sections 2 and 3) ───────────────────────
def _attr_nums(el, key):
    raw = el.get(key)
    if raw is None:
        return None
    try:
        return [float(v) for v in raw.split()]
    except ValueError:
        return None


def _ring_openings(root, fr):
    """Every ring on a plan whose contract places its opening (`sill` and
    `aperture.at`), as {via, run, base, box}: `base` the height, up from the
    device's bottom, of what it stands on (the envelope's top less the depth
    it is lifted down by); `box` its opening in the device frame."""
    out = []
    for el, m, lift, _guide, _mounts in _walk(root):
        if not el.get("data-guide") == "ring" or not el.get("id"):
            continue
        run = el.get("data-guide-run") or "x"
        ap, at = _attr_nums(el, "data-guide-aperture"), _attr_nums(el, "data-guide-aperture-at")
        sill, depth = _attr_nums(el, "data-guide-sill"), _attr_nums(el, "data-guide-depth")
        if not (ap and at and sill) or run not in ("x", "y"):
            continue
        depth = depth[0] if depth else 0.0
        (aw, ah), (ax, ay) = ap[:2], at[:2]
        fw, fh = (depth, aw) if run == "x" else (aw, depth)
        corners = [_apply(m, ax, ay), _apply(m, ax + fw, ay), _apply(m, ax, ay + fh), _apply(m, ax + fw, ay + fh)]
        fx, fy, fw2, fh2 = _bbox(corners)
        # its run as drawn, turned by the placement: along the face's x or y
        ux, uy = _apply(m, 1.0, 0.0), _apply(m, 0.0, 0.0)
        along_x = abs(ux[0] - uy[0]) >= abs(ux[1] - uy[1])
        drawn_run = run if along_x else ("y" if run == "x" else "x")
        base = fr.h + lift
        lo, hi = base + sill[0], base + sill[0] + ah
        out.append({"via": el.get("id"), "run": "x" if drawn_run == "x" else "z", "base": _r(base),
                    "box": fr.box("top", fx, fy, fw2, fh2, fr.h - hi, fr.h - lo)})
    return out


def trays(faces, chassis):
    """The `trays` of one device, for rack.json, or None: each tray drawn on
    its plan (a part's `tray:` under its instance, or the view's own `trays`),
    from the unpainted rects render.py compiles them to. Per tray, in the
    device frame of `solids`:

    - `id`, the placement's or the view's id, which a route names;
    - `top`, the height of the floor's surface above the device's bottom, and
      `thickness`, the plate's (`chassis.thickness`, else DEFAULT_T), so its
      underside is `top - thickness`;
    - `run`, `x` across the device or `z` front to back; `lip`; `slack`;
    - `floor` and `ties`, each a box through the plate;
    - `rings`: each ring standing on the floor whose opening its contract
      places, `{via, run, box}`, its box the clear opening, so a cable resting
      in it lies on the bottom of the box.

    Only the plan is read: a floor seen from above is where `height` gives the
    third axis."""
    root = faces.get("top")
    if root is None:
        return None
    w, h, d = (_num(chassis.get(k)) for k in ("w", "h", "d"))
    if not (w > 0 and h > 0 and d > 0):
        return None
    t = _num(chassis.get("thickness")) or DEFAULT_T
    fr = _Frame(w, h, d)
    by = {}
    for el, m, _lift, _guide, _mounts in _walk(root):
        cls, tid = el.get("data-class"), el.get("data-tray")
        if cls not in ("tray", "tie") or not tid:
            continue
        e = by.setdefault(tid, {"id": tid, "floor": [], "ties": []})
        if cls == "tray":
            top = _num(el.get("data-tray-height"))
            e["top"], e["thickness"] = _r(top), _r(t)
            e["lip"] = _r(_num(el.get("data-tray-lip")))
            # the run as drawn, through the placement's turn: across the plan
            # is x, down it is the depth, z
            ux, uy = _apply(m, 1.0, 0.0), _apply(m, 0.0, 0.0)
            along_x = abs(ux[0] - uy[0]) >= abs(ux[1] - uy[1])
            drawn = el.get("data-tray-run") or "x"
            e["run"] = "x" if (drawn == "x") == along_x else "z"
            slack = (el.get("data-tray-slack") or "").split()
            if slack[:1] == ["area"]:
                e["slack"] = {"kind": "area"}
            elif slack[:1] == ["spool"] and len(slack) == 4:
                sx, sy = _apply(m, float(slack[1]), float(slack[2]))
                e["slack"] = {"kind": "spool", "x": _r(sx), "z": _r(fr.d - sy), "diameter": _r(float(slack[3]))}
        for fx, fy, fw, fh in _shapes(el, m):
            e["floor" if cls == "tray" else "ties"].append(("pending", fx, fy, fw, fh))
    out = []
    rings = _ring_openings(root, fr)
    for tid in sorted(by):
        e = by[tid]
        if "top" not in e:
            continue
        top = e["top"]
        plate = lambda fx, fy, fw, fh: fr.box("top", fx, fy, fw, fh, h - top, h - top + e["thickness"])
        foot = [(fx, fy, fw, fh) for _, fx, fy, fw, fh in e["floor"]]
        e["floor"] = [plate(*f) for f in foot]
        e["ties"] = [plate(fx, fy, fw, fh) for _, fx, fy, fw, fh in e["ties"]]
        # a ring stands on this floor when its base is the floor's top and the
        # middle of its opening's footprint is over a floor rectangle
        on = []
        for r in rings:
            b = r["box"]
            cx, cz = b["x"] + b["w"] / 2, b["z"] + b["d"] / 2
            if abs(r["base"] - top) <= 0.1 and any(
                    f["x"] - 1e-6 <= cx <= f["x"] + f["w"] + 1e-6 and f["z"] - 1e-6 <= cz <= f["z"] + f["d"] + 1e-6
                    for f in e["floor"]):
                on.append({"via": r["via"], "run": r["run"], "box": b})
        if on:
            e["rings"] = sorted(on, key=lambda r: (r["box"]["x"], r["box"]["z"]))
        if not e["ties"]:
            del e["ties"]
        out.append(e)
    return out or None


def read_faces(paths):
    """{view: parsed root} for the face files that exist."""
    out = {}
    for view, p in paths.items():
        if Path(p).is_file():
            out[view] = ET.parse(p).getroot()
    return out
