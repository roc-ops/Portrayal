"""The elements file: every row a compiled face lists, written down once (#727).

`<device>[.<config>].<view>.elements.json` sits beside the SVG of the same name
and says, for each element the face draws, what the SVG already carries about
it - its address, class, ref, media, lamp states, owners - with its box in the
face's millimetre frame and the tree parent the Explorer gives it.

READ FROM THE DRAWING, NOT FROM THE MANIFEST. Every embedder used to rebuild
this from the SVG - the Explorer's tree, kit/zones.js, an adjacency importer -
and each did it a little differently, so the one way to be sure the file and
the drawing agree is to take the file from the drawing. render.py hands this
module the element tree it has just serialised; nothing here re-derives a
placement, so nothing here can disagree with what was drawn.

NO DOM AND NO LAYOUT. A server reading this has neither, which is the point of
publishing it. So the box is the union of the face-frame bounds of the shapes
under the row - rect, circle, ellipse, line, polygon, polyline and path, each
through the full transform stack, curves and arcs at their true extremes - and
three things are left out because they have no box without a layout pass or
are not geometry: <text> (a glyph run's extent depends on the font the viewer
has), stroke width (the box is the shape's, not its paint's), and clipping
(a clip-path or mask is not applied). docs/format-stability.md states the same.

THE TREE IS kit/swap.js's `faceTree`, in Python. The nesting rules - path
prefix, then a projection's host, then a cutout's filler, then a single local
`data-for` owner, then `chassis` for a lamp whose targets are all in another
view - are written once in the kit and once here, and
spec/tests/test_face_elements_parity.py runs the kit's over real faces and
compares parents row for row.
"""
import json
import math
import re

SVG_NS = "http://www.w3.org/2000/svg"

# THE FIELDS A ROW CARRIES, EACH THE data-* ATTRIBUTE IT IS READ FROM. Strings
# as the SVG writes them, except the two space-separated vocabularies, which
# are lists so a reader never splits them itself.
_FIELDS = (("id", "id"), ("class", "data-class"), ("ref", "data-ref"),
           ("media", "data-media"), ("speed", "data-speed"),
           ("group", "data-group"), ("group-role", "data-group-role"),
           ("rel-pos", "data-rel-pos"))
_LISTS = (("states", "data-states"), ("for", "data-for"))

# Subtrees that paint nothing where they stand: their shapes are referenced
# from elsewhere (a pattern, a clip, a mask) or are not shapes at all.
_INERT = {"defs", "clipPath", "mask", "pattern", "symbol", "marker", "title",
          "desc", "metadata", "style", "linearGradient", "radialGradient", "text"}


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _num(v):
    """A coordinate as the file writes it: 4 decimals (0.1 um), never -0."""
    r = round(float(v), 4)
    return 0.0 if r == 0 else r


# ---- transforms -------------------------------------------------------------
# SVG's [a b c d e f]: x' = a*x + c*y + e, y' = b*x + d*y + f - kit/zones.js's
# parseTransform, so a box here and a box there come from the same arithmetic.
_I = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_TF = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _mul(m, n):
    return (m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
            m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
            m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5])


def _apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def parse_transform(s):
    m = _I
    for kind, args in _TF.findall(s or ""):
        n = [float(v) for v in _NUM.findall(args)]
        if kind == "matrix" and len(n) >= 6:
            m = _mul(m, tuple(n[:6]))
        elif kind == "translate":
            m = _mul(m, (1, 0, 0, 1, n[0] if n else 0.0, n[1] if len(n) > 1 else 0.0))
        elif kind == "scale":
            sx = n[0] if n else 1.0
            m = _mul(m, (sx, 0, 0, n[1] if len(n) > 1 else sx, 0, 0))
        elif kind == "skewX":
            m = _mul(m, (1, 0, math.tan(math.radians(n[0] if n else 0)), 1, 0, 0))
        elif kind == "skewY":
            m = _mul(m, (1, math.tan(math.radians(n[0] if n else 0)), 0, 1, 0, 0))
        elif kind == "rotate":
            a = math.radians(n[0] if n else 0.0)
            r = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(n) >= 3:
                m = _mul(_mul(_mul(m, (1, 0, 0, 1, n[1], n[2])), r), (1, 0, 0, 1, -n[1], -n[2]))
            else:
                m = _mul(m, r)
    return m


# ---- shape bounds -----------------------------------------------------------

class _Box:
    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(self):
        self.x0 = self.y0 = math.inf
        self.x1 = self.y1 = -math.inf

    def add(self, x, y):
        self.x0 = min(self.x0, x); self.y0 = min(self.y0, y)
        self.x1 = max(self.x1, x); self.y1 = max(self.y1, y)

    def union(self, o):
        if o.empty():
            return
        self.add(o.x0, o.y0); self.add(o.x1, o.y1)

    def empty(self):
        return self.x0 == math.inf

    def out(self):
        if self.empty():
            return None
        return {"x": _num(self.x0), "y": _num(self.y0),
                "w": _num(self.x1 - self.x0), "h": _num(self.y1 - self.y0)}


def _f(el, k, d=0.0):
    try:
        return float(el.get(k))
    except (TypeError, ValueError):
        return d


def _conic(box, m, cx, cy, ux, uy, vx, vy, t0=None, dt=None):
    """An ellipse, or an arc of one, P(t) = c + u cos t + v sin t in local
    coordinates, through `m`. Its face-frame extremes are where each axis's
    derivative is zero - exact, at any rotation. With `t0`/`dt` only the
    extremes inside the swept range count (the caller adds the endpoints)."""
    a, b, c, d = m[0], m[1], m[2], m[3]
    # P(t) in the face frame: C + U cos t + V sin t
    Cx, Cy = _apply(m, cx, cy)
    Ux, Uy = a * ux + c * uy, b * ux + d * uy
    Vx, Vy = a * vx + c * vy, b * vx + d * vy
    for t in (math.atan2(Vx, Ux), math.atan2(Vy, Uy)):
        for tt in (t, t + math.pi):
            if dt is not None:
                # inside the sweep from t0 through dt (dt negative sweeps
                # backwards), measured round the circle
                rel = (tt - t0) % (2 * math.pi) if dt > 0 else (t0 - tt) % (2 * math.pi)
                if rel > abs(dt):
                    continue
            box.add(Cx + Ux * math.cos(tt) + Vx * math.sin(tt),
                    Cy + Uy * math.cos(tt) + Vy * math.sin(tt))


def _bezier_extrema(p):
    """Parameter values in (0,1) where a 1-D Bezier (2, 3 or 4 control values)
    turns."""
    if len(p) == 3:
        den = p[0] - 2 * p[1] + p[2]
        return [] if den == 0 else [t for t in ((p[0] - p[1]) / den,) if 0 < t < 1]
    a = -p[0] + 3 * p[1] - 3 * p[2] + p[3]
    b = 2 * (p[0] - 2 * p[1] + p[2])
    c = p[1] - p[0]
    if abs(a) < 1e-12:
        return [] if b == 0 else [t for t in (-c / b,) if 0 < t < 1]
    disc = b * b - 4 * a * c
    if disc < 0:
        return []
    r = math.sqrt(disc)
    return [t for t in ((-b + r) / (2 * a), (-b - r) / (2 * a)) if 0 < t < 1]


def _bezier_at(p, t):
    if len(p) == 3:
        return (1 - t) ** 2 * p[0] + 2 * (1 - t) * t * p[1] + t * t * p[2]
    return ((1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1]
            + 3 * (1 - t) * t * t * p[2] + t ** 3 * p[3])


def _bezier(box, m, pts):
    """An affine map takes a Bezier to the Bezier of its mapped control points,
    so map them first and find the extremes in the face frame."""
    q = [_apply(m, x, y) for x, y in pts]
    xs, ys = [p[0] for p in q], [p[1] for p in q]
    box.add(*q[0]); box.add(*q[-1])
    for t in _bezier_extrema(xs) + _bezier_extrema(ys):
        box.add(_bezier_at(xs, t), _bezier_at(ys, t))


_PATH_TOK = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def _path_tokens(d):
    """Commands and their numbers. An arc's two flags are single characters and
    may be written run together (`a1 1 0 011 1`), so they are read one digit at
    a time rather than by the number pattern."""
    out, i, n = [], 0, len(d)
    cmd, argi = None, 0
    while i < n:
        ch = d[i]
        if ch in " \t\r\n,":
            i += 1
            continue
        if ch.isalpha():
            out.append(ch); cmd, argi = ch.upper(), 0
            i += 1
            continue
        if cmd == "A" and argi % 7 in (3, 4) and ch in "01":
            out.append(float(ch)); argi += 1
            i += 1
            continue
        mt = _NUM.match(d, i)
        if not mt:
            i += 1                      # an unreadable character: skip it
            continue
        out.append(float(mt.group(0))); argi += 1
        i = mt.end()
    return out


def _arc(box, m, x1, y1, rx, ry, phi, fa, fs, x2, y2):
    """SVG F.6.5: endpoint to centre parameterisation, then the conic's exact
    extremes over the swept range."""
    if (x1, y1) == (x2, y2):
        return
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        box.add(*_apply(m, x2, y2))
        return
    cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        s = math.sqrt(lam); rx *= s; ry *= s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if fa == fs:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t0 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    box.add(*_apply(m, x2, y2))
    _conic(box, m, cx, cy, rx * cp, rx * sp, -ry * sp, ry * cp, t0, dt)


def _path_box(box, m, d):
    toks = _path_tokens(d or "")
    i, cmd = 0, None
    x = y = sx = sy = 0.0
    last_c = last_q = None             # reflected control points for S and T
    while i < len(toks):
        t = toks[i]
        if isinstance(t, str):
            cmd = t
            i += 1
            if cmd in "Zz":
                x, y = sx, sy
                last_c = last_q = None
                continue
        if cmd is None or cmd in "Zz":
            i += 1
            continue
        k = _ARITY[cmd.upper()]
        a = toks[i:i + k]
        if len(a) < k or any(isinstance(v, str) for v in a):
            break                       # a truncated command ends the path, as in SVG
        i += k
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == "M":
            x, y = ox + a[0], oy + a[1]
            sx, sy = x, y
            box.add(*_apply(m, x, y))
            cmd = "l" if rel else "L"   # implicit lineto after the first pair
            last_c = last_q = None
        elif C in "LHV":
            if C == "L":
                x, y = ox + a[0], oy + a[1]
            elif C == "H":
                x = (x if rel else 0.0) + a[0]
            else:
                y = (y if rel else 0.0) + a[0]
            box.add(*_apply(m, x, y))
            last_c = last_q = None
        elif C in "CS":
            if C == "C":
                c1 = (ox + a[0], oy + a[1]); c2 = (ox + a[2], oy + a[3]); e = (ox + a[4], oy + a[5])
            else:
                c1 = (2 * x - last_c[0], 2 * y - last_c[1]) if last_c else (x, y)
                c2 = (ox + a[0], oy + a[1]); e = (ox + a[2], oy + a[3])
            _bezier(box, m, [(x, y), c1, c2, e])
            last_c, last_q = c2, None
            x, y = e
        elif C in "QT":
            if C == "Q":
                c1 = (ox + a[0], oy + a[1]); e = (ox + a[2], oy + a[3])
            else:
                c1 = (2 * x - last_q[0], 2 * y - last_q[1]) if last_q else (x, y)
                e = (ox + a[0], oy + a[1])
            _bezier(box, m, [(x, y), c1, e])
            last_q, last_c = c1, None
            x, y = e
        elif C == "A":
            ex, ey = ox + a[5], oy + a[6]
            _arc(box, m, x, y, a[0], a[1], a[2], bool(a[3]), bool(a[4]), ex, ey)
            x, y = ex, ey
            last_c = last_q = None


def _shape_box(el, m):
    tag, box = _local(el.tag), _Box()
    if tag == "rect":
        w, h = _f(el, "width"), _f(el, "height")
        if w > 0 and h > 0:
            x, y = _f(el, "x"), _f(el, "y")
            for px, py in ((x, y), (x + w, y), (x + w, y + h), (x, y + h)):
                box.add(*_apply(m, px, py))
    elif tag == "circle":
        r = _f(el, "r")
        if r > 0:
            _conic(box, m, _f(el, "cx"), _f(el, "cy"), r, 0, 0, r)
    elif tag == "ellipse":
        rx, ry = _f(el, "rx"), _f(el, "ry")
        if rx > 0 and ry > 0:
            _conic(box, m, _f(el, "cx"), _f(el, "cy"), rx, 0, 0, ry)
    elif tag == "line":
        box.add(*_apply(m, _f(el, "x1"), _f(el, "y1")))
        box.add(*_apply(m, _f(el, "x2"), _f(el, "y2")))
    elif tag in ("polygon", "polyline"):
        v = [float(n) for n in _NUM.findall(el.get("points") or "")]
        for px, py in zip(v[0::2], v[1::2]):
            box.add(*_apply(m, px, py))
    elif tag == "path":
        _path_box(box, m, el.get("d"))
    return box


# ---- the walk ---------------------------------------------------------------

def _walk(root):
    """One pass over the drawing: each element's parent, its CTM (its own
    transform included) and the box of everything it paints, children
    included."""
    parent, ctm, boxes = {}, {}, {}

    def go(el, m, inert):
        m = _mul(m, parse_transform(el.get("transform")))
        ctm[el] = m
        # an inert subtree is still walked - a legend is a <text> with a
        # data-path, and is a row - but contributes nothing to any box
        inert = inert or _local(el.tag) in _INERT
        box = _Box() if inert else _shape_box(el, m)
        for ch in el:
            if not isinstance(ch.tag, str):
                continue                # a comment or processing instruction
            parent[ch] = el
            sub = go(ch, m, inert)
            if not inert:
                box.union(sub)
        boxes[el] = box
        return box
    go(root, _I, False)
    return parent, ctm, boxes


def face_entries(root, parent):
    """kit/swap.js `faceEntries`: every data-path, and every data-of whose
    path no element here draws as a part - in document order."""
    drawn = {e.get("data-path") for e in root.iter() if e.get("data-path") is not None}
    out = []
    for e in root.iter():
        if e is root or not isinstance(e.tag, str):
            continue                    # querySelectorAll never returns the root
        dp = e.get("data-path")
        if dp is not None:
            out.append((dp, e, False))
        elif e.get("data-of") is not None and e.get("data-of") not in drawn:
            out.append((e.get("data-of"), e, True))
    return out


def owner_path(el, parent):
    """kit/swap.js `ownerPath`: the nearest data-path or data-of, self first."""
    n = el
    while n is not None:
        p = n.get("data-path")
        if p is None:
            p = n.get("data-of")
        if p is not None:
            return p
        n = parent.get(n)
    return None


def face_tree(root, parent, entries=None):
    """kit/swap.js `faceTree` in Python: [(path, el, projected, parent_path)]
    in document order, one per path. See that function for why each rule is
    there; the order of the fallbacks is the kit's and must stay so."""
    entries = face_entries(root, parent) if entries is None else entries
    by_path = {}
    for path, el, projected in entries:
        by_path.setdefault(path, (path, el, projected))
    rows = []
    for path, el, projected in by_path.values():
        cut = path.rfind("/")
        up = by_path.get(path[:cut]) if cut >= 0 else None
        if up is None and projected:
            home = by_path.get(owner_path(parent.get(el), parent))
            if home is not None and home[0] != path:
                up = home
        if up is None and path.startswith("cutout:"):
            filled = by_path.get(path[7:])
            if filled is not None and filled[0] != path:
                up = filled
        dfor = el.get("data-for")
        if up is None and dfor:
            local = [t for t in dfor.split(" ") if t[:1] != "/"]
            single = len(local) == 1 or not el.get("data-ref")
            here = local[0] if single and local else None
            owner = by_path.get(here) if here else None
            if owner is not None and owner[0] != path:
                up = owner
            if up is None:
                body = by_path.get("chassis")
                if body is not None and body[0] != path:
                    up = body
        rows.append((path, el, projected, up[0] if up is not None else None))
    return rows


def _seat(path, rows_by_path):
    """The bay or cage whose occupant this row is part of, innermost first; None
    for the chassis's own rows. A bay's occupant is `<bay>/module` (render.py
    names it so, and nothing else), and a cage's is the element whose
    data-behaviour is `occupies`, its cage named by its data-for."""
    segs = path.split("/")
    for i in range(len(segs), 0, -1):
        q = "/".join(segs[:i])
        row = rows_by_path.get(q)
        if segs[i - 1] == "module" and i > 1:
            bay = rows_by_path.get("/".join(segs[:i - 1]))
            # a projection's module has no bay on this face; its data-of
            # `<bay>/module` is the same address render.py gave the seat
            if (bay is not None and bay[1].get("data-class") == "bay") \
                    or (row is not None and row[2]):
                return "/".join(segs[:i - 1])
        if row is not None and row[1].get("data-behaviour") == "occupies":
            host = (row[1].get("data-for") or "").split(" ")[0]
            if host:
                return host
    return None


def _cps(el, ctm):
    """Connection-point markers render.py hangs directly under a part's
    instance group: the point as written (`at`, the part's own frame) and
    where it lands on this face (`face`)."""
    out = {}
    m = ctm.get(el, _I)
    for ch in el:
        name = ch.get("data-cp")
        if not name:
            continue
        try:
            lx, ly = (float(v) for v in (ch.get("data-cp-at") or "").split())
        except ValueError:
            continue
        fx, fy = _apply(_mul(m, parse_transform(ch.get("transform"))), lx, ly)
        cp = {"at": [_num(lx), _num(ly)], "face": [_num(fx), _num(fy)]}
        if ch.get("data-cp-dir"):
            cp["dir"] = ch.get("data-cp-dir")
        if ch.get("data-cp-on"):
            cp["on"] = ch.get("data-cp-on")
        out[name] = cp
    return out


def face_elements(svg, config, view, configs=()):
    """The elements document for one compiled face, as a dict.

    `svg` is the root <svg> render.py wrote. `config` is the configuration that
    names the file and `configs` every configuration whose face it is (a face
    is written once and shared, #665)."""
    parent, ctm, boxes = _walk(svg)
    meta_el = next((e for e in svg if _local(e.tag) == "metadata"), None)
    try:
        meta = json.loads(meta_el.text) if meta_el is not None and meta_el.text else {}
    except ValueError:
        meta = {}
    vb = [_num(v) for v in _NUM.findall(svg.get("viewBox") or "")]
    tree = face_tree(svg, parent)
    by_path = {p: (p, el, proj) for p, el, proj, _ in tree}
    rows = []
    for path, el, projected, up in tree:
        row = {"of" if projected else "path": path, "parent": up,
               "box": boxes[el].out()}
        for key, attr in _FIELDS:
            v = el.get(attr)
            if v is not None and v != "":
                row[key] = v
        for key, attr in _LISTS:
            v = el.get(attr)
            if v:
                row[key] = [t for t in v.split(" ") if t]
        if el.get("data-inner"):
            row["inner"] = True
        cps = _cps(el, ctm)
        if cps:
            row["connection-points"] = cps
        seat = _seat(path, by_path)
        if seat is not None:
            row["seat"] = seat
        rows.append(row)
    return {
        "device": svg.get("data-device"),
        "device-version": meta.get("device-version"),
        "view": view,
        "config": config,
        "configs": sorted(set(configs) | {config}),
        "viewBox": vb,
        "source-sha256": meta.get("source-sha256"),
        "components": meta.get("resolved-components") or {},
        "generator": meta.get("generator"),
        "elements": rows,
    }


def dumps(doc):
    """Byte-deterministic: keys sorted, rows in document order, no spaces."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def elements_name(svg_name):
    """`agr110.ac.front.svg` -> `agr110.ac.front.elements.json`."""
    assert svg_name.endswith(".svg"), svg_name
    return svg_name[:-4] + ".elements.json"
