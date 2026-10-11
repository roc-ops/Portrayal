"""Adjustable positions: a part that slides (docs/adjustable-positions-design.md).

A device declares a sliding part once, in a top-level `adjustments:` map, and
every placement, bay or decor entry that slides with it says `moves-with: <id>`.
The value is a position in mm along one axis of the device, held as a field at
the path of one placement, the `carrier`.

ONE HOME FOR THE RULE. The build draws a configuration that sets a position
moved, lint asks whether a value is a position, and the lock records each
adjustment with its members. All three read this module, so they cannot give
three answers. kit/fields.js holds the same rule for a value a reader sets
after the build (`adjustmentAccepts`), and spec/tests/test_adjustments_js.py
holds the two to one list of cases.

THE FRAME is the one rack_solids.py uses: x from the left of the device as
seen from its front, y up from its bottom, z back from its front.
"""
import copy
import math
import re

# HOW EACH FACE SHOWS A MOVE ALONG EACH AXIS: the mm a node on that face moves
# for each mm of position. `dx` and `dy` are in the 2D frame of the face (x to
# the right, y down), and `dz` is the change in its depth behind that face.
# A plan (top and bottom alike) has the rear of the device at y = 0, and a
# side view has the front at the left on `right` and at the right on `left`.
# Written once here, so no reader holds a rule about which way a plan faces.
MOVES_BY = {
    "x": {"front": (1, 0, 0), "rear": (-1, 0, 0), "top": (1, 0, 0),
          "bottom": (-1, 0, 0), "left": (0, 0, 1), "right": (0, 0, -1)},
    "y": {"front": (0, -1, 0), "rear": (0, -1, 0), "left": (0, -1, 0),
          "right": (0, -1, 0), "top": (0, 0, -1), "bottom": (0, 0, 1)},
    "z": {"front": (0, 0, 1), "rear": (0, 0, -1), "top": (0, -1, 0),
          "bottom": (0, -1, 0), "right": (1, 0, 0), "left": (-1, 0, 0)},
}
# the extent of the device along each axis, as a key of `chassis`
EXTENT = {"x": "width", "y": "height", "z": "depth"}

# what a typed number may look like: digits and one point, as kit/fields.js
# reads it. No sign and no exponent, so the two halves refuse the same text.
_NUMBER = re.compile(r"^[ \t\n\r]*(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)[ \t\n\r]*$")
# a number all the same, written with a sign or an exponent: refused, and told so
_SIGNED = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")


def face_of(view_name, view):
    """The face a view draws: its own name, or the face a variant stands in for."""
    return (view or {}).get("face") or view_name


def moves_by(axis, face):
    """`(dx, dy, dz)` for one face, or None for a view that is not a face."""
    return MOVES_BY.get(axis, {}).get(face)


def round01(x):
    """A position to 0.1 mm, rounded half up. kit/fields.js rounds alike."""
    return math.floor(float(x) * 10 + 0.5) / 10


def spell(x):
    """THE ONE SPELLING OF A POSITION: rounded to 0.1 mm, in decimal, with no
    exponent, no sign and no trailing `.0`. So `120` and `271.2`, never `120.0`
    or `271.20`. One state is one string in a link and in a saved rack."""
    s = f"{round01(x):.1f}"
    return s[:-2] if s.endswith(".0") else s


def _stops_by_value(adj):
    return sorted((adj.get("stops") or {}).items(), key=lambda kv: (kv[1], kv[0]))


def accepts(adj, value, aid, on=None):
    """Is `value` a position of this adjustment? `(True, spelling)` with the
    one spelling to keep, or `(False, sentence)` saying what it takes.

    A stop name is input: it answers with the number behind it. With a
    `range` any number from min to max is a position, both ends included; with
    stops and no range only the stop values are.
    """
    who = f"{aid} on {on}" if on else str(aid)
    stops = adj.get("stops") or {}
    rng = adj.get("range")
    named = _stops_by_value(adj)
    # the four blanks kit/fields.js takes off, and no others: `strip()` alone
    # would take a unit separator the kit keeps, and keep a BOM the kit takes
    text = "" if value is None or isinstance(value, bool) else str(value).strip(" \t\n\r")
    n = None
    if text in stops:
        n = float(stops[text])
    elif _NUMBER.match(text):
        n = float(text)
    if rng:
        if n is None and _SIGNED.match(text):
            # `-20`, `+20`, `1e2`: a number, in a spelling a position never has
            return False, (f"{who} takes a number in mm written with digits and a point "
                           f"only. {text} is not.")
        if n is None:
            tail = f", or one of: {', '.join(k for k, _ in named)}" if named else ""
            return False, f"{who} takes a number in mm{tail}."
        r = round01(n)
        if r < round01(rng[0]) or r > round01(rng[1]):
            return False, (f"{who} takes {spell(rng[0])} to {spell(rng[1])} mm. "
                           f"{spell(n)} is outside it.")
        return True, spell(n)
    if n is not None and any(round01(v) == round01(n) for _, v in named):
        return True, spell(n)
    return False, (f"{who} takes one of: "
                   + ", ".join(f"{k} ({spell(v)})" for k, v in named) + ".")


def declared(device):
    """The `adjustments` map of a device, or {}."""
    adj = (device or {}).get("adjustments")
    return adj if isinstance(adj, dict) else {}


def positions(device, config):
    """Where each adjustment stands in one configuration: `{id: (mm, set)}`.

    `set` is true when the configuration states the position, as
    `component-attrs: {<carrier>: {<id>: <value>}}`. A value that is not a
    position fails the build with the sentence `accepts` gives.
    """
    out = {}
    overrides = (config or {}).get("component-attrs") or {}
    for aid, adj in declared(device).items():
        raw = (overrides.get(adj.get("carrier")) or {}).get(aid)
        if raw is None:
            out[aid] = (float(adj["default"]), False)
            continue
        ok, answer = accepts(adj, raw, aid, device.get("model"))
        if not ok:
            raise ValueError(answer)
        out[aid] = (float(answer), True)
    return out


def canonical_config(device, config):
    """`config` with each position it sets spelled the one way, so the drawing
    carries `data-<id>="271.2"` on the carrier whether the manifest said
    `271.2`, `271.20` or `rear`. The same object when it sets none."""
    pos = positions(device, config)
    if not any(was_set for _, was_set in pos.values()):
        return config
    overrides = {k: dict(v) for k, v in ((config or {}).get("component-attrs") or {}).items()}
    for aid, (value, was_set) in pos.items():
        if was_set:
            overrides[declared(device)[aid]["carrier"]][aid] = spell(value)
    return {**config, "component-attrs": overrides}


def _items(view):
    """Every entry of a view that can state `moves-with`: (kind, entry)."""
    view = view or {}
    comps = view.get("components") or {}
    for kind, seq in (("placements", comps.get("placements")),
                      ("bays", comps.get("bays")),
                      ("decor", (view.get("panel") or {}).get("decor"))):
        for item in seq or []:
            if isinstance(item, dict):
                yield kind, item


def members(device):
    """What states `moves-with`, by adjustment: `{id: ["<view>/<kind>/<id>"]}`,
    sorted. The key is spelled as devicelock spells a placed thing."""
    out = {}
    for vname, view in ((device or {}).get("views") or {}).items():
        for kind, item in _items(view):
            aid = item.get("moves-with")
            if aid is not None:
                out.setdefault(str(aid), []).append(f"{vname}/{kind}/{item.get('id')}")
    return {aid: sorted(keys) for aid, keys in out.items()}


def published(device, pos):
    """The map the drawing and configs.json carry: for each id its `axis`,
    `carrier`, `range`, `default`, `stops`, `label`, `datum`, and `at`, the
    position this build drew. A key the device does not state is left out."""
    out = {}
    for aid, adj in declared(device).items():
        row = {k: adj[k] for k in ("axis", "carrier", "range", "default", "stops",
                                   "label", "datum") if adj.get(k) is not None}
        row["at"] = float(spell(pos[aid][0]))
        out[aid] = row
    return out


def _shift(at, by, delta):
    return [round(at[0] + by[0] * delta, 4), round(at[1] + by[1] * delta, 4)] + list(at[2:])


def moved(device, deltas):
    """`device` with every member drawn `deltas[id]` mm along its axis.

    Each member's `at` is shifted by the delta times what its view shows of
    the axis, and a member bay's `plan` lands shifted on the view it names.
    Depth is not a coordinate of a manifest: the build changes it on the
    drawing (render.py). The same object when nothing moves, so a device at
    its default is built from the manifest as written.
    """
    deltas = {aid: d for aid, d in (deltas or {}).items() if d}
    if not deltas:
        return device
    adj = declared(device)
    out = copy.deepcopy(device)
    views = out.get("views") or {}
    for vname, view in views.items():
        face = face_of(vname, view)
        for kind, item in _items(view):
            aid = item.get("moves-with")
            if aid not in deltas or aid not in adj:
                continue
            by = moves_by(adj[aid]["axis"], face)
            if by and item.get("at"):
                item["at"] = _shift(item["at"], by, deltas[aid])
            plan = item.get("plan") if kind == "bays" else None
            if plan and plan.get("at") and plan.get("view") in views:
                pby = moves_by(adj[aid]["axis"], face_of(plan["view"], views[plan["view"]]))
                if pby:
                    plan["at"] = _shift(plan["at"], pby, deltas[aid])
    return out


# THE WORDS THAT NAME AN END OF A RANGE in the name of an attr, and the end
# each names. These four and no others: `lower`, `upper`, `from` and `to` are
# not read, and a name that uses them is read as the default.
_ENDS = {"min": "min", "minimum": "min", "max": "max", "maximum": "max"}


def restating_attrs(aid, flat_attrs):
    """The attrs that restate adjustment `aid`, by their names: `{key: what}`
    with `what` one of `default`, `min` and `max`.

    AN ATTR RESTATES AN ADJUSTMENT WHEN ITS NAME SAYS SO. The value of an
    adjustment is in mm, so the attr ends in `-mm`; before that it may say
    `-min` or `-max`; and what is left ends with the id of the adjustment, as
    whole words. So `rail-setback` is restated by `rail-setback-mm`, by
    `din-rail-setback-mm` and by `din-rail-setback-max-mm`, and by no key that
    does not end in the id. `min` or `max` among the words before the id names
    the same end (`max-rail-setback-mm`), and `minimum` and `maximum` are read
    as `min` and `max` in either place. A name that says both ends is not paired. No key of the adjustment names the attr, and no
    name of any maker is written here.
    """
    out = {}
    for key in flat_attrs or {}:
        key = str(key)
        if not key.endswith("-mm"):
            continue
        stem, ends = key[:-3], set()
        # every end the name says after the id, in whatever order: both are
        # collected, so `-max-min-mm` and `-min-max-mm` are judged alike
        while "-" in stem and stem.rsplit("-", 1)[1] in _ENDS:
            stem, word = stem.rsplit("-", 1)
            ends.add(_ENDS[word])
        if stem != aid and not stem.endswith("-" + aid):
            continue
        # `min` OR `max` MAY STAND BEFORE THE ID TOO: `max-rail-setback-mm` is
        # the top of the range as `rail-setback-max-mm` is, and never the
        # default. A name that says both ends, or one end twice over in two
        # places that disagree, says nothing a rule can hold, and is not paired.
        before = stem[:-len(aid)].strip("-").split("-") if stem != aid else []
        ends |= {_ENDS[w] for w in before if w in _ENDS}
        if len(ends) > 1:
            continue
        out[key] = ends.pop() if ends else "default"
    return out
