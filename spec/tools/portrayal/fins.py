"""The ribs of a housing that states a `chassis.section` (docs/modelling-a-device.md,
"A housing with a stepped end").

`chassis.fins` is a list of rib fields. A field is on the section's one edge that lies on the
top or the bottom of the box (`on`), runs along the length from `span[0]` to `span[1]` measured
from the left end, and puts a rib of thickness `rib` every `rib + gap` from the start of the
span. The ribs are slabs the full extent of the edge across the depth.

Two kinds of field, by what the stated size includes:

  inside    `core` is the height of the tallest rib: how far the casting's own surface is in
            from the edge. The edge is the tip line of the tallest rib, the box and the section
            keep their sizes, and the body is the section cut back to the core surface, with the
            ribs standing on it. `steps` lower the tips: each is a span and the height of the
            tips above the core surface in it.
  outside   `outside: true`, a `height` and no `core`. The edge is the casting's own surface and
            the ribs stand out of it by their step heights (the field's `height` without steps),
            beyond the box, by at most MAX_OUTSIDE.

This module is the one place that reads the key, so lint, the compiler and the tests cannot
disagree about where a rib is, how tall it is or where the silhouette runs.
"""

# how close two figures have to be to be the same, millimetres
TOL = 0.01
SIDES = ("top", "bottom")
# faces whose outline follows the steps, and which mirror the length
OUTLINE_FACES = ("front", "rear")
MAX_RIBS = 400
MAX_OUTSIDE = 60.0
DEFAULT_COLOR = "#3a3f45"


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def fields(chassis):
    """The entries of `chassis.fins` that are mappings, in the order written."""
    raw = (chassis or {}).get("fins")
    return [f for f in raw if isinstance(f, dict)] if isinstance(raw, list) else []


def is_outside(f):
    return f.get("outside") is True


def limit(f):
    """The height of the tallest rib of a field: its `core` inside, its `height` outside."""
    v = f.get("height") if is_outside(f) else f.get("core")
    return float(v) if _is_num(v) else None


def span(f):
    s = f.get("span")
    if (isinstance(s, (list, tuple)) and len(s) == 2 and all(_is_num(v) for v in s)):
        return float(s[0]), float(s[1])
    return None


def steps(f):
    """`[(from, to, height), ...]` as written, or None when there are none or one is not
    a span and a height."""
    raw = f.get("steps")
    if not isinstance(raw, list) or not raw:
        return None
    out = []
    for s in raw:
        if not isinstance(s, dict):
            return None
        sp, h = s.get("span"), s.get("height")
        if not (isinstance(sp, (list, tuple)) and len(sp) == 2 and all(_is_num(v) for v in sp)
                and _is_num(h)):
            return None
        out.append((float(sp[0]), float(sp[1]), float(h)))
    return out


def step_height(f, x):
    """The height of the tips at `x` along the length: the step whose half-open span
    `[from, to)` holds it, and the field's limit where it has no steps (or none holds `x`)."""
    st = steps(f)
    if st:
        for a, b, h in st:
            if a <= x < b:
                return h
    return limit(f)


def usable(f):
    """Whether a field has the numbers the geometry below needs: a side, a span that goes
    forward, a positive rib, gap and limit. Lint reports each of those that is wrong; the
    compiler and the viewer skip a field that is not usable."""
    sp = span(f)
    return (f.get("on") in SIDES and sp is not None and sp[0] < sp[1]
            and all(_is_num(f.get(k)) and f[k] > 0 for k in ("rib", "gap"))
            and limit(f) is not None and limit(f) > 0)


def rib_count(f):
    """How many whole ribs fit in the span: one every `rib + gap` from the start, the last one
    ending on or before the end."""
    sp = span(f)
    if sp is None or not _is_num(f.get("rib")) or not _is_num(f.get("gap")):
        return 0
    pitch = f["rib"] + f["gap"]
    if pitch <= 0:
        return 0
    return max(0, int((sp[1] - sp[0] + f["gap"] + TOL) // pitch))


def leftover(f):
    """How much of the span is left after the last rib, in millimetres."""
    n = rib_count(f)
    sp = span(f)
    if sp is None:
        return 0.0
    if n == 0:
        return sp[1] - sp[0]
    return sp[1] - sp[0] - ((n - 1) * (f["rib"] + f["gap"]) + f["rib"])


def ribs(f):
    """`[(x0, x1, height), ...]` for a usable field: where each rib runs along the length
    and how tall it stands. A rib takes the height of the step that holds its centre."""
    if not usable(f):
        return []
    a = span(f)[0]
    pitch = f["rib"] + f["gap"]
    out = []
    for i in range(rib_count(f)):
        x0 = a + i * pitch
        x1 = x0 + f["rib"]
        out.append((x0, x1, step_height(f, (x0 + x1) / 2.0)))
    return out


def count_all(chassis):
    return sum(rib_count(f) for f in fields(chassis))


def edge_count(pts, side, height):
    """How many horizontal edges of the section lie on the top or the bottom of the box."""
    y = 0.0 if side == "top" else height
    return sum(1 for a, b in zip(pts, pts[1:] + pts[:1])
               if a[1] == b[1] and abs(a[1] - y) <= 0.005 and a[0] != b[0])


def edge_extent(pts, side, height):
    """`(x0, x1)` across the depth of the section's edge on `side`, or None unless there is
    exactly one."""
    y = 0.0 if side == "top" else height
    runs = [(min(a[0], b[0]), max(a[0], b[0])) for a, b in zip(pts, pts[1:] + pts[:1])
            if a[1] == b[1] and abs(a[1] - y) <= 0.005 and a[0] != b[0]]
    return runs[0] if len(runs) == 1 else None


def reach(chassis):
    """`(top, bottom)`: how far the ribs of the outside fields stand beyond the box above and
    below it, in millimetres. (0, 0) for a housing none of whose ribs leave it."""
    out = {"top": 0.0, "bottom": 0.0}
    for f in fields(chassis):
        if usable(f) and is_outside(f):
            out[f["on"]] = max(out[f["on"]], max((h for _a, _b, h in ribs(f)), default=0.0))
    return out["top"], out["bottom"]


def tallest(f):
    """The height of the tallest rib that is actually drawn."""
    return max((h for _a, _b, h in ribs(f)), default=0.0)


# --- the silhouette of the front and rear --------------------------------------------------

def _tip_runs(f):
    """`[(x0, x1, height)]` of a field's tip line: its steps, or the whole span at its limit."""
    sp = span(f)
    st = steps(f)
    if st:
        return [(max(a, sp[0]), min(b, sp[1]), h) for a, b, h in st if min(b, sp[1]) > max(a, sp[0])]
    return [(sp[0], sp[1], limit(f))]


def edge_profile(chassis, side):
    """The silhouette of the housing along the length where it meets the top or the bottom of
    the box, as `[(x0, x1, y)]` runs covering `[0, width]` in the front's frame (x from the
    left end, y down from the top of the box).

    Outside every span of an inside field the casting is at its core; within a span it is the
    step's tip line, so the gaps between ribs are filled. An outside field stands out of the
    casting's own edge by its step heights.
    """
    w, h = float(chassis["width"]), float(chassis["height"])
    mine = [f for f in fields(chassis) if usable(f) and f["on"] == side]
    inside = next((f for f in mine if not is_outside(f)), None)
    edge = 0.0 if side == "top" else h
    base = edge
    if inside is not None:
        base = limit(inside) if side == "top" else h - limit(inside)
    runs = [(0.0, w, base)]
    for f in mine:
        for a, b, tip in _tip_runs(f):
            if is_outside(f):
                y = -tip if side == "top" else h + tip
            else:
                y = (limit(f) - tip) if side == "top" else (h - limit(f) + tip)
            nxt = []
            for x0, x1, yy in runs:
                if x1 <= a or x0 >= b:
                    nxt.append((x0, x1, yy))
                    continue
                if x0 < a:
                    nxt.append((x0, a, yy))
                nxt.append((max(x0, a), min(x1, b), y))
                if x1 > b:
                    nxt.append((b, x1, yy))
            runs = nxt
    return sorted(runs)


def _simplify(pts):
    """Drop a repeated point and a point on a straight run."""
    out = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    keep = []
    n = len(out)
    for i, b in enumerate(out):
        a, c = out[i - 1], out[(i + 1) % n]
        if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
            continue
        keep.append(b)
    return keep


def silhouette(face, chassis):
    """The outline of the front or the rear as a clockwise polygon of `(x, y)` in that face's
    own drawing frame, or None for a face the fins do not reshape. The rear is the front's
    outline mirrored across the length, wound the other way to stay clockwise."""
    if face not in OUTLINE_FACES:
        return None
    w = float(chassis["width"])
    top, bottom = edge_profile(chassis, "top"), edge_profile(chassis, "bottom")
    pts = []
    for x0, x1, y in top:
        pts += [(x0, y), (x1, y)]
    for x0, x1, y in reversed(bottom):
        pts += [(x1, y), (x0, y)]
    pts = _simplify(pts)
    if face == "rear":
        pts = [(w - x, y) for x, y in reversed(pts)]
    return pts


def zones(face, chassis):
    """The rectangles `(x0, y0, x1, y1)` of the front or the rear where the casting has been
    cut back to its core and the ribs stand: from the edge to the core, along each inside
    field's span. A part is not mounted there."""
    if face not in OUTLINE_FACES:
        return []
    w, h = float(chassis["width"]), float(chassis["height"])
    out = []
    for f in fields(chassis):
        if not usable(f) or is_outside(f):
            continue
        a, b = span(f)
        y0, y1 = (0.0, limit(f)) if f["on"] == "top" else (h - limit(f), h)
        out.append((w - b, y0, w - a, y1) if face == "rear" else (a, y0, b, y1))
    return out


# --- tones ---------------------------------------------------------------------------------

def _rgb(color):
    c = (color or DEFAULT_COLOR).strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return _rgb(DEFAULT_COLOR)


def tone(color, height, top):
    """The tone of a rib of `height` where the tallest in its field is `top`: the casting's
    colour lifted toward white, a taller rib lighter than a shorter one."""
    frac = 0.0 if not top else max(0.0, min(1.0, height / top))
    k = 0.12 + 0.2 * frac
    r, g, b = (round(v + (255 - v) * k) for v in _rgb(color))
    return f"#{r:02x}{g:02x}{b:02x}"
