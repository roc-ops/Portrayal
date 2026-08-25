"""One reading of a device view for every tool.

A view is written in manufacturing order - panel, silkscreen, components - and
nested to say so. Readers do not want to know that; they want the lists. This
is the only place that knows the nesting, so when the shape changes it changes
here and nowhere else.
"""


def view_parts(view):
    """Flatten a canonical view into its lists. Missing sections are empty lists."""
    view = view or {}
    panel = view.get("panel") or {}
    comps = view.get("components") or {}
    return {
        "size": view.get("size"),
        "decor": panel.get("decor") or [],
        "cutouts": panel.get("cutouts") or [],
        "silkscreen": view.get("silkscreen") or [],
        "bays": comps.get("bays") or [],
        "placements": comps.get("placements") or [],
        "regions": view.get("regions") or [],
    }


def targets(value):
    """`for:` is one id or a list of them. Always hand back a list."""
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def split_target(t):
    """One `for:` target, split into (view, id).

    A bare id means "in this view" and gives (None, id) - that is what ~250
    bindings in the portfolio say and it has not changed meaning. A qualified
    'view/id' names a target in another view of the SAME device and gives
    (view, id): a front-panel PSU lamp indicates a PSU that lives in the rear.
    A list may mix the two forms.
    """
    if "/" in t:
        v, i = t.split("/", 1)
        return v, i
    return None, t


# the order a view's keys must appear in - the order the part is made
VIEW_KEY_ORDER = ("size", "panel", "silkscreen", "components", "regions")
PANEL_KEY_ORDER = ("decor", "cutouts")
COMPONENT_KEY_ORDER = ("bays", "placements")
