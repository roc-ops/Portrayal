"""One reading of a device view for every tool.

A view is written in manufacturing order - panel, silkscreen, components - and
nested to say so. Readers do not want to know that; they want the lists. This
is the only place that knows the nesting, so when the shape changes it changes
here and nowhere else.
"""
import math

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


def alias_names(device):
    """The `name` of every entry in a device's `aliases:`, in declared order.

    What configs.json and devices.json publish - the names an HCL or a search
    box would type. `kind`, `note` and `shared` stay in the manifest.
    """
    return [a["name"] for a in (device.get("aliases") or [])
            if isinstance(a, dict) and a.get("name")]


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


def _turn(v, rotate):
    """Rotate vector v by `rotate` degrees, SVG convention (x' = x cos - y sin,
    y' = x sin + y cos). Exact for the right angles the corpus uses."""
    deg = float(rotate or 0) % 360
    exact = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}
    c, s = exact.get(deg, (math.cos(math.radians(deg)), math.sin(math.radians(deg))))
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def seat_point(at, size, rotate, local):
    """Where `local` (a point in a placement's own frame) lands in the device
    frame, for a placement drawn translate(at) rotate(deg w/2 h/2).

    HERE AND NOT IN render.py because `presented_interface` below needs it: a
    composed aperture is itself a placement in its host's frame, drawn by that
    same transform, so the point it forwards has to go through it too. One
    helper for both, so the rotation is written once; render.py imports it."""
    cx, cy = size["w"] / 2, size["h"] / 2
    dx, dy = _turn((local[0] - cx, local[1] - cy), rotate)
    return [round(at[0] + cx + dx, 4), round(at[1] + cy + dy, 4)]


def _seat_out(contract, point):
    """The `out` of the relief feature a connection point sits `on:`, or 0.0.

    A point with no `on:` sits on the part's own face. One whose `on:` names
    nothing, or a feature with no `out`, also answers 0.0 here - lint L106
    refuses both, and a renderer that guessed a depth would hide the error L106
    exists to report.
    """
    node = point.get("on")
    if not node:
        return 0.0
    for f in ((contract.get("relief") or {}).get("features") or []):
        if f.get("node") == node and f.get("out") is not None:
            return float(f["out"])
    return 0.0


def presented_interface(contract, resolve):
    """What a receptacle presents to a module, and where the module mates into it.

    Returns (interface, mate_at, lift)

    THE LIFT IS THE HOST'S PROTRUSION AT THAT POINT, and it is why this returns
    three things now. A forwarded point belongs to a composed aperture, and that
    aperture's `lift` is how far off the host's own face it stands. An occupant
    positioned by the point and not displaced by the lift is seated at the panel
    plane behind whatever the aperture is mounted on. A host that presents its
    own point forwards nothing, and lifts only when that point - `mate`, or the
    one `interface-at` names - sits `on:` a relief feature, by that feature's
    `out`: a boot on a plug stands on the plug body's rear face.

    WHY THIS LOOKS THROUGH `parts`. Seating an optic worked end to end and was
    used by exactly one configuration on one device, out of 7,058 ports. Not
    because authors had not got to it, but because on most ports it could not be
    written: a port that PLACES `std/sfp-ganged` can host, and a port that
    COMPOSES the same aperture inside a vendor cage cannot, because the checks
    read only the wrapper's own top-level `interface` and its own `mate` point.

    The knowledge was never missing. It sat one level down, in the standard
    aperture the wrapper wraps, where nothing looked.

    THE FORWARDED POINT IS NOT A NEW CLAIM ABOUT GEOMETRY, and the corpus says
    so: of the thirteen port wrappers that compose an aperture carrying an
    interface, TEN already declare a connection-point at exactly the position
    this computes - `qsfp28-cage`'s own `net` is at [9.5, 9.0] and the aperture's
    `mate`, offset by the part's `at`, lands on [9.5, 8.99]. The authors had
    already put the point in the right place. What they could not do was give it
    the name the mating code looks for.

    `resolve` takes a component ref and returns its contract, or None. It is
    passed in because lint and render each have their own resolver and neither
    should grow a second one.
    """
    cps = contract.get("connection-points") or {}
    mate = cps.get("mate")
    # WHICH POINT, AND HOW FAR PROUD (pluggables D, D3). A plug mates INTO its
    # receptacle at `mate` but presents its own interface - `lc-plug` - at its
    # REAR, where a boot seats; `interface-at` names that point (default
    # `mate`, which is every contract written before it). The point's `on:`
    # names the relief feature it sits on, and the seat stands off by that
    # feature's `out`, which is ABSOLUTE from this part's own face - a
    # feature's `lift` is where it starts, not where its rear face is. Without
    # either key this is exactly the old answer: `mate`, 0.0.
    point = cps.get(contract.get("interface-at") or "mate")
    if contract.get("interface") and point:
        return contract["interface"], list(point["at"]), _seat_out(contract, point)
    # A wrapper may compose several parts - a duplex adapter holds two bores -
    # and only one aperture can be the thing a module seats into. Take the first
    # that presents an interface, in declaration order, and leave the multi-mate
    # case alone: `lc-duplex-adapter` composes two LC bores and its own point is
    # their midpoint, which is a fibre landing on a ferrule rather than a module
    # entering a cage. Different question, not this one.
    cores = []
    for part in (contract.get("parts") or []):
        core = resolve(part.get("ref")) if part.get("ref") else None
        if not core or not core.get("interface"):
            continue
        cm = (core.get("connection-points") or {}).get("mate")
        if not cm:
            continue
        # THROUGH THE PART'S OWN PLACEMENT, rotation and all. `at + mate`
        # was right only for an unturned part: every generic transceiver
        # composes std/lc-bore@3 at `rotate: 180` (tongue up), and the plain
        # sum put a plug seated in that bore 1.6 mm off the bore's centre in
        # y - (x, 4.10) where the bore, and the part's own `optical` point,
        # is at (x, 5.70). The part is drawn translate(at) rotate(deg w/2
        # h/2) with its own contract's size, so its mate lands by seat_point.
        at = part.get("at") or [0, 0]
        cores.append((core["interface"],
                      seat_point(at, core["size"], part.get("rotate"), cm["at"]),
                      float(part.get("lift") or 0)))
    if len(cores) == 1:
        return cores[0]
    return contract.get("interface"), (list(mate["at"]) if mate else None), 0.0


def resolve_views(device, cfg):
    """{face: (view-name, view)} for one configuration.

    A view carrying `face:` is a VARIANT and appears only when bound, because
    rendering it unbound would emit `<device>.<config>.front-12-lff.svg` - a
    file named after a panel rather than a face, which no consumer asks for.
    Everything else keeps its own name, so a device with no bindings behaves
    exactly as it did before this existed.
    """
    views = device.get("views") or {}
    out = {}
    for face, vname in ((cfg or {}).get("views") or {}).items():
        if vname in views:
            out[face] = (vname, views[vname] or {})
    for vname, v in views.items():
        if (v or {}).get("face"):
            continue
        out.setdefault(vname, (vname, v or {}))
    return out


def config_airflow(device, cfg):
    """The airflow one configuration is built with, or None.

    `configurations.<name>.airflow` is stated only where a build differs from
    the chassis (L91), so the chassis value is the answer everywhere else. The
    SVG root's `data-airflow`, the `configs[].airflow` in `<device>.configs.json`
    and the DCIM export all read it here, so the drawing, the index and the
    export cannot come to disagree about which way a build breathes. The value
    is the library's own vocabulary - front-to-back, back-to-front, side,
    passive - and None where the device states nothing.
    """
    return ((cfg or {}).get("airflow")
            or ((device or {}).get("chassis") or {}).get("airflow")
            or None)


def config_power(device, cfg):
    """The supply feeds one configuration is built with, as a sorted list.

    Resolved exactly as `config_airflow` is - the configuration's `power`, else
    the chassis's (L117) - so the drawing's `data-power`, `configs[].power` and
    `options.power` cannot disagree. ALWAYS A LIST, where airflow is a string,
    because a build can be fed two ways at once (a fixed box with an AC inlet and
    a DC terminal both fitted); a consumer that wants one word reads `[0]` of a
    one-item list rather than branching on a type. Empty where nothing is stated.
    """
    v = ((cfg or {}).get("power")
         or ((device or {}).get("chassis") or {}).get("power"))
    if not v:
        return []
    return sorted({v} if isinstance(v, str) else set(v))


# THE CONFIGURATIONS A BUYER CAN ACTUALLY GET. An `example` is somebody's
# illustration and a `model` a teaching build (#51), so neither may widen what
# the device is said to be offered with. A device that declares no kinds at all
# still has builds, so all of them count there rather than none.
OFFERED_KINDS = {"orderable", "base"}


def device_options(device):
    """What a device can be bought with: `{"power": [...], "airflow": [...]}`.

    The union over its offered configurations (OFFERED_KINDS) of each one's
    resolved feed and airflow, sorted, so "does this switch come in DC?" and
    "is there a back-to-front build?" are one lookup instead of a walk over the
    configurations - which is what the tools filtering an HCL were doing, by
    parsing names (#513). A device with no configurations answers from the
    chassis alone. Only what is MODELLED is offered: a back-to-front SKU the
    vendor sells and nobody has drawn is not in the list, and its absence is
    what a gap records.
    """
    cfgs = (device or {}).get("configurations") or {}
    offered = [c or {} for c in cfgs.values()
               if (c or {}).get("kind") in OFFERED_KINDS]
    if not offered:
        offered = [c or {} for c in cfgs.values()] or [{}]
    power, airflow = set(), set()
    for c in offered:
        power.update(config_power(device, c))
        a = config_airflow(device, c)
        if a:
            airflow.add(a)
    return {"power": sorted(power), "airflow": sorted(airflow)}

# --- occupants keyed inside a seated module (#484, R2) -----------------------
#
# A configuration's `occupants:` may key a cage on a card seated in a bay by the
# card's MODULE-LESS path - `front-6/xg0` - the convention its nested `bays:`
# keys already use. The build finds those keys from the module it is drawing
# (module_key_prefix, occupants_under); lint finds the module from the key
# (nested_key_host). Both read a bay's occupant with seated_ref and name a
# seated occupant with occupant_local_id, so the two directions cannot come to
# disagree about which module a key reaches or which occupant a chained key
# names.

def module_key_prefix(path):
    """The module-less key prefix a configuration uses for what is in the
    module drawn at `path` - `front-6/module` -> `front-6`, `riser-1/module/
    slot-1/module` -> `riser-1/slot-1` - or None when `path` is not a module
    seated in a bay. The same stripping as a nested bay's `bay_path`."""
    if not path or not path.endswith("/module"):
        return None
    return (path[:-len("/module")] + "/").replace("/module/", "/")[:-1]


def seated_ref(cfg_bays, bay_path, bay):
    """What a configuration seats in the bay at module-less `bay_path`: its own
    `bays:` entry, else the bay's `default`; empty means empty."""
    return (cfg_bays or {}).get(bay_path, (bay or {}).get("default"))


def occupant_spec(key, spec):
    """An `occupants:` value as a dict with a `ref`, or ValueError naming the key."""
    spec = {"ref": spec} if isinstance(spec, str) else spec
    if not isinstance(spec, dict) or not spec.get("ref"):
        raise ValueError(f"occupants/{key}: names no component - give a ref, "
                         "or {ref: ..., attrs: ...}")
    return spec


def occupant_local_id(host_id, spec):
    """The id an occupant seated on `host_id` is drawn under: its own `id:`,
    else `<host>-occupant` - what a chained key names."""
    return spec.get("id") or f"{host_id}-occupant"


def occupants_under(prefix, occupants):
    """{local host id: (key, spec)} for the `occupants:` keys that name a host
    directly in the module whose key prefix is `prefix` - `front-6/xg0` under
    `front-6`, but not `front-6/slot-1/xg0`, which belongs to the module in
    that nested bay."""
    out = {}
    for key, spec in (occupants or {}).items():
        rest = key[len(prefix) + 1:] if key.startswith(prefix + "/") else None
        if rest and "/" not in rest:
            out[rest] = (key, occupant_spec(key, spec))
    return out


def chained_occupant_ref(host_id, occupants, terminal):
    """Resolve `host_id` - a host id a caller has already found is not itself
    a terminal - to the ref of whatever hosts it, by walking `occupants`
    ({key: spec}, all in the SAME scope: a configuration's device-level
    occupants for a device-level key, or `occupants_under` a module's prefix
    for a nested one) for the entry whose own produced id
    (`occupant_local_id`) equals it - a plug named by the optic's key, a boot
    named by the plug's.

    `terminal(id)` answers a ref for anything the chain can ground on that is
    not itself a chained occupant - a placement, or inside a seated module,
    one of the module's own parts - or None to keep walking.

    Returns the ref of the entry that immediately hosts `host_id`: one hop,
    which is the whole answer `_mate_check` needs, because that entry's own
    host is that entry's own problem, checked when IT is linted. The walk
    continues past that hop only to confirm the chain is well-founded - it
    stops at a terminal, or a dead end (again, not this key's problem) - so
    that a chain which instead loops back on itself is caught here rather
    than left to recurse forever the day two keys name each other.

    Raises KeyError(host_id) when nothing in `occupants` produces `host_id`
    at all, and ValueError(id) naming the id the chain revisits."""
    match = next((k for k, spec in occupants.items()
                  if occupant_local_id(k, spec) == host_id), None)
    if match is None:
        raise KeyError(host_id)
    ref = occupants[match]["ref"]
    seen, cur = {host_id}, match
    while terminal(cur) is None:
        if cur in seen:
            raise ValueError(cur)
        seen.add(cur)
        nxt = next((k for k, spec in occupants.items()
                    if occupant_local_id(k, spec) == cur), None)
        if nxt is None:
            break
        cur = nxt
    return ref


def nested_key_host(key, device, cfg, resolve):
    """Walk a module-less `occupants:` key down the configuration's bays to its
    host: (host_ref, module_ref, module_path). `resolve(ref)` returns a
    contract or None. Raises ValueError saying what the key failed to reach.

    A chained key (`front-6/xg0-occupant`) names the occupant seated on
    another key of the same module, and resolves to that occupant's ref -
    however many hops long, via `chained_occupant_ref`."""
    segs = key.split("/")
    host_id = segs[-1]
    bays = {b["id"]: b for _face, (_n, v) in resolve_views(device, cfg).items()
            for b in view_parts(v)["bays"]}
    if segs[0] not in bays:
        raise ValueError(f"occupants/{key}: {segs[0]!r} is no bay in any view "
                         "this configuration draws")
    cfg_bays = (cfg or {}).get("bays") or {}
    bay_path, path = segs[0], f"{segs[0]}/module"
    ref = seated_ref(cfg_bays, bay_path, bays[segs[0]])
    for seg in segs[1:-1]:
        c = resolve(ref) if ref else None
        nb = ((c or {}).get("bays") or {}).get(seg)
        if not isinstance(nb, dict):
            raise ValueError(f"occupants/{key}: names no cage - {bay_path!r} "
                             f"seats {ref or 'nothing'}, which has no bay {seg!r}")
        bay_path, path = f"{bay_path}/{seg}", f"{path}/{seg}/module"
        ref = seated_ref(cfg_bays, bay_path, nb)
    if not ref:
        raise ValueError(f"occupants/{key}: names no cage - bay {bay_path!r} is "
                         "empty in this configuration")
    module = resolve(ref)
    if module is None:
        raise ValueError(f"occupants/{key}: {bay_path!r} seats {ref}, which "
                         "does not resolve")
    parts = {q.get("id"): q for q in module.get("parts") or []}
    if host_id in parts:
        return parts[host_id]["ref"], ref, path
    mine = {h: s for h, (_k, s) in
            occupants_under(module_key_prefix(path), (cfg or {}).get("occupants")).items()}
    try:
        host_ref = chained_occupant_ref(
            host_id, mine, lambda h: (parts[h]["ref"] if h in parts else None))
    except (KeyError, ValueError):
        raise ValueError(f"occupants/{key}: names no cage on {ref} seated at "
                         f"{bay_path!r}")
    return host_ref, ref, path
