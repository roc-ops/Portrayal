"""The two halves of a box that opens (docs/modelling-a-device.md, "A box that opens").

A node that mounts on a strand or a pedestal opens like a clamshell: a base that
stays where it is bolted and a lid that swings on a hinge. `chassis.halves` says
what the two are, and `regions[].half` says which of them each part of the open
drawing belongs to. This module is the one place that reads those keys, so lint,
the lock, the compiler and the exports cannot disagree about which half holds a
bay.

WHICH HALF HOLDS A BAY is derived, never authored: the half of the one region,
among those of the view that carries half regions, whose box holds the centre of
the bay's box. A bay with no `size` is judged by its `at`.
"""

FACES = ("front", "rear", "left", "right", "top", "bottom")
AXIS = {"front": "z", "rear": "z", "left": "x", "right": "x", "top": "y", "bottom": "y"}
OPPOSITE = {"front": "rear", "rear": "front", "left": "right", "right": "left",
            "top": "bottom", "bottom": "top"}
# the chassis dimension along each axis
DIMENSION = {"x": "width", "y": "height", "z": "depth"}
NAMES = ("base", "lid")

# THE SUM OF THE TWO `stands` MAY DIFFER FROM THE CHASSIS DIMENSION by this
# fraction of it before the sum is reported. A build-time choice: no source
# gives a tolerance, and a hinge and a gasket make a closed box a little taller
# than the sum of its two shells.
STANDS_TOLERANCE = 0.02


def declared(doc):
    """`chassis.halves` as written, `{}` where the device states none."""
    halves = (doc.get("chassis") or {}).get("halves")
    return halves if isinstance(halves, dict) else {}


def seam_axis(doc):
    """The axis the two halves are stacked along: the axis of the base's
    `outer` face. None where the base states none."""
    outer = (declared(doc).get("base") or {}).get("outer")
    return AXIS.get(outer)


def view_regions(view):
    """The regions of one view that state a `half`."""
    return [r for r in (view or {}).get("regions") or []
            if isinstance(r, dict) and r.get("half") is not None]


def _size(item):
    size = item.get("size")
    if isinstance(size, dict):
        return size.get("w"), size.get("h")
    if isinstance(size, (list, tuple)) and len(size) == 2:
        return size[0], size[1]
    return None


def _member_box(view, member_id):
    comps = (view or {}).get("components") or {}
    cutouts = ((view or {}).get("panel") or {}).get("cutouts") or []
    for item in list(comps.get("bays") or []) + list(cutouts):
        if isinstance(item, dict) and item.get("id") == member_id and item.get("at"):
            size = _size(item)
            if size and None not in size:
                return item["at"][0], item["at"][1], size[0], size[1]
    return None


def region_box(view, region):
    """`(x, y, w, h)` of a region: its stated `at` and `size`, else the union of
    the bays and cutouts it names in `members` that have a box. None where it
    has neither. The compiler draws a region by the same rule, but for the
    placements, whose size only a contract knows, which this does not read."""
    at, size = region.get("at"), region.get("size")
    if at and isinstance(size, dict) and "w" in size and "h" in size:
        return at[0], at[1], size["w"], size["h"]
    boxes = [b for b in (_member_box(view, m) for m in region.get("members") or []) if b]
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return x0, y0, x1 - x0, y1 - y0


def bay_centre(bay):
    at = bay.get("at")
    if not at:
        return None
    size = _size(bay)
    if size and None not in size:
        return at[0] + size[0] / 2.0, at[1] + size[1] / 2.0
    return float(at[0]), float(at[1])


def _holds(box, point):
    x, y, w, h = box
    return x <= point[0] <= x + w and y <= point[1] <= y + h


def bay_regions(view):
    """For one view that carries half regions: `{bay id: [ids of the half
    regions whose box holds the bay's centre]}`, every bay of the view in it."""
    boxes = [(r, region_box(view, r)) for r in view_regions(view)]
    out = {}
    for bay in ((view or {}).get("components") or {}).get("bays") or []:
        centre = bay_centre(bay)
        out[bay["id"]] = [r.get("id") for r, box in boxes
                          if centre and box and _holds(box, centre)]
    return out


def view_bay_halves(view):
    """`{bay id: half}` for the bays of one view that exactly one half region
    holds. Empty where the view carries no half region."""
    if not view_regions(view):
        return {}
    by_id = {r.get("id"): r.get("half") for r in view_regions(view)}
    return {bay: by_id[ids[0]] for bay, ids in bay_regions(view).items() if len(ids) == 1}


def bay_halves(doc):
    """`{view: {bay id: half}}` over the views that carry half regions."""
    out = {}
    for name, view in sorted((doc.get("views") or {}).items()):
        mapped = view_bay_halves(view)
        if mapped:
            out[name] = mapped
    return out


def published(doc):
    """What `configs.json` carries as `chassis.halves`: the two entries as
    written, in the order base, lid; absent (`None`) where the device has none."""
    halves = declared(doc)
    if not halves:
        return None
    names = [n for n in NAMES if n in halves] + sorted(n for n in halves if n not in NAMES)
    return {name: dict(halves[name]) for name in names}
