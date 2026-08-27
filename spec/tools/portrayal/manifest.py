"""One reading of a device view for every tool.

A view is written in manufacturing order - panel, silkscreen, components - and
nested to say so. Readers do not want to know that; they want the lists. This
is the only place that knows the nesting, so when the shape changes it changes
here and nowhere else.
"""
import yaml
from pathlib import Path


# ONE READING OF A FILE, TOO, AND THE FAST ONE.
#
# Two separate costs were paying for the same bytes. The tools each parsed the
# library in their own process - devices_index, components_index and gaps_index
# between them did about 938 parses of 275 distinct files - and every one of
# those parses used PyYAML's pure-Python loader.
#
# libyaml does the same job on the same bytes 9.5x faster and returns an equal
# object; parsing the whole library went 1.95s to 0.21s. It ships with the
# PyYAML wheel on every platform this runs on, but the import is guarded because
# a source build without libyaml headers silently omits it, and a tool that dies
# on `from yaml import CSafeLoader` would be worse than a slow one.
#
# CACHED ON (path, mtime) so a file read twice in one process is parsed once,
# and a file rewritten mid-run is not answered from a stale parse.
#
# THE RESULT IS SHARED, NOT COPIED. Callers must treat it as read-only - which
# is true of every tool here, and was NOT true of one test helper, whose
# fixtures pop views off a real device. That one still parses for itself.
try:
    from yaml import CSafeLoader as _Loader
except ImportError:                        # pragma: no cover - no libyaml here
    from yaml import SafeLoader as _Loader

_CACHE = {}


def load_yaml(path):
    """Parse `path` once per process. Read-only: the result is shared."""
    path = Path(path)
    try:
        key = (str(path), path.stat().st_mtime_ns)
    except OSError:
        return None
    hit = _CACHE.get(key)
    if hit is None:
        with path.open("rb") as fh:
            hit = _CACHE[key] = yaml.load(fh, Loader=_Loader)
    return hit



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


def component_refs(device):
    """Every `ns/name@major` a device manifest names, from anywhere it can.

    A device depends on more than its own file, and the places a ref can hide
    are not obvious: a placement's `ref`, a bay's `accepts` list AND its
    `default`, a configuration's `bays` map and its `occupants` - which may be a
    bare string or a mapping carrying `ref`. Miss one and a dependency graph
    built on this silently under-reports, which for an incremental build means a
    stale drawing that looks fresh.
    """
    out = set()
    for view in (device.get("views") or {}).values():
        parts = view_parts(view or {})
        for q in parts["placements"]:
            if q.get("ref"):
                out.add(q["ref"].split(":")[0])
        for b in parts["bays"]:
            for a in (b.get("accepts") or []):
                out.add(a.split(":")[0])
            if b.get("default"):
                out.add(str(b["default"]).split(":")[0])
    for cfg in (device.get("configurations") or {}).values():
        for v in ((cfg or {}).get("bays") or {}).values():
            if v:
                out.add(str(v).split(":")[0])
        for v in ((cfg or {}).get("occupants") or {}).values():
            ref = v.get("ref") if isinstance(v, dict) else v
            if ref:
                out.add(str(ref).split(":")[0])
    return out
