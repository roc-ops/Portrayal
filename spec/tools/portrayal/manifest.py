"""One reading of a device view for every tool.

A view is written in manufacturing order - panel, silkscreen, components - and
nested to say so. Readers do not want to know that; they want the lists. This
is the only place that knows the nesting, so when the shape changes it changes
here and nowhere else.
"""
import functools
import math
import re

import yaml
from pathlib import Path

from portrayal.faces import DIRECTIONS, face_ref


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
        "passes": view.get("passes") or [],
        "guides": view.get("guides") or [],
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
VIEW_KEY_ORDER = ("size", "open-frame", "panel", "silkscreen", "components", "passes", "guides", "regions")
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


# Approximate glyph metrics, in em. Real faces differ by a few percent, which is
# why L21 carries a tolerance rather than pretending these are exact.
CAP_EM, DESC_EM, ADV_EM = 0.72, 0.10, 0.60


def text_extent(m):
    """Bounding box of a text mark, (x0, y0, x1, y1) in view mm.

    HERE AND NOT IN lint.py, where L21 first measured with it, because
    render.default_seat_turn asks the same question of a legend (#829), and
    two copies of the glyph metrics would be one edit from disagreeing.

    `at` is the BASELINE, not the top edge - which is the whole reason L21
    exists: 2.2mm digits anchored 1.2mm below a port still reached up into it.

    A ROTATED MARK RUNS ALONG A DIFFERENT AXIS, and measuring it as if it did not
    is how a label printed neatly down a chassis's right edge gets reported as
    running off the face: its length was being added to x, where the metal ends,
    instead of to y, where there is room. The same arithmetic accused rotated
    module legends of painting over the modules beside them. Only the right
    angles are handled - anything else is rare enough that the unrotated box is
    the safer approximation, and being slightly too generous costs a missed
    warning rather than a fabricated one."""
    x, y = m["at"]
    fs = m.get("font-size", 2.2)
    w = len(str(m["text"])) * fs * ADV_EM
    up, down = fs * CAP_EM, fs * DESC_EM
    # THE DEFAULT HAS TO BE THE ONE THE RENDERER USES. render.py draws an
    # unanchored silkscreen mark CENTRED on its `at` (render.py:880); this read
    # it as running rightward from `at`, so every extent check on the 433 marks
    # in this library that state no anchor was off by half a text width - in the
    # direction that hides an overlap on the left and invents one on the right.
    # A mark then lints as one thing and draws as another, and no rule reports
    # the difference because both halves are working from their own assumption.
    anchor = m.get("anchor", "middle")
    lead = w if anchor == "end" else (w / 2 if anchor == "middle" else 0.0)
    rot = int(m.get("rotate", 0)) % 360
    # WHICH SIDE THE CAPS FALL ON is the renderer's `rotate(deg x y)` applied to
    # an upright mark, whose caps point up (-y). SVG turns clockwise on screen,
    # so at 90 up becomes +x and the caps sit RIGHT of the baseline; at 270
    # (-90, reading bottom to top) they sit LEFT. This had the two swapped, so
    # an upright legend set against a part's left edge - XM-7380's CONSOLE, its
    # glyphs painting 1.2mm clear of the USB port - was reported as buried in
    # it, and a legend whose caps really did reach into a part went unreported.
    if rot == 90:            # runs downward, cap side to the RIGHT of the baseline
        return (x - down, y - lead, x + up, y - lead + w)
    if rot == 270:           # runs upward, cap side to the LEFT
        return (x - up, y + lead - w, x + down, y + lead)
    if rot == 180:           # runs leftward, cap side below
        return (x - w + lead, y - down, x + lead, y + up)
    return (x - lead, y - up, x - lead + w, y + down)


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
    """The rear of the relief feature a connection point sits `on:`, or 0.0.

    An `out` feature's rear is its `out`, absolute from the part's face. A
    `cyl` feature's is its far end, `lift + cyl`: the lift is where it starts
    and the cyl its length from there.

    A point with no `on:` sits on the part's own face. One whose `on:` names
    nothing, or a feature with neither `out` nor `cyl`, also answers 0.0 here -
    lint L106 refuses both, and a renderer that guessed a depth would hide the
    error L106 exists to report.

    A point may instead carry a numeric `seat-out`: the plane itself, absolute
    from the part's face, where no drawn feature has its rear there (a coax
    jack's mated plane lies partway along a plain barrel). L106 refuses a
    point with both it and `on:`.
    """
    if point.get("seat-out") is not None:
        return float(point["seat-out"])
    node = point.get("on")
    if not node:
        return 0.0
    for f in ((contract.get("relief") or {}).get("features") or []):
        if f.get("node") != node:
            continue
        if f.get("out") is not None:
            return float(f["out"])
        if f.get("cyl") is not None:
            return float(f.get("lift") or 0.0) + float(f["cyl"])
    return 0.0


def presented_point(contract):
    """The connection point `contract` presents its interface at: the one
    `interface-at` names, default `mate` - or None when that point is not
    declared (L106's error). THE ONE READING of which point is presented, for a
    part that presents its own interface and for a core a wrapper forwards
    (#671): a plug presents at its boot point, and a bezel composing a core
    must present where the core does, not at the core's `mate`."""
    cps = contract.get("connection-points") or {}
    return cps.get(contract.get("interface-at") or "mate")


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
    rear (its `out`, or a `cyl`'s `lift + cyl`): a boot on a plug stands on the
    plug body's rear face.

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
    # either key this is exactly the old answer: `mate`, 0.0. A `cyl`
    # feature has no `out`; its rear is its far end, `lift + cyl`.
    point = presented_point(contract)
    if contract.get("interface") and point:
        return contract["interface"], list(point["at"]), _seat_out(contract, point)
    part = forwarded_part(contract, resolve)
    if part is not None:
        core = resolve(part["ref"])
        # THE CORE'S PRESENTED POINT, not its `mate` (#671): where the core
        # presents placed bare - `interface-at`, default `mate` - is where it
        # presents through the wrapper, position and seat out alike.
        cm = presented_point(core)
        # THROUGH THE PART'S OWN PLACEMENT, rotation and all. `at + mate`
        # was right only for an unturned part: every generic transceiver
        # composes std/lc-bore@3 at `rotate: 180` (tongue up), and the plain
        # sum put a plug seated in that bore 1.6 mm off the bore's centre in
        # y - (x, 4.10) where the bore, and the part's own `optical` point,
        # is at (x, 5.70). The part is drawn translate(at) rotate(deg w/2
        # h/2) with its own contract's size, so its mate lands by seat_point.
        #
        # AND THROUGH THE CORE'S OWN SEAT OUT. The part's `lift` is how far the
        # core stands off the wrapper's face; the core's mate may itself sit
        # `on:` a feature whose rear stands further out still. A coax jack's
        # mate sits on the face a mated plug's coupling front reaches, and a
        # bezel that composes the jack must present it there too, or a plug
        # seated through the bezel stands nearer the panel than the same plug
        # seated in the bare jack. The same sum presented_turn makes for the
        # part's `rotate`.
        at = part.get("at") or [0, 0]
        return (core["interface"],
                seat_point(at, core["size"], part.get("rotate"), cm["at"]),
                float(part.get("lift") or 0) + _seat_out(core, cm))
    return contract.get("interface"), (list(mate["at"]) if mate else None), 0.0


def forwarded_part(contract, resolve):
    """Which of `contract`'s `parts:` entries `presented_interface` forwards
    its mate point from, or None.

    The same selection `presented_interface` makes when it has no top-level
    `interface` of its own: a wrapper may compose several parts - a duplex
    adapter holds two bores - and only one aperture can be the thing a
    module seats into, so this takes the interfaced part ONLY when it is
    the single one found, in declaration order, and leaves the multi-mate
    case alone (a duplex adapter's own point is its bores' midpoint, a
    fibre landing rather than a module entering a cage - different
    question). Exposed as its own function so a caller can ask a further
    question of THAT SPECIFIC part - here, whether it sits `on` a facet -
    without re-deriving which one presented_interface would pick.
    """
    if contract.get("interface") and presented_point(contract):
        return None
    hits = []
    for part in (contract.get("parts") or []):
        core = resolve(part.get("ref")) if part.get("ref") else None
        if not core or not core.get("interface"):
            continue
        # a core is forwarded by the point it presents at (#671); one whose
        # `interface-at` names no point presents nowhere, and is not forwarded
        # to its `mate` instead
        if not presented_point(core):
            continue
        hits.append(part)
    return hits[0] if len(hits) == 1 else None


def spanned_slots(contract, resolve, connectors):
    """The ids of the `parts:` entries this contract's OWN slot takes the place
    of - what the caps work calls its BORES (B3, docs/pluggables-caps-design.md,
    "The duplex host"). [] for everything else.

    An interface in spec/schemas/connectors.yaml may declare that it SPANS
    another: `lc-duplex` spans two `lc` bores, because one duplex connector
    fills both of them. A contract presenting a spanning interface and
    composing the parts it spans therefore holds TWO LEVELS OF SLOT FOR ONE
    PIECE OF HARDWARE - its own, and the bores - and the two are mutually
    exclusive: filling either level means the other is not offered, and filling
    both is an error the build and lint each refuse.

    The ids are LOCAL to this contract, because that is how a configuration
    addresses them: the bore beside a slot keyed `bay-1/lc01` is `bay-1/lc01/1`.

    ONLY A CONTRACT PRESENTING THE SPANNING INTERFACE AS ITS OWN names bores. A
    wrapper that FORWARDS a spanned slot (P2, `render._forwarded_part`) is not
    the host of these parts - they sit one level further down than any id a key
    at the wrapper's level could name - and it publishes no second slot for them.
    """
    iface = (contract or {}).get("interface")
    spans = ((connectors or {}).get(iface) or {}).get("spans") if iface else None
    if not spans:
        return []
    want = spans.get("interface")
    out = []
    for part in contract.get("parts") or []:
        if not part.get("id") or not part.get("ref"):
            continue
        core = resolve(part["ref"])
        if core and core.get("interface") == want:
            out.append(part["id"])
    return out


@functools.lru_cache(maxsize=1)
def slot_interfaces():
    """(every interface a part can present AS A SLOT, the connector registry):
    the pluggables families' interfaces (a cage) and spec/schemas/
    connectors.yaml's (a connector slot) - the two registries render.slot_entry
    answers from. Empty on a broken checkout."""
    schemas = Path(__file__).resolve().parents[2] / "schemas"
    try:
        fams = (yaml.safe_load((schemas / "pluggables.yaml").read_text()) or {}).get("families") or {}
        conns = (yaml.safe_load((schemas / "connectors.yaml").read_text()) or {}).get("interfaces") or {}
    except (OSError, yaml.YAMLError):
        return frozenset(), {}
    return frozenset({f.get("interface") for f in fams.values() if f.get("interface")} | set(conns)), conns


def slot_in_slot(carrier, host_id, resolve):
    """True when the part `host_id` of `carrier` is a slot that is NOT one of
    `carrier`'s own when `carrier`, placed, is itself a slot - a cage
    wrapper's composed aperture (B3, docs/pluggables-caps-design.md, "A slot
    inside a slot").

    A wrapper presents the aperture it composes as its own interface
    (presented_interface looks through it), so the frame that places the
    wrapper already publishes that aperture as a slot, at the wrapper's key.
    Keying the aperture again one level down names the same opening twice;
    the build refuses it, L12 reports it, and the kit never offers it. The one
    slot that may sit inside a slot is a BORE a spanning slot names
    (spanned_slots): the duplex adapter's `1` and `2`, the other level of
    the same opening, which L115 keeps exclusive of it.

    `carrier` is the contract of the instance holding `host_id` - a device
    placement, a part a component composes, or a seated occupant. A module
    seated in a bay is never asked (slot_in_slot_at): a bay is not a slot, so
    the card that is one cage keeps its cage."""
    if not carrier:
        return False
    registered, conns = slot_interfaces()
    if presented_interface(carrier, resolve)[0] not in registered:
        return False
    part = next((q for q in carrier.get("parts") or [] if q.get("id") == host_id), None)
    core = resolve(part["ref"]) if part and part.get("ref") else None
    if not core or presented_interface(core, resolve)[0] not in registered:
        return False
    return host_id not in spanned_slots(carrier, resolve, conns)


def slot_in_slot_at(path, carrier, host_id, resolve):
    """slot_in_slot for the instance drawn at `path` - THE GATE both the build
    (render._seat_nested_occupants) and the resolver L12 calls
    (nested_key_host) apply, so the two cannot come to disagree about which
    keys it refuses. A module in a bay (`.../module`) is never a placed slot;
    every other instance is asked - a device placement, a composed part, and
    an OCCUPANT too: an optic that forwards one bore (generic/sfp-lc-simplex@2)
    is a slot at its own key, `front-2/xg0-occupant`, and its bore is not a
    second one."""
    if not path or path.endswith("/module"):
        return False
    return slot_in_slot(carrier, host_id, resolve)


def slot_in_slot_error(key, carrier_key, host_id):
    """The refusal for slot_in_slot, one wording for the build and L12."""
    return ValueError(
        f"occupants/{key}: {host_id!r} is the aperture the slot {carrier_key!r} "
        f"composes, not a slot of its own - key {carrier_key!r} instead (a slot "
        "inside a slot is only one of the bores a spanning slot names)")


# THE CANONICAL AXIS A SPANNING CONNECTOR IS DRAWN ON: ACROSS, along +x, with
# the first spanned part on the left. Every duplex part in the library is drawn
# that way, and a host whose own pair runs some other way publishes the turn
# that carries the one onto the other (B3, docs/pluggables-caps-design.md,
# "The duplex host").
CANONICAL_SPAN_AXIS = 0


def spanning_axis(contract, resolve, connectors):
    """THE TURN A SPANNING OCCUPANT IS DRAWN AT ON THIS HOST, in degrees, or
    None where this contract hosts no spanning slot.

    A duplex connector is ONE moulding with two ferrules on an axis, and it
    cannot turn itself: a seated part takes its host's rotation
    (`render.solve_seat`, D3). So the axis has to come from the host, and the
    two adapters in the library disagree about it - `common/lc-duplex-adapter`
    puts its bores SIDE BY SIDE and `common/lc-duplex-v-adapter` STACKS them,
    which its own provenance calls "the same duplex pair stood on end". One
    part drawn on one axis is right on one of them and wrong on the other
    unless the host says which way round its pair runs.

    DERIVED FROM THE BORES, never from a name or a ref: the direction from the
    FIRST spanned part's composed mate point to the LAST, snapped to the right
    angle it lies nearest, is the direction the canonical +x axis has to be
    carried onto. Composed mate points and not `at`, for L116's reason - a
    stacked pair and a side-by-side pair differ in box, axis and rotation, and
    their mate points do not.

    The ORDER is the `parts:` declaration order (`spanned_slots`), so the
    answer distinguishes a pair running left-to-right from one running
    right-to-left. That matters for a part whose two halves are not
    interchangeable - a duplex plug's `a` half carries the fibre its host's
    first bore does - and is invisible on a symmetric one like a dust cap.

    This is the turn IN THE CONTRACT'S OWN FRAME. A placement of the contract
    adds its own `rotate` on top, which is a sum because both are rotations of
    the same plane.
    """
    ids = spanned_slots(contract, resolve, connectors)
    if len(ids) < 2:
        return None
    places = {q.get("id"): q for q in (contract.get("parts") or [])}
    pts = []
    for bid in ids:
        q = places.get(bid) or {}
        core = resolve(q.get("ref")) or {}
        cm = (core.get("connection-points") or {}).get("mate")
        if not cm or not core.get("size"):
            return None                 # a bore with no mate point is L58/L1's
        pts.append(seat_point(q.get("at") or [0, 0], core["size"],
                              q.get("rotate"), cm["at"]))
    dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
    if dx == 0 and dy == 0:
        return None                     # two bores on one point is L116's
    if abs(dx) >= abs(dy):
        lies_at = 0 if dx >= 0 else 180
    else:
        lies_at = 90 if dy > 0 else 270
    return (lies_at - CANONICAL_SPAN_AXIS) % 360


def summed_rotate(rotate, axis):
    """A placement's own `rotate` turned further by the axis its slot's pair
    runs on - the ONE spelling of that sum, so the entry `render._slot_dict`
    publishes and the turn `render.solve_seat` draws at cannot come apart.

    `axis` None means the slot spans nothing and the placement's own answer
    stands, `None` included: "drawn upright" and "not a question this slot
    answers" have to stay tellable apart. A whole number comes back as an
    `int`, because the sum is written straight into an SVG `rotate()` and
    `rotate(90.0 ...)` is a different string from the one every unspanned
    placement emits.
    """
    if axis is None:
        return rotate
    turn = (float(rotate or 0) + float(axis)) % 360
    return int(turn) if turn == int(turn) else turn


def presented_turn(contract, resolve, connectors):
    """THE TURN AN OCCUPANT TAKES ON THIS HOST beyond the host placement's own
    `rotate`, or None when there is none (#548).

    A seated part turns with what it seats in (solve_seat, D3). A host that
    presents its OWN interface seats at its own turn, plus the axis a
    spanning pair runs on (spanning_axis). A host that FORWARDS a composed
    part's aperture (forwarded_part) seats the occupant in THAT part, so the
    part's own `rotate` is part of the turn as well: generic/sfp-lc-simplex@2
    composes its bore at 180 (tongue up), and a plug seated through the optic
    took the optic's turn alone - 180 out, its latch off the side opposite
    the keyway, where a plug in a composed bore seated directly faces it. The
    same was true of an optic `mate-to` a card whose cage is a part at 90: it
    was drawn crosswise over its cage.

    None, not 0, for an unturned forward, for the reason summed_rotate keeps
    None: a published entry's `rotate` and a drawn `rotate()` do not change
    for the port wrappers, which all compose their aperture upright.
    """
    part = forwarded_part(contract, resolve)
    if part is None:
        return spanning_axis(contract, resolve, connectors)
    core = resolve(part["ref"]) if part.get("ref") else None
    turn = summed_rotate(part.get("rotate"), spanning_axis(core, resolve, connectors)
                         if core else None)
    return turn if float(turn or 0) % 360 else None


def allowed_turns(contract, resolve, connectors):
    """THE TURNS AN OCCUPANT MAY BE SEATED AT ON THIS HOST, relative to the
    seat, in the order the registry lists them (#829). [0] for a host whose
    interface names none, and for a contract that presents nothing.

    TWO LISTS, INTERSECTED. The interface's `turns` in spec/schemas/
    connectors.yaml says what the connector allows - a ring lug turns freely
    about its stud, so `terminal-stud` allows the four right angles, and a
    two-hole lug across a pair of studs only 0 and 180. The presented point's
    own `turns` narrows it for one part: a barrier block's terminal screw is
    the same `terminal-stud` and allows 0 alone, because the barriers fix the
    pole. The point is the one `presented_interface` seats on - this
    contract's own presented point, or the presented point of the core a
    wrapper forwards (`forwarded_part`) - so a wrapper adds no list of its own.

    THE TURN IS ADDED AFTER THE SEAT'S OWN: `render.solve_seat` draws the
    occupant at `summed_rotate(summed_rotate(host rotate, axis), turn)`, so 0
    is always the seat's own direction, and the turn a configuration states
    keeps its meaning whichever way the host is placed.
    """
    interface, _at, _lift = presented_interface(contract or {}, resolve)
    if not interface:
        return [0]
    reg = (connectors or {}).get(interface) or {}
    offered = [int(t) for t in (reg.get("turns") or [0])]
    part = forwarded_part(contract, resolve)
    point = presented_point(resolve(part["ref"]) or {}) if part is not None \
        else presented_point(contract)
    narrowed = (point or {}).get("turns")
    if narrowed is None:
        return offered
    keep = {int(t) for t in narrowed}
    return [t for t in offered if t in keep]


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
    the chassis's (L118) - so the drawing's `data-power`, `configs[].power` and
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


# --- rack PDUs: the capability class and the wiring (#934) -------------------
#
# docs/pdu-model-design.md sections 2.2 and 5. A PDU states two facts in
# `attrs.management` - how far down its metering goes and whether an outlet can
# be switched - and the class is DERIVED from them, never stated, so no manifest
# can name a class its two facts contradict. Every combination has a name; the
# names are ours and say what is metered, so they part from vendor names where
# a vendor name is loose (the G4 "metered input" EVMI2130X meters each branch
# too, and is `metered-branch`).
METERING_SCOPES = ("none", "input", "branch", "outlet")
PDU_CLASSES = {
    ("none", False): "basic",
    ("none", True): "switched",
    ("input", False): "metered-input",
    ("input", True): "switched-metered-input",
    ("branch", False): "metered-branch",
    ("branch", True): "switched-metered-branch",
    ("outlet", False): "metered-outlet",
    ("outlet", True): "managed",
}


def pdu_class(device):
    """The derived capability class of a rack PDU, or None.

    None unless `attrs.management` states BOTH `metering-scope` (one of
    METERING_SCOPES) and `outlet-switching` (a boolean); lint L166 holds a
    device to stating the two together, so a half-stated pair publishes
    nothing rather than a guess. configs.json and devices.json publish it as
    `pdu-class`, and the DCIM export writes it in the device type comments.
    """
    mgmt = ((device or {}).get("attrs") or {}).get("management") or {}
    scope, switching = mgmt.get("metering-scope"), mgmt.get("outlet-switching")
    if not isinstance(switching, bool):
        return None
    return PDU_CLASSES.get((scope, switching))


# The conductors a protecting placement's `lines` may name (section 5.3): one
# to three of the three lines and the neutral. `[L1, L2]` is line to line,
# `[L1, N]` line to neutral.
LINES = ("L1", "L2", "L3", "N")
# THE LEG A LINE-TO-NEUTRAL OUTLET IS ON, as NetBox and Nautobot spell
# PowerOutletFeedLegChoices: L1 is A, L2 B, L3 C (section 5.2).
FEED_LEGS = {"L1": "A", "L2": "B", "L3": "C"}


def device_placements(device):
    """{placement id: placement} over every view of a device, the first
    statement of an id winning. `fed-by`, `through` and `lines` cross a face,
    so they resolve over the whole device, not over the view they stand in."""
    out = {}
    for view in ((device or {}).get("views") or {}).values():
        for p in view_parts(view or {})["placements"]:
            out.setdefault(p.get("id"), p)
    return out


def outlet_lines(placement, placed):
    """The `lines` an outlet is wired across, or None where nothing states them.

    The outlet's own `lines` first, for an outlet with no breaker; else the
    `lines` of the placement its `through` names - a fixed breaker, which
    states them once for every outlet it protects, so an outlet reaches its
    lines through its breaker instead of restating them (section 5.3). A
    `through` naming a bay reaches no lines: a bay carries none."""
    own = (placement or {}).get("lines")
    if own:
        return list(own)
    via = (placement or {}).get("through")
    if via is not None and (placed.get(via) or {}).get("lines"):
        return list(placed[via]["lines"])
    return None


def feed_leg(device, lines):
    """The DCIM `feed_leg` of an outlet wired across `lines`, or None.

    WRITTEN EXACTLY WHEN THE INPUT IS THREE-PHASE WYE AND THE OUTLET IS WIRED
    LINE TO NEUTRAL (docs/pdu-model-design.md section 5.2), and it is that
    line. A line-to-line outlet sits on two legs and has no honest single
    answer; a single-phase PDU is on whatever leg its plug is on, which is a
    fact of the installation and not of the device type."""
    power = ((device or {}).get("attrs") or {}).get("power") or {}
    if power.get("input-phase") != "three" or power.get("input-wiring") != "wye":
        return None
    if not lines or len(lines) != 2 or "N" not in lines:
        return None
    line = next(x for x in lines if x != "N")
    return FEED_LEGS.get(line)


def input_rating(device):
    """The input rating as one sentence, or None where the device states no
    structured input key: what the export writes on the input power port's
    `description` and in the comments, since neither DCIM has an input rating
    on a device type (docs/pdu-model-design.md sections 4.3 and 8).

    Built from the structured keys only - `input-voltage-v`, `input-phase`,
    `input-wiring`, `input-current-a`, `plug-rating-a` - so it says nothing the
    numbers do not: '208 V three-phase wye, 24 A input (30 A plug)'."""
    power = ((device or {}).get("attrs") or {}).get("power") or {}
    head = []
    if power.get("input-voltage-v") is not None:
        head.append(f"{power['input-voltage-v']:g} V")
    if power.get("input-phase") in ("single", "three"):
        head.append(f"{power['input-phase']}-phase")
    if power.get("input-wiring") in ("wye", "delta"):
        head.append(power["input-wiring"])
    parts = [" ".join(head)] if head else []
    amps = power.get("input-current-a")
    plug = power.get("plug-rating-a")
    if amps is not None:
        tail = f"{amps:g} A input"
        if plug is not None and plug != amps:
            tail += f" ({plug:g} A plug)"
        parts.append(tail)
    elif plug is not None:
        parts.append(f"{plug:g} A plug")
    return ", ".join(parts) or None

# --- occupants keyed inside a seated module (#484, R2) -----------------------
#
# A configuration's `occupants:` may key a cage on a card seated in a bay by the
# card's MODULE-LESS path - `front-6/xg0` - the convention its nested `bays:`
# keys already use - and, since B3, a slot at any depth, part ids after the
# bays (`bay-1/lc01/1`). The build finds those keys from the instance it is
# drawing (slot_key_prefix, occupants_under); lint finds the instance from
# the key (nested_key_host). Both read a bay's occupant with seated_ref and name a
# seated occupant with occupant_local_id, so the two directions cannot come to
# disagree about which module a key reaches or which occupant a chained key
# names.

def slot_key_prefix(path):
    """The key prefix a configuration uses for what is on the instance drawn
    at `path`: the path with every `module` step dropped (B3, P1) -
    `bay-1/module/lc01` -> `bay-1/lc01`, `front-6/module` -> `front-6`, a
    device placement's `port-3` -> `port-3` - or None when there is no path.
    A slot at any depth is keyed this way: part ids from the device's
    placement or bay down to the slot, a seated bay's `module` left out."""
    if not path:
        return None
    return "/".join(s for s in path.split("/") if s != "module")


def seated_ref(cfg_bays, bay_path, bay):
    """What a configuration seats in the bay at module-less `bay_path`: its own
    `bays:` entry, else the bay's `default`; empty means empty."""
    return (cfg_bays or {}).get(bay_path, (bay or {}).get("default"))


def slot_default(part, contract):
    """The ref a slot ships holding, or None - the shipped default (B3,
    docs/pluggables-caps-design.md, "The shipped default").

    `part` is the `parts:` entry (or device placement) that places the slot and
    `contract` the placed component's. The entry's own `default:` wins - a
    composer overriding the placed component's TOP-LEVEL default, `""` for
    none - and otherwise the component's top-level `default:` stands. That is
    the whole of what a composer can say (P5): the defaults declared INSIDE the
    placed component, on its own `parts:`, are that component's, and only a
    configuration's `occupants:` reaches past them."""
    if "default" in (part or {}):
        return part["default"] or None
    return (contract or {}).get("default") or None


def drawn_refs(contract):
    """Every ref a contract draws without a configuration asking: each part's
    `ref`, each part's `default:`, its own top-level `default:` (which its
    composer draws unless it overrides it), and each of its `faces:`.
    Over-inclusive for a dependency walk on purpose - a default is drawn like
    a composed part.

    A FACE IS DRAWN TOO, and the three walks that read this list - the device
    lock's `composed` bucket, the build's up-to-date check and lint's
    `--device` filter - all missed it while it was left out. A cassette's
    `faces.rear` is drawn as the back of the seated module and a riser's
    `faces.plan` (or legacy `plan:`) lands in the device's top view, so a
    rear redrawn under a device went unseen: the FS FHD rears' MPO openings
    moved from 13.1 x 7.0 to 12.9 x 8.0 and fs/fhd-1ufce's lock reported
    nothing (roc-ops/Portrayal#405 is that silent redraw). Read through
    `face_ref`, so both spellings of `plan` count and a new direction in
    `faces.DIRECTIONS` is followed without a change here."""
    out = []
    for part in (contract or {}).get("parts") or []:
        for r in (part.get("ref"), part.get("default")):
            if r:
                out.append(str(r).split(":")[0])
    if (contract or {}).get("default"):
        out.append(str(contract["default"]).split(":")[0])
    for direction in DIRECTIONS:
        ref = face_ref(contract or {}, direction)
        if ref:
            out.append(str(ref).split(":")[0])
    return out


def occupant_spec(key, spec, label=None):
    """An `occupants:` value as a dict with a `ref`, or ValueError naming the key.
    An empty string empties the slot (B3, P4): None, and nothing is seated.

    `label` replaces `occupants/<key>` in that message, for a value that is not
    a configuration's key at all - a slot's shipped `default:`, which no
    `occupants:` entry named."""
    if spec == "":
        return None
    spec = {"ref": spec} if isinstance(spec, str) else spec
    if not isinstance(spec, dict) or not spec.get("ref"):
        raise ValueError(f"{label or f'occupants/{key}'}: names no component - "
                         "give a ref, or {ref: ..., attrs: ...}")
    return spec


def occupant_local_id(host_id, spec):
    """The id an occupant seated on `host_id` is drawn under: its own `id:`,
    else `<host>-occupant` - what a chained key names."""
    return spec.get("id") or f"{host_id}-occupant"


def back_parts(contract, resolve):
    """{part id: parts entry} of the drawing of `contract`'s BACK - the
    component its `faces.rear` names - or {} when it has none.

    A SLOT ON A MODULE'S BACK IS KEYED LIKE ONE ON ITS FRONT (B3, Task 7i).
    The build draws a seated module's back as a projection of the module
    (render.py `rear:`), so the back's parts are published under the module's
    own path - `bay-1/module/mtp1`, a cassette's MTP bulkhead - and a slot on
    one is keyed by the same module-less path, `bay-1/mtp1`. One namespace
    for the two faces, which is the one the drawing already publishes. A key
    is looked up on the front first, so a back part sharing a front part's id
    could not be addressed; no module does that, and
    spec/tests/test_rear_slots.py holds every module in the library to it."""
    ref = (((contract or {}).get("faces") or {}).get("rear") or {}).get("ref")
    back = resolve(ref) if ref else None
    return {q["id"]: q for q in (back or {}).get("parts") or [] if q.get("id")}


def back_hosts(prefix, occupants, back):
    """The host ids under `prefix` that are on a module's BACK: the ids of
    `back` (back_parts) and, to a fixed point, the produced id of every
    occupant keyed on one of them - `mtp1-occupant`, a plug seated in the
    bulkhead `mtp1`, which a boot can be keyed on in turn. The build splits a
    module's keys between its two drawings by this set, so the front and the
    back cannot both claim a key or both let one fall."""
    on = set(back)
    under = occupants_under(prefix, occupants) if prefix is not None else {}
    grew = True
    while grew:
        grew = False
        for host, (_key, spec) in under.items():
            if host in on and spec is not None:
                oid = occupant_local_id(host, spec)
                if oid not in on:
                    on.add(oid)
                    grew = True
    return on


def key_on_back(key, device, cfg, resolve):
    """Whether a module-less `occupants:` key names a slot on the BACK of the
    module seated in its head bay - `bay-1/mtp1`, or anything keyed under an
    occupant seated there (back_hosts). The front drawing hands such a key to
    the rear one, and render_view asks this to know it was handed on rather
    than dropped. A front part or nested bay of the same id wins, as it does
    in nested_key_host."""
    segs = key.split("/")
    if len(segs) < 2:
        return False
    bays = {b["id"]: b for _face, (_n, v) in resolve_views(device, cfg).items()
            for b in view_parts(v)["bays"]}
    if segs[0] not in bays:
        return False
    ref = seated_ref((cfg or {}).get("bays"), segs[0], bays[segs[0]])
    module = resolve(ref) if ref else None
    back = back_parts(module, resolve)
    front = {q.get("id") for q in (module or {}).get("parts") or []}
    if not back or segs[1] in front or segs[1] in ((module or {}).get("bays") or {}):
        return False
    return segs[1] in back_hosts(segs[0], (cfg or {}).get("occupants"), back)


def occupants_under(prefix, occupants):
    """{local host id: (key, spec)} for the `occupants:` keys that name a host
    directly on the instance whose key prefix is `prefix` - `front-6/xg0` under
    `front-6`, but not `front-6/slot-1/xg0`, which belongs to the module in
    that nested bay, nor `bay-1/lc01/1`, which belongs to the adapter `lc01`.
    A key that empties its slot (P4) comes back with spec None."""
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
    """Walk a module-less `occupants:` key down to its host: (host_ref,
    module_ref, module_path). `resolve(ref)` returns a contract or None.
    Raises ValueError saying what the key failed to reach.

    The key's head is a bay in a view this configuration draws, or a device
    placement in one (an adapter placed directly, `port-1510/1`). After a
    head bay, each segment is a nested bay of the module reached so far, and
    once a segment is not, every segment is a PART id of the contract reached
    so far (B3, deep addressing): `bay-1/lc01/1` is the part `1` of the part
    `lc01` of whatever `bay-1` seats. `module_ref` and `module_path` are the
    contract and the drawing path of the innermost instance holding the slot -
    `bay-1/module/lc01` - which is where the build draws the occupant.

    A chained key (`front-6/xg0-occupant`) names the occupant seated on
    another key of the same instance, and resolves to that occupant's ref -
    however many hops long, via `chained_occupant_ref`. ANY SEGMENT may be a
    chained occupant, not only the last: the head (`port-1510-occupant/a`, a
    composed part of a plug seated on a device placement) is resolved against
    this configuration's device-level occupants, and a segment mid-walk
    (`bay-1/lc01-occupant/a`, the same plug seated on an adapter in a
    cassette) against the keys of the instance reached so far. Resolving only
    the head made this function refuse keys the build seats."""
    segs = key.split("/")
    host_id = segs[-1]
    views = resolve_views(device, cfg)
    bays = {b["id"]: b for _face, (_n, v) in views.items()
            for b in view_parts(v)["bays"]}
    # A placement seated by mate-to has no `at`, so it is not a placement this
    # map can offer: an occupant is named by the CHAINED key that produced it
    # (P3), which is what the `else` branch below and the mid-walk branch in
    # the loop resolve. Only a placement with its own `at` belongs here.
    placements = {q.get("id"): q for _face, (_n, v) in views.items()
                  for q in view_parts(v)["placements"] if q.get("at") and q.get("ref")}
    cfg_bays = (cfg or {}).get("bays") or {}
    if segs[0] in bays:
        where, path = segs[0], f"{segs[0]}/module"
        ref, in_bays = seated_ref(cfg_bays, where, bays[segs[0]]), True
    elif segs[0] in placements:
        where, path = segs[0], segs[0]
        ref, in_bays = placements[segs[0]]["ref"], False
    else:
        # A SEATED OCCUPANT CAN BE THE HEAD TOO: `port-1510-occupant/a` is half
        # `a` of the duplex plug seated at `port-1510`. The head is resolved by
        # the SAME chained walk a bare chained key takes (chained_occupant_ref
        # over this configuration's device-level occupants), and `path` is the
        # occupant's own drawing path, which is its placement id - instance_group
        # falls back to `inst_id` when no path is passed, so the build names the
        # instance exactly this. Reached only when the head is neither a bay nor
        # a placement, so nothing that resolved before resolves differently.
        try:
            ref = chained_occupant_ref(
                segs[0],
                {k: (v if isinstance(v, dict) else {"ref": v})
                 for k, v in ((cfg or {}).get("occupants") or {}).items()
                 if "/" not in k and v != ""},
                lambda h: placements[h]["ref"] if h in placements else None)
        except (KeyError, ValueError):
            raise ValueError(f"occupants/{key}: {segs[0]!r} is no bay in any view "
                             "this configuration draws, no placement either, and "
                             "no occupant of this configuration seats it")
        where, path, in_bays = segs[0], segs[0], False
    for seg in segs[1:-1]:
        c = resolve(ref) if ref else None
        nb = ((c or {}).get("bays") or {}).get(seg) if in_bays else None
        if isinstance(nb, dict):
            where, path = f"{where}/{seg}", f"{path}/{seg}/module"
            ref = seated_ref(cfg_bays, where, nb)
            continue
        q = next((q for q in (c or {}).get("parts") or [] if q.get("id") == seg), None)
        if q is None or not q.get("ref"):
            # A SEATED OCCUPANT MID-WALK, the same thing the head branch above
            # and the terminal block below already resolve, and the reason this
            # is here rather than only in those two: `bay-1/lc01-occupant/a` is
            # half `a` of a duplex plug seated on the adapter `lc01` in the
            # cassette in `bay-1`, and the build seats it - the plug's instance
            # is drawn at `bay-1/module/lc01-occupant` and carries the keys
            # whose prefix is its own. Resolving a chained occupant only at
            # segs[0] made this function refuse a key the build accepted, so
            # lint failed a seat that rendered.
            #
            # SCOPE IS THIS INSTANCE'S OWN KEYS, `occupants_under` the path
            # reached so far - the same scope the terminal block uses - and the
            # chain grounds on a part of the contract reached so far.
            here = {p.get("id"): p for p in (c or {}).get("parts") or []}
            mine = {h: s for h, (_k, s) in
                    occupants_under(slot_key_prefix(path),
                                    (cfg or {}).get("occupants")).items()
                    if s is not None}
            try:
                ref = chained_occupant_ref(
                    seg, mine,
                    lambda h: here[h]["ref"] if h in here else None)
            except (KeyError, ValueError):
                raise ValueError(f"occupants/{key}: names no cage - {where!r} "
                                 f"holds {ref or 'nothing'}, which has no bay "
                                 f"or part {seg!r}, and no occupant seated "
                                 "there produces it")
            where, path, in_bays = f"{where}/{seg}", f"{path}/{seg}", False
            continue
        where, path, ref, in_bays = f"{where}/{seg}", f"{path}/{seg}", q["ref"], False
    if not ref:
        raise ValueError(f"occupants/{key}: names no cage - bay {where!r} is "
                         "empty in this configuration")
    module = resolve(ref)
    if module is None:
        raise ValueError(f"occupants/{key}: {where!r} holds {ref}, which "
                         "does not resolve")
    parts = {q.get("id"): q for q in module.get("parts") or []}
    if host_id in parts:
        if slot_in_slot_at(path, module, host_id, resolve):
            raise slot_in_slot_error(key, where, host_id)
        return parts[host_id]["ref"], ref, path
    # A SLOT ON THE MODULE'S BACK (back_parts), or an occupant chained on
    # one: only a module seated straight into a device bay has a back the
    # build draws, and only where that bay says where its back is seen
    # (`rear:`) - otherwise the key would seat nowhere, silently. A back part
    # is held by the back's own component, drawn at the module's path.
    back = back_parts(module, resolve) if len(segs) == 2 and in_bays else {}
    mine = {h: s for h, (_k, s) in
            occupants_under(slot_key_prefix(path), (cfg or {}).get("occupants")).items()
            if s is not None}
    if host_id in back_hosts(slot_key_prefix(path), (cfg or {}).get("occupants"), back):
        drawn = {vname for _face, (vname, _v) in views.items()}
        if (bays[segs[0]].get("rear") or {}).get("view") not in drawn:
            raise ValueError(f"occupants/{key}: {host_id!r} is on the back of "
                             f"{ref}, and bay {segs[0]!r} shows no back in any "
                             "view this configuration draws (no `rear:`)")
        if host_id in back:
            return back[host_id]["ref"], module["faces"]["rear"]["ref"], path
    try:
        host_ref = chained_occupant_ref(
            host_id, mine, lambda h: (parts[h]["ref"] if h in parts
                                      else back[h]["ref"] if h in back else None))
    except (KeyError, ValueError):
        raise ValueError(f"occupants/{key}: names no cage on {ref} at "
                         f"{where!r} - no part {host_id!r}, and no occupant "
                         "seated there produces it")
    return host_ref, ref, path


# A POSITION'S MOVES (docs/switch-positions-design.md section 4). render.py
# applies them and lint L148/L149 checks them, so the table is read in one place;
# kit/fields.js parseMoves spells the same pattern.
MOVE_ENTRY = re.compile(r"^\s*([^:,\s]+)\s*:\s*(-?[0-9.]+)\s+(-?[0-9.]+)(?:\s+(-?[0-9.]+))?\s*$")


def parse_moves(spec):
    """`data-move="on: 0 -3.2, off: 0 0"` -> {"on": (0.0, -3.2, 0.0), ...}.

    Each entry is an option, then a translation in millimetres in the skin's
    own frame, then optionally a turn in degrees about the node's own centre.
    A malformed entry raises: a table nobody can read moves nothing silently,
    which is the failure this rule exists to make loud."""
    out = {}
    for part in (spec or "").split(","):
        if not part.strip():
            continue
        m = MOVE_ENTRY.match(part)
        if not m:
            raise ValueError(f"data-move entry {part.strip()!r} is not 'option: dx dy [deg]'")
        opt, dx, dy, deg = m.groups()
        try:
            out[opt] = (float(dx), float(dy), float(deg or 0))
        except ValueError:      # '.' and '1.2.3' match the pattern and are not numbers
            raise ValueError(f"data-move entry {part.strip()!r} is not 'option: dx dy [deg]'") from None
    return out
