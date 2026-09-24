"""Tilted facets: the projection shared by render.py and lint.py.

A facet is a relief feature angled `deg` off the panel, facing up/down/left/right
(docs/superpowers/specs/2026-09-24-tilted-facets-design.md). A part `on` a facet keeps
its true size; what the front view shows is that size foreshortened by cos(deg)
along the facet's axis. Everything here is pure so the two consumers cannot disagree.
"""
import math


def cos_of(facet):
    return math.cos(math.radians(facet["deg"]))


def axis_of(facet):
    return "y" if facet["facing"] in ("up", "down") else "x"


def proud_extent(facet, w, h):
    """How far the facet's proud edge stands off: projected extent x tan(deg)."""
    span = h if axis_of(facet) == "y" else w
    return span * math.tan(math.radians(facet["deg"]))


def derived_profile(facet, w, h):
    """The wedge a facet compiles to, in the existing profile vocabulary.

    `up`: root (0 proud) at the upper edge, proud at the lower edge.
    `down`: the reverse. `left`: proud at the left edge; `right`: proud at the right.
    """
    t = proud_extent(facet, w, h)
    f = facet["facing"]
    if f == "up":
        return "profile-y", [[0.0, 0.0], [float(h), t]]
    if f == "down":
        return "profile-y", [[0.0, t], [float(h), 0.0]]
    if f == "left":
        return "profile", [[0.0, t], [float(w), 0.0]]
    return "profile", [[0.0, 0.0], [float(w), t]]


def scale_transform(facet):
    c = cos_of(facet)
    return f"scale(1,{c:.6g})" if axis_of(facet) == "y" else f"scale({c:.6g},1)"


def projected_box(at, w, h, rotate, facet):
    """(x0, y0, x1, y1) a part occupies on the face.

    Order as render.py applies it: rotate the true box about its true centre, then
    scale about the part's origin (0, 0) by cos along the facet axis, then translate.
    """
    x0, y0, x1, y1 = 0.0, 0.0, float(w), float(h)
    if rotate in (90, 270, -90):
        cx, cy = w / 2, h / 2
        x0, y0, x1, y1 = cx - h / 2, cy - w / 2, cx + h / 2, cy + w / 2
    if facet:
        c = cos_of(facet)
        if axis_of(facet) == "y":
            y0, y1 = y0 * c, y1 * c
        else:
            x0, x1 = x0 * c, x1 * c
    return (at[0] + x0, at[1] + y0, at[0] + x1, at[1] + y1)


def facet_of(contract, node):
    for f in (contract.get("relief") or {}).get("features") or []:
        if f.get("node") == node and f.get("facet"):
            return f["facet"]
    return None
