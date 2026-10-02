#!/usr/bin/env python3
"""Portrayal renderer v0: compile a device manifest + component skins into flat SVG.

One SVG per view. Deterministic output: no timestamps; tool version stamped in
<metadata> along with resolved component versions and the digest of the device's
published <device>.source.json.
"""
import argparse
import copy
import functools
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

# PARTS APPLIED OVER THE PANEL RATHER THAN PRINTED INTO IT. Their text is the
# part, not silkscreen, so `--without silkscreen` leaves them alone and L38 does
# not ask them to group text they were never meant to group.
APPLIED_CLASSES = {"sticker", "label", "marking"}

from portrayal import attrsections as attrs_mod
from portrayal.faces import face_ref, rear_place, rear_turn
from portrayal import libwalk
from portrayal.manifest import (presented_point, back_hosts, back_parts, key_on_back, slot_in_slot_at, slot_in_slot_error,
                                view_parts, targets, split_target, component_refs,
                      presented_interface, forwarded_part, seat_point, _turn,
                      load_yaml, resolve_views, slot_key_prefix,
                      seated_ref, occupants_under, occupant_local_id,
                      occupant_spec, nested_key_host, slot_default, drawn_refs,
                      spanned_slots, spanning_axis, summed_rotate, presented_turn,
                      alias_names, config_airflow,
                      config_power, device_options)
from portrayal import capability
from portrayal import bevel as _bevel
from portrayal import elements as elements_mod
from portrayal import facets as _facets
TOOL_VERSION = "0.1.0"
# profiles.yaml lives with the schemas, and every tool that needs it can find it
# from here rather than each growing a flag that is always given the same value.
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

STATE_CSS = """
    [data-path] { cursor: pointer; }
    .state-on    { --led-color: #22c55e; }
    .state-up    { --led-color: #22c55e; }
    /* link and up are the same fact on an Ethernet lamp; see docs/rj45-family-design.md */
    .state-link  { --led-color: #22c55e; }
    .state-activity { --led-color: #86efac; }
    .state-ok    { --led-color: #22c55e; }
    .state-fault { --led-color: #ef4444; }
    .state-fail  { --led-color: #ef4444; }
    .state-locate { --led-color: #3b82f6; }
    .state-absent { opacity: 0.35; }
    /* A state is a colour AND a behaviour. Solid and blinking of the same colour
       are different facts on real hardware: on the S9510-28DC a solid green PWR
       is "system power good" and a blinking green PWR is "power good but BMC
       power fail". A blinking state that renders solid is the same failure as a
       state class nothing paints - it looks modelled and is not.
       blink animates opacity rather than fill, because each skin carries its own
       unlit colour in the fill fallback and a keyframe cannot name it. alternate
       animates fill, because two colours is the whole point, and takes its first
       value from the element's own fill. */
    @keyframes portrayal-blink {
      0%, 49.9% { opacity: 1; }
      50%, 100% { opacity: 0; }
    }
    @keyframes portrayal-alternate {
      0%, 49.9% { fill: var(--led-color, #3a3f44); }
      50%, 100% { fill: var(--led-color-alt, #3a3f44); }
    }
    .portrayal-highlight { filter: drop-shadow(0 0 1.2px #f59e0b) drop-shadow(0 0 0.5px #f59e0b); }
    .portrayal-dim { opacity: 0.25; }
    [data-class='region'].portrayal-highlight { stroke: #f59e0b; stroke-width: 0.7; filter: none; }
    .state-fail[data-class='psu'], .state-fail[data-class='fan'] { filter: drop-shadow(0 0 1.4px #ef4444); }
"""


def data_for(value):
    """The `data-for` attribute for a `for:` value, or None.

    A bare target stays bare: it is a data-path in THIS drawing, and the ~250
    existing bindings say exactly that. A cross-view target comes out
    device-absolute, with a leading slash - `/rear/psu-0`.

    The slash is the point. Consumers split data-for on spaces and look each
    token up as a path in the drawing they are holding; `rear/psu-0` is a
    perfectly plausible-looking local path (a bay `rear` carrying a child
    `psu-0`) and could resolve to the wrong node without a word said. No
    data-path ever begins with a slash, so the qualified form cannot be mistaken
    for a local one: a consumer either understands the leading slash or fails to
    find the token, and neither of those is silent.
    """
    tg = targets(value)
    if not tg:
        return None
    return " ".join("/" + t if split_target(t)[0] else t for t in tg)



class Library:
    def __init__(self, roots):
        self.roots = [Path(r) for r in roots]
        self.cache = {}

    def resolve(self, ref):
        """ref = namespace/name@major -> (contract dict, skin dir Path)."""
        if ref in self.cache:
            return self.cache[ref]
        f = libwalk.contract_path(ref, self.roots)
        if f is None:
            raise FileNotFoundError(f"component ref not found in library path: {ref}")
        self.cache[ref] = (load_yaml(f), f.parent / "skins")
        return self.cache[ref]


def local(tag):
    return tag.split("}")[-1]


# 10 degrees +/-2 of taper a side and a 3.35 radius in four places, TE
# application specification 114-40010 Rev G Figure 3 - the mounting panel cutout
# every D-subminiature shell passes through, which is the same shape at every
# shell size. The radius is absolute in the specification rather than
# proportional; it is clamped only so a box too small to carry it still closes.
DSUB_TAPER = 0.17632698070846498          # tan(10 degrees)
DSUB_RADIUS = 3.35


def _dsub_path(x, y, w, h):
    """The D of D-subminiature: wide edge at top, both flanks raked in."""
    import math
    t = h * DSUB_TAPER
    # DERIVED, NOT GUESSED. A first draft clamped at 0.29 * h and the clamp bit
    # at exactly the standard size - 0.29 * 11.40 is 3.306, a hair under the
    # 3.35 the specification gives - so the shape came out subtly wrong for the
    # one box that matters most. The real limits are where the fillets meet:
    # 2.03r along a raked side of length h/cos(10), and 1.68r along the narrow
    # bottom edge. Inside those the specification's radius stands.
    r = min(DSUB_RADIUS, 0.49 * h, (w - 2 * t) / 1.7)
    pts = [(x, y), (x + w, y), (x + w - t, y + h), (x + t, y + h)]
    tang = []
    for i, p in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % 4]

        def unit(q):
            dx, dy = q[0] - p[0], q[1] - p[1]
            d = math.hypot(dx, dy) or 1.0
            return dx / d, dy / d
        ua, ub = unit(a), unit(b)
        half = math.acos(max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1]))) / 2
        d = r / math.tan(half)
        tang.append(((p[0] + ua[0] * d, p[1] + ua[1] * d),
                     (p[0] + ub[0] * d, p[1] + ub[1] * d)))
    seg = [f"M{tang[0][0][0]:.3f} {tang[0][0][1]:.3f}"]
    for i in range(4):
        to = tang[i][1]
        seg.append(f"A{r:.3f} {r:.3f} 0 0 1 {to[0]:.3f} {to[1]:.3f}")
        nxt = tang[(i + 1) % 4][0]
        seg.append(f"L{nxt[0]:.3f} {nxt[1]:.3f}")
    seg[-1] = "Z"
    return " ".join(seg)


def _octagon_path(x, y, w, h):
    """A rectangle with its four corners chamfered at 45 degrees.

    The chamfer is derived from the SHORT axis rather than passed in, so this
    helper's signature matches `_dsub_path` and `_slot_path` and one `shape:`
    value can mean the same thing in decor and in cutouts. 0.35 of the short
    axis is what a formed bezel's window reads as on the MaiaEdge PBC - a flat
    top, a chamfer, a short vertical end, a chamfer back - and it degrades
    sensibly: a square box becomes a regular-looking octagon, a long one keeps
    its chamfers proportional to its height instead of swallowing its length.
    """
    c = min(w, h) * 0.35
    # EVERY SEGMENT IS AN ABSOLUTE L, including the ones H and V would shorten.
    # Eight corners then read as eight coordinate pairs, which is what lets a
    # test - or anyone reading the SVG - check the shape without parsing SVG's
    # shorthand.
    pts = ((x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h - c),
           (x + w - c, y + h), (x + c, y + h), (x, y + h - c), (x, y + c))
    head = f"M{pts[0][0]:.3f} {pts[0][1]:.3f}"
    rest = " ".join(f"L{px:.3f} {py:.3f}" for px, py in pts[1:])
    return f"{head} {rest} Z"


def _slot_path(x, y, w, h):
    """A stadium: semicircular ends on the short axis."""
    if w >= h:
        r = h / 2
        return (f"M{x + r:.3f} {y:.3f} H{x + w - r:.3f} "
                f"A{r:.3f} {r:.3f} 0 0 1 {x + w - r:.3f} {y + h:.3f} "
                f"H{x + r:.3f} A{r:.3f} {r:.3f} 0 0 1 {x + r:.3f} {y:.3f} Z")
    r = w / 2
    return (f"M{x + w:.3f} {y + r:.3f} V{y + h - r:.3f} "
            f"A{r:.3f} {r:.3f} 0 0 1 {x:.3f} {y + h - r:.3f} "
            f"V{y + r:.3f} A{r:.3f} {r:.3f} 0 0 1 {x + w:.3f} {y + r:.3f} Z")


URL_REF = re.compile(r"url\(#([A-Za-z0-9_-]+)\)")


def state_names(states):
    return [st if isinstance(st, str) else st["name"] for st in states or []]


# How a lamp is lit, as opposed to what colour it is lit. `blinking` is one
# colour on and off; `alternating` flashes between two, which the S9510-28DC PSU
# does to mean "working condition not satisfied". Rate is deliberately NOT here
# yet - some hardware distinguishes a slow blink from a fast one, and the object
# form of `behavior` exists from day one so that adding `rate:` is one more
# property rather than the coercion `legend: true` needed a v2 to undo.
BEHAVIORS = {"solid", "blinking", "alternating"}
BLINK_KEYFRAMES = {"blinking": "portrayal-blink", "alternating": "portrayal-alternate"}


# A bay's size is {w,h} on a device and [w,h] in a component contract. One
# reader for both, because the difference is historical rather than meaningful.
def bay_size(bay):
    sz = bay.get("size")
    if isinstance(sz, dict):
        return sz["w"], sz["h"]
    return sz[0], sz[1]


# A carrier in a carrier is real (chassis -> MOD -> MPA). A carrier in ITSELF is
# a contract bug, and without a cap it is an unbounded recursion at build time.
MAX_BAY_DEPTH = 3


def state_style(st, vocabulary=()):
    """(color, alt, mode, lit, rate, phases) for one state, or None if it needs
    no CSS.

    A bare token needs none: it names a state with no declared presentation, and
    whatever the base stylesheet says about `state-<name>` still applies.

    `lit` is the tuple of segment names a SHAPE-CHANGING state turns on. A lamp
    state says what colour one element is; a seven-segment digit showing `4` is
    not a colour at all, it is four of seven bars. `vocabulary` is every segment
    the component draws, so the rule can turn the rest off explicitly rather than
    relying on whatever the previous state left behind.

    `rate` and `phases` are what a real lamp needed that three modes could not
    say. Dell documents its drive status lamp as seven conditions, of which
    `blinking amber` had to stand for two - 'blinks amber four times per second,
    drive failure' and 'blinks green, amber, and turns off, PREDICTED failure' -
    which is a fault and a warning rendering identically.
    """
    if not isinstance(st, dict):
        return None
    beh = st.get("behavior")
    obj = {} if isinstance(beh, str) else (beh or {})
    mode = beh if isinstance(beh, str) else obj.get("mode", "solid")
    alt = obj.get("color")
    rate = obj.get("rate")
    phases = tuple((p.get("color"), p.get("seconds"))
                   for p in obj.get("phases") or ()) or None
    color = st.get("color")
    # `is not None`, not truthiness: `lights: []` is a state that lights NOTHING -
    # a blank digit, an unlit decimal point - and is as real as any other.
    lit = st.get("lights")
    if lit is not None:
        return (color, alt, mode, (tuple(lit), tuple(sorted(vocabulary))),
                rate, phases)
    if not color and mode == "solid":
        return None
    return (color, alt, mode, None, rate, phases)


def seq_css_name(*parts):
    """The @keyframes name for one state's sequence.

    A sequence needs its own keyframes, so it needs its own NAME: the cycle is
    per state, and two states sharing a name animate each other. Built from the
    component and state so it is stable across builds rather than an ordinal
    that moves when a part is added.

    THIS LIVES HERE BECAUSE TWO GENERATORS FOR ONE OUTPUT DRIFT. render.py and
    components_index.py both emit state rules, and the last time the second one
    grew its own copy of that logic every component skin carried a Python tuple
    where a colour belonged. When the sequence name was passed in only one of
    them, the other emitted `@keyframes None` - twice, colliding - which is a
    stylesheet that parses and a lamp that does not animate.
    """
    return "portrayal-seq-" + re.sub(r"[^a-zA-Z0-9]+", "-",
                                     "-".join(str(p) for p in parts)).strip("-")


def sequence_keyframes(name, phases):
    """A named @keyframes walking one lamp through an ordered cycle.

    A phase with no colour is the lamp OFF, which is a phase like any other -
    'blinks green, amber, and turns off' is three of them and the third is the
    point. Durations may be absent, in which case the phases divide the cycle
    evenly: some vendors give the order without the timing, and dividing evenly
    records that rather than inventing seconds.

    Opacity carries the off phases and fill carries the colours, which is the
    same split the fixed blink and alternate keyframes already use.
    """
    total = sum(s for _, s in phases if s) or 0.0
    if not total:                       # no timings given: even division
        each = 100.0 / len(phases)
        bounds = [(i * each, (i + 1) * each) for i in range(len(phases))]
        total = float(len(phases))
    else:
        bounds, at = [], 0.0
        for _, s in phases:
            span = (s or 0) / total * 100.0
            bounds.append((at, at + span))
            at += span
    steps = []
    for (start, end), (color, _) in zip(bounds, phases):
        lit = "opacity: 1;" if color else "opacity: 0;"
        fill = f" fill: {color};" if color else ""
        steps.append(f"      {start:g}%, {max(start, end - 0.1):g}% "
                     f"{{ {lit}{fill} }}")
    return f"    @keyframes {name} {{\n" + "\n".join(steps) + "\n    }", total


def state_rule(sel_color, sel_anim, color, alt, mode, segments=None,
               rate=None, phases=None, seq_name=None):
    """The CSS for one state at one scope: what colour, how it is lit, and - for a
    segment display - which of its segments are on.

    THE OFF ONES ARE WRITTEN OUT TOO. A rule that only turns segments on leaves
    whatever the last state lit still lit, so `8` followed by `1` reads as `8`.
    Naming every segment in the component's vocabulary makes each state a
    complete statement of the face rather than a difference from an unknown one.
    """
    out = ""
    decls = [d for d in (f"--led-color: {color};" if color else "",
                         f"--led-color-alt: {alt};" if alt else "") if d]
    if decls:
        out += f"\n    {sel_color} {{ {' '.join(decls)} }}"
    if mode == "sequence" and phases:
        kf, total = sequence_keyframes(seq_name, phases)
        out += "\n" + kf
        out += (f"\n    {sel_anim} {{ animation: {seq_name} "
                f"{total:g}s steps(1, end) infinite; }}")
    elif mode in BLINK_KEYFRAMES:
        # a rate is a frequency, so the period is its reciprocal; no rate keeps
        # the one second every state written before `rate` existed meant
        period = 1.0 / rate if rate else 1.0
        out += (f"\n    {sel_anim} {{ animation: {BLINK_KEYFRAMES[mode]} "
                f"{period:g}s linear infinite; }}")
    if segments:
        lit, vocabulary = segments
        on = " ,".join(f"{sel_color} [data-seg='{s}']" for s in lit)
        off = " ,".join(f"{sel_color} [data-seg='{s}']"
                        for s in vocabulary if s not in lit)
        if on:
            out += f"\n    {on} {{ opacity: 1; }}"
        if off:
            out += f"\n    {off} {{ opacity: 0; }}"
    return out


def apply_states(g, states, palette):
    """Override a placed instance's state vocabulary with the device's own.

    A component declares what it IS - a 2mm round lamp - and can only guess what
    it MEANS. The meaning is per-device and per-function: the same common/led-dot
    is a speed lamp on one port and a link lamp on the next, and the speed lamp
    over a QSFP28 says Blue=100G/Green=40G while the one over a QSFP-DD says
    Cyan=400G/Blue=100G. Nothing about the lamp knows that; the device does.

    So the vocabulary is overridden on the whole instance: on the group element,
    and on every contracted element inside it that is a lamp - including lamps in
    composed parts, because a jack with integrated LEDs is one indicator to
    whoever declared it. Overriding only the outer <g> would be the bug this
    replaces: the tree reads the innermost data-states it can find, so the
    component's generic default would still be what reaches the chips.

    Colours are collected per instance id rather than per component ref: two
    placements of the SAME component now legitimately paint different colours for
    different names, which a `g[data-ref^=...]` rule cannot express.

    A mapping instead of a list addresses one lamp at a time, because one
    component can carry two lamps that do NOT share a vocabulary: the S9510-28DC
    management jack is one common/rj45-port whose left lamp is green for a 1G
    link and whose right lamp is amber for 10M/100M. One list over both would
    have to invent a vocabulary neither lamp has.
    """
    def lamp(node, sts):
        node.set("data-states", " ".join(state_names(sts)))
        if palette is None:
            return
        for st in sts or []:
            style = state_style(st)
            if style:
                name = st if isinstance(st, str) else st["name"]
                palette.setdefault((name, *style), []).append(
                    (node.get("id"), node is not g))

    if isinstance(states, dict):
        for el, sts in states.items():
            want = f"{g.get('id')}--{el}"
            for node in g.iter():
                if node.get("id") == want:
                    lamp(node, sts)
                    break
        return
    lamp(g, states)
    for node in g.iter():
        if node is not g and node.get("data-class") == "led":
            node.set("data-states", g.get("data-states"))


def rewrite_ids(el, prefix, contract, path_prefix, skip=None, in_port=False):
    """Prefix all ids (and url(#...) references to them); attach data-* to contracted elements."""
    elements = contract.get("elements", {}) or {}
    # A CONTRACT CAN NEST A PORT IN ITSELF, not just in a composed `parts:`
    # entry: an MPO/MTP flange adapter's own class is `port` and its keyed
    # `opening` is drawn as a second `class: port` element inside it, and a
    # bare plug's `body` does the same, for the same reason a composed cage
    # marks its std core - an audit walking `[data-class=port]` should not
    # count the opening or the body as a second connector. This wrapping `g`
    # (below, via the caller) is what carries `contract`'s own class, so an
    # inner element is nested under a port ancestor when THIS contract is
    # itself a port, or when the caller says an ancestor above it already is.
    self_in_port = in_port or contract.get("class") == "port"
    renamed = {}
    for node in el.iter():
        if node is skip:
            continue
        nid = node.get("id")
        if nid is None:
            continue
        renamed[nid] = f"{prefix}--{nid}"
        node.set("id", renamed[nid])
        if nid in elements:
            spec = elements[nid]
            node.set("data-path", f"{path_prefix}/{nid}")
            if spec.get("class"):
                node.set("data-class", spec["class"])
                if self_in_port and spec["class"] == "port":
                    node.set("data-inner", "1")
            if spec.get("states"):
                node.set("data-states", " ".join(state_names(spec["states"])))
            # A DISPLAY IS NOT A LAMP AND ITS VOCABULARY IS NOT COLOURS. `states`
            # answers "what colour can this be"; a four-character LED matrix
            # reading INIT, BOOT or PSEQ needs "what can this say", which is a
            # list of strings. It rides on its own attribute rather than
            # data-states so that nothing reading lamp vocabularies is handed
            # words it will try to paint - statesOfEl already drops a value that
            # is not a list of tokens, and quietly dropping the only thing a
            # display knows is the silence this exists to remove.
            if spec.get("characters"):
                node.set("data-characters", str(spec["characters"]))
            if spec.get("messages"):
                node.set("data-messages",
                         " ".join(str(m["text"]) for m in spec["messages"]))
            if spec.get("description"):
                node.set("data-description", spec["description"])
    for node in el.iter():
        for attr, val in list(node.attrib.items()):
            if "url(#" in val:
                node.set(attr, URL_REF.sub(
                    lambda m: f"url(#{renamed.get(m.group(1), m.group(1))})", val))


# A DERIVED OUTLINE IS ONE EXACT RULE, written twice - here for the build and in
# kit/fields.js `strokeShade` for a viewer that changes a colour afterwards - and
# spec/tests/test_stroke_derive.py holds the two to identical output. Each channel
# is multiplied by 61/100 and rounded half up, in integers so neither language's
# rounding of a binary fraction can differ: (c * 61 + 50) // 100. 0.61 is chosen
# so the generic latch's grey #6f6f6f lands exactly on the #444444 its outline
# was drawn with by hand. Accepted: `#rgb` and `#rrggbb`, either case, with
# surrounding space; anything else (a name, rgb(), a var()) has no shade and
# leaves the stroke as drawn. The answer is always lowercase `#rrggbb`.
STROKE_DERIVE_NUM, STROKE_DERIVE_DEN = 61, 100
_HEX_COLOUR = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def stroke_shade(colour):
    """The outline `data-stroke-derive` draws for a fill of `colour`, or None."""
    m = _HEX_COLOUR.fullmatch(str(colour or "").strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + "".join(
        f"{(int(h[i:i + 2], 16) * STROKE_DERIVE_NUM + STROKE_DERIVE_DEN // 2) // STROKE_DERIVE_DEN:02x}"
        for i in (0, 2, 4))


# WHAT `data-r-from` ACCEPTS AS A NUMBER: ASCII digits and a point, with ASCII
# blanks around them. kit/fields.js holds the same pattern character for
# character, and lint L122 asks it before its range check, so the three accept
# one set. It is spelled out rather than `\s` and `\d` because those differ
# between the two languages: Python's are Unicode (it read Arabic-Indic digits
# as a number and took the \x1c separator as blank), JS's `\d` is ASCII
# (spec/tests/test_r_from_binding.py holds all three to one answer).
R_FROM_NUMBER = re.compile(r"[ \t\n\r]*[0-9.]+[ \t\n\r]*")


def fill_from_attrs(root, attrs):
    """Fill skin nodes marked `data-from` or `data-fill-from` from this
    instance's merged attrs.

    A node carries the value it should show when nothing says otherwise, so the
    skin remains a valid standalone drawing; an attr replaces it. This is the
    same bargain `var(--led-color, #2c3a30)` makes for colour, moved to text.

    AND THEN MOVED BACK. `data-fill-from` names an attr that sets a node's
    `fill`, which is what a part whose SHELL COMES IN COLOURS needs and what a
    skin per colour does badly: the four RJ45 parts are one drawing whose shield
    is bright metal on the S9701-82DC (measured 183-185 against a cavity of 16)
    and black plastic on the S8901-54XC (39-46), and every other line of those
    files is identical. A skin apiece would be four near-copies per finish and a
    name to choose on each of 758 placements; an attr is one word on the ones
    that differ. `fields` is where a part advertises it, the same as for text.

    EMPTY LEAVES THE DEFAULT HERE, where for text it deletes. A label nobody
    filled in should not print, but a shape with no fill is not a quieter
    drawing - it is an invisible one, and no unspecified attr should be able to
    delete a housing.

    ABSENT LEAVES THE DEFAULT; EMPTY DELETES. An attr nobody mentioned must not
    blank a label - a part dropped into a bay with no attrs at all still has to
    draw - so only an explicit empty string removes anything. When it does, the
    node goes, and so does the nearest run of ancestors marked
    `data-hide-when-empty`: an SSD has no rotational speed AND no spindle glyph
    beside it, and deleting the text alone would leave the glyph pointing at
    nothing.
    """
    parents = {c: p for p in root.iter() for c in p}

    # A BLANK COLOUR IS AN EMPTY ONE. "  " is not in (None, ""), and stripping it
    # used to paint fill="" - an invisible node, the one outcome the rule above
    # exists to prevent. kit/fields.js trims before it asks, so the build does too.
    def colour(key):
        v = attrs.get(key)
        return "" if v is None else str(v).strip()
    # the fill each colour field is DRAWN with, read before anything is painted:
    # a derived outline with no value set follows the drawing's own default
    drawn = {}
    for node in root.iter():
        k = node.get("data-fill-from")
        if k is not None and k not in drawn and node.get("fill"):
            drawn[k] = node.get("fill")
    for node in list(root.iter()):
        # AN OUTLINE THAT FOLLOWS ITS FILL WITHOUT A FIELD OF ITS OWN. A latch
        # whose colour is a field needs an edge that goes with whatever colour
        # it is given - the generic transceivers' red latch wore the dark blue
        # outline of the fill it used to have (#482). `data-stroke-from` would
        # make that a second field for every wrapper to keep in step with the
        # first; `data-stroke-derive` names the colour field and draws the
        # outline as a fixed darker shade of it (`stroke_shade`). With the field
        # unset it is the shade of the drawn default, so the compiled default
        # and the hand-written literal cannot disagree.
        derive = node.get("data-stroke-derive")
        if derive is not None:
            src = colour(derive) or drawn.get(derive)
            shade = stroke_shade(src)
            if shade:
                node.set("stroke", shade)
        paint = node.get("data-fill-from")
        if paint is not None and colour(paint):
            node.set("fill", colour(paint))
        # AND THE OUTLINE WITH IT. A coloured part is not a fill on its own: every
        # red latch in this library is `fill="#c22f2f" stroke="#8c1f1f"`, and the
        # blue variant changed both. Converting those skins to an attr with only
        # `data-fill-from` would have left a blue handle wearing a dark red
        # outline - a drawing nobody would have written by hand, arrived at by a
        # mechanism that could only say half of what the art said (#177).
        line = node.get("data-stroke-from")
        if line is not None and colour(line):
            node.set("stroke", colour(line))
        key = node.get("data-from")
        if key is None:
            continue
        if key not in attrs:
            continue
        val = "" if attrs[key] is None else str(attrs[key]).strip()
        if val:
            node.text = val
            continue
        target = node
        while True:
            p = parents.get(target)
            if p is not None and p.get("data-hide-when-empty") is not None:
                target = p
                continue
            break
        p = parents.get(target)
        if p is not None:
            p.remove(target)

    # A FIELD MAY SET A SIZE. `data-r-from` names a numeric field whose value is a
    # DIAMETER; the circle takes half of it as its radius. Empty, absent or not a
    # number leaves the radius the skin was drawn with - the same rule colour
    # follows - so the skin stays a valid standalone drawing
    # (docs/pluggables-cables-design.md section 4).
    #
    # A NUMBER IS DIGITS AND A POINT, and kit/fields.js asks the same question the
    # same way: float() alone would take "1e1", "inf" and "1_0", which the kit
    # reads differently, and a stub sized in one view and not the other is the
    # drift one rule exists to prevent. The radius is written the way JS's
    # String() writes a number - shortest round trip, no trailing ".0" - so both
    # halves put the same text in `r` (spec/tests/test_r_from_binding.py).
    for node in root.iter():
        key = node.get("data-r-from")
        if key is None:
            continue
        v = attrs.get(key)
        if v is None or isinstance(v, bool) or not R_FROM_NUMBER.fullmatch(str(v)):
            continue
        try:
            d = float(str(v).strip())
        except ValueError:
            continue
        if math.isfinite(d) and d > 0:
            r = d / 2
            node.set("r", str(int(r)) if r.is_integer() else repr(r))


def _inset_feature(feat, back, group_lift=0.0):
    """A feature on an instance mounted `back` mm behind the panel face.

    A part's relief is written for the usual mounting - the flange bolts to the
    sheet metal and the body stands proud by its own depth. Mount the same part
    on a board set back from the face and every one of those numbers is measured
    from the wrong plane.

    `out` and `lift` are distances FROM THE FACE and simply move; `cyl`, `bar`
    and `uhandle` are LENGTHS whose base is `lift`, so what moves is where they
    start and what shortens is however much of them ends up behind the panel.
    A feature left wholly behind is dropped: it is inside the machine, and the
    drawing of a face does not show what is behind it.

    `group_lift` IS THE PART OF `back` THE INSTANCE GROUP ALREADY CARRIES, and
    keeping it separate is the whole reason this takes two numbers. relief.js
    reads `data-z-out` as an ABSOLUTE distance from the panel but SUMS
    `data-z-lift` up the ancestor chain, so a lift written onto the part's own
    group must be folded into that part's `out` values and must NOT be folded
    into their `lift` values. Doing both counts it twice, and it did: composing
    common/lc-duplex-adapter@3 onto smartoptics/dcp-f-a22's plate at `lift: 44`
    put 44 on the adapter's group AND rewrote each dust cap's own 3.175 lift to
    47.175, so relief.js summed 91.175 against an `out` of 50.35 and built the
    caps as boxes 40mm deep starting in front of where they end. They rendered as
    white spikes standing off the face.
    Only one caller has a group lift to pass - a component's `parts:`, which sets
    `data-z-lift` on the part group. A device placement's `lift:` sets no such
    attribute and is carried entirely by `back`, which is why it must not.
    """
    if not back and not group_lift:
        return feat
    f = dict(feat)
    # what a `lift`, and anything measured from one, has to move by
    lb = back + group_lift
    # A SUNK FACET IS BELOW THE PLATE ON PURPOSE (recessed facets, in
    # docs/superpowers/specs/2026-09-24-tilted-facets-design.md): it stands in
    # a pocket, so a negative `out` or `lift` is its geometry, not a feature
    # left behind the panel. Nothing here clamps or drops one.
    sunk = bool(f.get("facet")) and (f.get("lift") or 0) < 0
    top = None
    for k in ("cyl", "bar", "uhandle"):
        if f.get(k) is not None:
            top = (f.get("lift") or 0.0) + f[k]
    if f.get("out") is not None:
        f["out"] = round(f["out"] - back, 4)
        if f["out"] <= 0 and not sunk:
            return None
    if f.get("lift") is not None:
        f["lift"] = round(f["lift"] - lb if sunk else max(0.0, f["lift"] - lb), 4)
        if not f["lift"]:
            f.pop("lift")
    if top is not None:
        top -= lb
        if top <= 0:
            return None
        for k in ("cyl", "bar", "uhandle"):
            if f.get(k) is not None:
                f[k] = round(top - (f.get("lift") or 0.0), 4)
    return f


def _facet_wedge(feat, contract):
    """A `facet` feature's derived `out`/profile, off the facet node's own
    `elements[node].size`, computed BEFORE `_inset_feature` sees it
    (docs/superpowers/specs/2026-09-24-tilted-facets-design.md; the schema
    forbids a `facet` feature from also declaring them). A node missing
    from `elements` derives nothing.

    `lift` offsets the WHOLE wedge, root edge included, not just `out`:
    `derived_profile` starts every wedge at 0, so both its points are
    shifted here by the same `lift` `out` already carries.
    """
    if not feat.get("facet"):
        return feat
    el = (contract.get("elements") or {}).get(feat["node"]) or {}
    if not el.get("size"):
        return feat
    fw, fh = el["size"]
    lift = feat.get("lift") or 0
    key, prof = _facets.derived_profile(feat["facet"], fw, fh)
    if lift:
        prof = [[p, round(o + lift, 4)] for p, o in prof]
    return {**feat, key: prof,
            "out": round(lift + _facets.proud_extent(feat["facet"], fw, fh), 4)}


def _inset_facet_profile(raw_feat, pre_out, feat):
    """Shift a facet-DERIVED profile by whatever `_inset_feature` just moved
    `out` by.

    `_inset_feature` moves `out` and `lift`; it knows nothing about
    `profile`/`profile-y`, because a hand-written feature's profile is
    written against the part's own face and never needed to move with an
    inset before now. A facet's derived profile is exactly as "declared" as
    its derived `out` and has to move by the same amount `out` just did, or
    the wedge and the plate it sits on disagree about where the panel is.
    Hand-written profiles are untouched - only a feature THIS BUILD expanded
    from a `facet` is shifted here, guarded by `raw_feat.get("facet")`.
    Clamped at 0: an inset larger than the wedge's own proud extent must not
    read as a negative depth - EXCEPT on a sunk facet (`lift < 0`), whose
    heights are below the plate on purpose and pass through unclamped.
    """
    if not raw_feat.get("facet") or pre_out is None or feat is None or feat.get("out") is None:
        return feat
    shift = feat["out"] - pre_out
    if not shift:
        return feat
    pkey = "profile-y" if raw_feat["facet"]["facing"] in ("up", "down") else "profile"
    if feat.get(pkey):
        feat = dict(feat)
        floor = None if (raw_feat.get("lift") or 0) < 0 else 0.0
        feat[pkey] = [[x, round(o + shift, 4) if floor is None else max(floor, round(o + shift, 4))]
                      for x, o in feat[pkey]]
    return feat


def well_floor(placements, lib, wid):
    """How deep the floor of well `wid` is, for whatever says it is `in:` one.

    The aperture rule again: an unmounted, non-module part's `size.d` is the
    depth of the recess it draws as, and the floor of that recess is where a
    part on it sits. render_view emits it as a NEGATIVE data-z-lift - relief.js
    sums lifts up the ancestor chain, so a sunk group sinks everything in it -
    and pulls the part's own `out` figures, which are measured from the face,
    down by the same amount so they rise from the floor instead.

    Module-level so cage_entries reads the SAME floor the build sinks a cage
    by: a cage in a well publishes that sink in its `lift`, as the mate-to
    resolution carries it in `host-lift`.
    """
    q = next((z for z in placements if z.get("id") == wid), None)
    if not q:
        return 0.0
    try:
        c, _ = lib.resolve(q["ref"])
    except Exception:
        return 0.0
    c = c or {}
    # the aperture rule exactly as the emitter applies it: a module is
    # solid, a mounted part is solid UNLESS it declares `relief.cavity` -
    # the mid tray lifts out and is the recess its drives sit in
    if c.get("kind") == "module":
        return 0.0
    if c.get("behaviour") == "mounts" and not (c.get("relief") or {}).get("cavity"):
        return 0.0
    return float((c.get("size") or {}).get("d") or 0.0)


def seat_at(point, rotate, occ_size, occ_mate):
    """The `at` that lands an occupant's `occ_mate` on `point` when the
    occupant is drawn translate(at) rotate(deg w/2 h/2) - the inverse of
    seat_point for the occupant."""
    cx, cy = occ_size["w"] / 2, occ_size["h"] / 2
    dx, dy = _turn((occ_mate[0] - cx, occ_mate[1] - cy), rotate)
    return [round(point[0] - cx - dx, 4), round(point[1] - cy - dy, 4)]


def data_attrs(attrs):
    """An attrs bag as the SVG attributes the build writes for it:
    {data-<k>: str(v)}, in key order. The one spelling, used by
    instance_group for every placement and by group_side_attrs for a group."""
    return {f"data-{k}": str(v) for k, v in sorted((attrs or {}).items())}


def group_side_attrs(group_name, grp):
    """EVERYTHING DRAWING A PLACEMENT IN A GROUP WRITES ON IT FROM THE GROUP,
    as {data-attr: string}: the group's attrs, `data-group`,
    `data-group-role`, `data-description`.

    ONE FUNCTION DECIDES IT, AND BOTH SIDES READ IT. draw_placement writes
    exactly this map onto every grouped placement (a placement's own attrs and
    description still win), and cage_entries publishes it as a cage's
    `occupant-attrs` - because an occupant seated through `occupants:` takes
    its host's `group` and nothing else from it (see the expansion in
    render_view), this map IS what the host side contributes to a seated
    optic: a group's `media: qsfp-dd` over the optic contract's `media:
    fiber`, and so on. A new host-side write added here reaches the drawing
    and the published cage together; one added anywhere else is caught by
    test_cage_accepts, which diffs a built occupant against the same occupant
    built with no group and requires the difference to equal this map.
    """
    grp = grp or {}
    out = data_attrs(grp.get("attrs"))
    if group_name:
        out["data-group"] = group_name
    if grp.get("role"):
        out["data-group-role"] = grp["role"]
    if grp.get("description"):
        out["data-description"] = grp["description"]
    return out


def write_group_side(g, group_name, grp, own_attrs):
    """Write group_side_attrs onto a drawn member `g`, except where the member's
    OWN attrs already name the key - a placement's attrs win over its group's.

    THE ONE WRITER, for the three places a member is drawn: a device placement
    (draw_placement), a component part in a component group (instance_group's
    `parts:` loop, at any nesting depth), and an optic seated in a card's cage
    (_seat_nested_occupants). The map is group_side_attrs and nothing else, so
    a cage's published `occupant-attrs` and what the build writes cannot drift
    apart on a card any more than on a device."""
    own = data_attrs(own_attrs)
    for name, value in group_side_attrs(group_name, grp).items():
        if name not in own:
            g.set(name, value)


def group_merged_attrs(grp, own_attrs):
    """The attrs bag a grouped member is DRAWN with: its group's attrs under its
    own. instance_group reads this for text filled from attrs and for the
    contract-attr precedence; write_group_side is what the group writes."""
    return {**((grp or {}).get("attrs") or {}), **(own_attrs or {})} or None


def solve_seat(lib, who, occ_ref, host_name, host, occ_rotate=None, occ_in=None,
               floor_of=None):
    """WHERE ONE OCCUPANT SEATS ON ONE HOST: (at, rotate, lift), in the frame
    the host's `at` is written in, with every rule a seat is held to.

    THE ONE SEATING RULE, called by render_view's `mate-to` resolution for a
    device-level seat and by _seat_nested_occupants for a seat on a card, so
    the two cannot drift apart - the plan's "nothing about seating is solved
    twice". `host` is a placement-shaped dict: `ref`, `at`, `rotate`,
    `mirror`, `in`, `projection-of`, and `host-lift` - what the host itself
    already stands at (a seated host's own seat lift; a composed cage's own
    `lift`, which a sibling occupant does not inherit). `who` and
    `host_name` are only for the messages.

    The host's mate point - possibly FORWARDED from a composed aperture (see
    manifest.presented_interface) - is taken through the host's rotation
    (seat_point), and the occupant is solved to land its own `mate` there
    while drawn at that rotation plus, for a host whose slot SPANS a pair,
    the axis that pair runs on (manifest.spanning_axis; seat_at). `lift` is
    the host's presented lift plus its `host-lift`, less the floor of a well
    it stands `in:` (floor_of, device frame only)."""
    hc, _ = lib.resolve(host["ref"])
    oc, _ = lib.resolve(occ_ref)

    def _res(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None
    # The host's mate point may be FORWARDED from a composed aperture -
    # see manifest.presented_interface. The occupant's is its own: a
    # module is the thing that mates, not a wrapper around one.
    _, hm_at, hm_lift = presented_interface(hc, _res)
    om = (oc.get("connection-points") or {}).get("mate")
    if hm_at is None or om is None:
        raise ValueError(
            f"{who}: mate-to needs a 'mate' connection-point on both "
            f"{occ_ref} and {host['ref']} - the host may also present "
            "one through a composed aperture")
    # A SEATED PART TURNS WITH ITS HOST (docs/pluggables-slotting-
    # design.md, D3). 941 of the library's cages are drawn rotated -
    # 940 at 180, one at 90 - and this used to seat every one of them
    # as if upright: `host.at + host_mate - occupant_mate`, no rotate
    # carried, so the optic's mate point missed the cage's TURNED one
    # and the optic was drawn the wrong way up. At rotate 0 seat_point
    # and seat_at reduce exactly to the old formula, so no unrotated
    # seat moves.
    hrot = host.get("rotate")
    # AND A SPANNING HOST TURNS IT FURTHER (B3, "The duplex host"). A duplex
    # connector is one moulding with two ferrules on an axis; it cannot turn
    # itself, and the library's two duplex adapters do not agree about which
    # way round their pair runs. `manifest.spanning_axis` reads that off the
    # host's own bores, and the occupant is drawn at the SUM - the placement's
    # rotation and its pair's axis are rotations of the same plane.
    #
    # THE HOST'S OWN MATE POINT IS NOT TAKEN THROUGH IT. `seat_point` below
    # maps a point of the host's contract into the host's frame, which is the
    # host's own `rotate` and nothing else; the axis is a fact about the
    # OCCUPANT's drawing, not about where the host's slot is. The published
    # entry splits them the same way (`_slot_dict`: `mate` by the placement's
    # rotate, `rotate` by the sum), so the kit seats what the build draws.
    orot = summed_rotate(hrot, presented_turn(hc, _res, _connector_registry()))
    if host.get("mirror"):
        raise ValueError(
            f"{who}: its host {host_name!r} is mirrored, and a "
            "mirrored host cannot seat an occupant - handedness of a "
            "seated part is not a question the seating rule answers")
    if occ_rotate is not None and \
            float(occ_rotate) % 360 != float(orot or 0) % 360:
        raise ValueError(
            f"{who}: declares rotate {occ_rotate} but its host "
            f"{host_name!r} seats at {orot or 0} - a seated part turns "
            "with its host; drop the rotate")
    # A SEATED PART ALREADY SINKS WITH A SUNK HOST - through host-lift,
    # below - so its own `in:` would sink it a second time: -3.46 where
    # 3.27 is right (final review I2). A host is sunk when it stands
    # `in:` a well itself, or inherits a sink from its own host (a
    # negative host-lift: a seat lift is otherwise never negative).
    if occ_in and not host.get("projection-of") and (
            host.get("in") or float(host.get("host-lift") or 0.0) < 0):
        raise ValueError(
            f"{who}: stands in:{occ_in!r} but a seated part sinks "
            f"with its host {host_name!r}, which is already sunk in a "
            "well - drop the in:")
    at = seat_at(seat_point(host["at"], hc["size"], hrot, hm_at),
                 orot, oc["size"], om["at"])
    # A CHAINED SEAT INHERITS THE WHOLE STACK, not just the last link.
    # `presented_interface` answers one question - how far the HOST's
    # aperture stands off the HOST's own face - and returns 0.0 whenever
    # the host declares its own `interface` + `mate`, which every plug
    # does. So a boot on a plug on a 10 mm-proud bore took 0.0 and sat
    # 10 mm too deep. The host's own seat lift is the missing term, and
    # the caller computed it when it seated the host. Summed HERE, once,
    # at resolution time, because an occupant is a SIBLING of its host in
    # the compiled drawing and relief.js's ancestor sum has no path from
    # one to the other to walk.
    lift = float(hm_lift or 0.0) + float(host.get("host-lift") or 0.0)
    # AND A HOST SUNK IN A WELL TAKES ITS OCCUPANT DOWN WITH IT. A host
    # that stands `in:` a well is sunk by the well's floor in
    # draw_placement (`sink`): data-z-lift -floor on the host's group,
    # and every data-z-out in it pulled down by floor. The occupant is a
    # sibling, so that group lift never reaches it; the sink is carried
    # as a NEGATIVE term of the same lift, and a chained seat inherits it
    # once, through the host's own host-lift, rather than re-adding it
    # per link. A projection is not sunk, so neither is what seats on one.
    if host.get("in") and not host.get("projection-of"):
        lift -= floor_of(host["in"])
    return at, orot, lift


def refuse_bay_module_default(lib, ref, where):
    """A module seated in a BAY may not ship an occupant on its own slot.

    A default is the product's shipped state and seats wherever the part is
    placed or composed (B3, "The shipped default") - but the rule that makes
    that safe is that a configuration can always override it, and a bay
    module's OWN slot has no key today: `occupants:` keys a part id under a
    bay (`bay-1/lc01`), never the seated module itself, so `bay-1` names no
    slot and neither the build nor L12 can empty one. Seating it anyway would
    put an occupant in every drawing that nothing could take out, and
    dropping it silently is the fault this refusal exists to stop: the same
    contract would ship its cap as a composed part and lose it in a bay.

    So it is an ERROR that names the default, not a silent drop. Nothing in
    the library declares one; whoever needs it gives a bay module's slot a
    key first. The defaults declared INSIDE such a module - on its own
    `parts:` - are unaffected and seat as they do anywhere else.
    """
    try:
        shipped = (lib.resolve(ref)[0] or {}).get("default")
    except (FileNotFoundError, ValueError, KeyError):
        return                          # a bad ref is reported where it is drawn
    if shipped:
        raise ValueError(
            f"{where}: {ref} ships holding {shipped} on its own slot, and a "
            "module seated in a bay has no slot key a configuration could "
            "override (B3) - compose it as a part, or place it, to seat that "
            "default")


def filled_spanned_slots(contract, resolve, connectors, slot_key, occupants):
    """Which of `contract`'s spanned bores hold something once this
    configuration and the contracts' own defaults resolve (B3, "The duplex
    host") - the ids, in declaration order.

    `slot_key` is the key the SPANNING slot is addressed by (`bay-1/lc01`,
    `port-1510`), so a bore's own key is `<slot_key>/<id>`. A configuration
    that keys a bore answers for it outright, `""` included - that is P5, and
    an emptied bore is not filled. A bore no key names holds what it ships
    (`slot_default`), because a default is the product's state and seats in
    every configuration that does not override it.
    """
    parts = {q.get("id"): q for q in (contract.get("parts") or [])}
    out = []
    for bid in spanned_slots(contract, resolve, connectors):
        key = f"{slot_key}/{bid}" if slot_key else None
        if key is not None and key in (occupants or {}):
            try:
                if occupant_spec(key, occupants[key]) is not None:
                    out.append(bid)
            except ValueError:
                pass                    # a malformed value is reported when it seats
            continue
        q = parts.get(bid) or {}
        try:
            if slot_default(q, resolve(q.get("ref")) or {}):
                out.append(bid)
        except (FileNotFoundError, ValueError, KeyError):
            continue                    # a bad ref is draw_placement's to report
    return out


def refuse_spanned_overlap(slot_key, ref, contract, resolve, connectors, occupants):
    """A SPANNING SLOT AND ITS BORES ARE MUTUALLY EXCLUSIVE (B3, docs/
    pluggables-caps-design.md, "The duplex host"), and this is where the build
    says so - called wherever a fill lands on the spanning slot itself.

    One duplex connector occupies both LC bores of a duplex adapter. So when
    the adapter's own slot is filled its bores are not offered, and when either
    bore is filled the adapter's slot is not offered. Both filled is not a
    precedence question with a quiet answer - there is one piece of hardware
    and two claims on it - so it is an error naming the key to edit. Emptying
    the level you do not want (`""`) is how a configuration chooses: the
    Smartoptics adapter ships capped bores, so a duplex plug there needs both
    bores emptied first, and the FS adapter ships a duplex cap, so a simplex
    plug in one bore needs the adapter's own slot emptied first.
    """
    for bid in filled_spanned_slots(contract, resolve, connectors, slot_key,
                                    occupants):
        raise ValueError(
            f"occupants/{slot_key}: {ref} and its bore {bid} cannot both be "
            "filled - one duplex connector fills both bores. Empty the bores "
            f"({slot_key}/{bid}: \"\"), or empty this slot")


def _facet_via_part(contract, part, node_prefix):
    """(facet, part_at, node_id) for a `parts:` entry that sits `on` a
    facet, or (None, None, None).

    The tail shared by every place an occupant can inherit a facet straight
    from a `parts:` entry: a wrapper's forwarded aperture (`forwarded_part`,
    for a `mate-to` naming the wrapper, e.g. `card`) and a card's own cage
    named directly by id (`_seat_nested_occupants`'s `occupants:`).
    `node_id` is the facet node's rendered id, e.g. `"card--housing"` -
    matching what the `parts:` loop above writes for a part composed
    directly `on` that same node.
    """
    if not part or not part.get("on"):
        return None, None, None
    facet = _facets.facet_of(contract, part["on"])
    if not facet:
        return None, None, None
    return facet, part["at"], f"{node_prefix}--{part['on']}"


def _drawn_facet(facet, rotate):
    """`facet`, axis-swapped for the STRING a seated occupant's own
    `scale(...) rotate(rotate, ...)` draws (and for the matching
    `_tilt_offset` call that solves its `at`) - never for `data-tilt-facing`,
    which stays the facet's own true facing.

    A composed part `on` a facet with no rotate of its own is turned by its
    CONTAINER, from outside its own transform string - an ordinary Rotate
    applied AFTER that part's own Scale. A TOP-LEVEL, `mate-to`-seated
    occupant has no such container: it inherits its host's rotation as ITS
    OWN `rotate`, baked into the SAME string as the scale, where `rotate`
    (rightmost, so applied first to a point) comes BEFORE the scale -
    Rotate-then-Scale, the opposite order. At 0/180 the two orders agree;
    at 90/270 they do not (Rot90.Sy = Sx.Rot90), so a TOP-LEVEL occupant at
    90/270 has to swap which axis its OWN scale lands on to still
    foreshorten the same physical dimension its host's own (unrotated,
    container-turned) parts do.

    NOT for a NESTED `occupants:` seat (`_seat_nested_occupants`): that one
    IS drawn inside its card's own group, exactly like a composed part, so
    its `rotate` (the cage's own local rotate) is turned from outside by
    that group and needs no swap - applying one there regressed a
    previously-correct render.
    """
    if float(rotate or 0) % 360 not in (90, 270):
        return facet
    swapped = {"up": "left", "down": "right", "left": "up", "right": "down"}
    return {**facet, "facing": swapped[facet["facing"]]}


def _tilt_offset(local_q, size, rotate, facet):
    """Where `local_q` (a point in a part's own untransformed frame) lands
    relative to the part's own origin, when the part is drawn
    `translate(origin) scale(1,cos) rotate(rotate, size/2)`
    (`instance_group`'s `tilt` branch) - the EXACT composition, not an
    approximation: rotate about the part's own centre first (`seat_point`'s
    own `_turn`), then the facet's scale, which is about the part's own
    coordinate origin (0, 0) - NOT about the centre `rotate` just turned
    around. That second point is the one a per-axis "project `at`" shortcut
    misses: even a `local_q` sitting exactly on the part's own centre picks
    up a scale term from the centre's own (non-zero) offset from the
    origin, whenever the part itself is drawn rotated 90/270. Add `origin`
    to what this returns for the forward point; subtract it from a known
    target to solve for the `origin` (`at`) a seat needs.
    """
    cx, cy = size["w"] / 2.0, size["h"] / 2.0
    dx, dy = _turn((local_q[0] - cx, local_q[1] - cy), rotate)
    x, y = cx + dx, cy + dy
    if facet:
        c = _facets.cos_of(facet)
        if _facets.axis_of(facet) == "y":
            y *= c
        else:
            x *= c
    return x, y


def _seat_nested_occupants(lib, contract, g, inst_id, path, mirror, occupants,
                           occ_used, z_inset, z_group_lift, palette, inst_palette,
                           skin_overrides, attr_overrides, resolved):
    """Seat the configuration's occupants keyed to THIS instance's slots - and,
    to a fixed point, to occupants already seated in them (a plug in the
    optic, a boot on the plug) - inside the instance group `g`.

    Called for EVERY instance with a path (B3, deep addressing): a module in
    a bay, a part composed at any depth, a device placement. Its keys are the
    ones whose prefix is slot_key_prefix(path) - `bay-1/lc01/1` is seated by
    the adapter drawn at `bay-1/module/lc01` - so an occupant is drawn inside
    the innermost group holding its slot. A key whose value is "" empties the
    slot (P4): it counts as used when its host exists and draws nothing.

    Each seat is solve_seat - the device-level rule, in the card's frame -
    carried by the same trio draw_placement applies (z_inset / z_group_lift /
    data-z-lift), with `data-for` naming the host's path. A composed cage's
    own `lift` is its `host-lift`, because the occupant sits BESIDE the
    cage's group and not in it - the figure component_cages publishes as the
    cage's `lift`. A mirrored card mirrors every cage on it, so it refuses as
    a mirrored cage does. An occupant takes its host part's COMPONENT group
    (#511) exactly as a device occupant takes its host placement's - the map
    component_cages publishes as `occupant-attrs`; a card that declares no
    groups contributes nothing. Keys used are added to `occ_used`, which
    render_view reads to report a key nothing seated."""
    prefix = slot_key_prefix(path)
    # {host id: (key, spec, chain)} - `chain` is the refs already seated ON
    # THIS ONE SEAT, innermost last, which is what tells a default that loops
    # back on itself from two sibling slots shipping the same part.
    pending = {h: (key, spec, ())
               for h, (key, spec) in (occupants_under(prefix, occupants).items()
                                      if occupants and prefix is not None else ())}
    # AND WHAT EACH SLOT SHIPS HOLDING (B3, "The shipped default"): a part's
    # resolved default (manifest.slot_default) seats unless the configuration
    # keys that part - a configured key, `""` included, wins. Keyed None: a
    # default is no `occupants:` key, so nothing is added to `occ_used` for it.
    # Seated whether or not any configuration reached this instance, because
    # a default is the product's shipped state, like a composed part.
    for q in contract.get("parts") or []:
        if not q.get("id") or not q.get("at") or q["id"] in pending:
            continue
        shipped = slot_default(q, lib.resolve(q["ref"])[0])
        if shipped:
            pending[q["id"]] = (None, {"ref": shipped}, ())
    if not pending:
        return
    hosts = {q["id"]: {"ref": q["ref"], "at": q["at"], "rotate": q.get("rotate"),
                       "mirror": bool(mirror or q.get("mirror")),
                       "host-lift": float(q.get("lift") or 0.0),
                       "group": q.get("group")}
             for q in contract.get("parts") or [] if q.get("id") and q.get("at")}
    # A FILL ON A SPANNING SLOT IS REFUSED WHILE ITS BORES HOLD SOMETHING (B3,
    # "The duplex host"). Checked from the HOST side, here, because this is the
    # one place that knows both halves: the fill on the part's own slot - a key
    # of this instance, or what the part ships - is in `pending`, and its bores'
    # keys and defaults belong to the part's own contract, one level down.
    _conn = _connector_registry()

    def _res(ref):
        try:
            return lib.resolve(ref)[0]
        except (FileNotFoundError, ValueError, KeyError):
            return None
    # A KEY ON THE MODULE'S BACK IS SEATED BY THE REAR DRAWING (B3, Task 7i).
    # `bay-1/mtp1` names the MTP bulkhead on a cassette's back
    # (manifest.back_parts), which this instance - the cassette seen from the
    # front - does not draw. The rear view draws the back as a projection at
    # the module's own path and seats the key there (draw_placement), so here
    # it is handed on, the way render_view hands a key whose bay is on another
    # face to that face - with every occupant chained on it
    # (manifest.back_hosts). NOT counted as used here: render_view's check
    # asks manifest.key_on_back, and refuses one whose bay shows no back.
    back = back_parts(contract, _res) if (path or "").endswith("/module") else {}
    if back and prefix is not None:
        for host_id in (back_hosts(prefix, occupants, back) - set(hosts)) & set(pending):
            pending.pop(host_id)
    if not pending:
        return
    for host_id, (key, spec, _c) in pending.items():
        q = hosts.get(host_id)
        # A SLOT INSIDE A SLOT IS REFUSED (B3, manifest.slot_in_slot_at, the
        # gate nested_key_host - and so L12 - applies too): a key on a cage
        # wrapper's own aperture names the opening the wrapper's key already
        # names. Only a configured key - a default is the product's own.
        if (key is not None and q is not None and prefix is not None
                and slot_in_slot_at(path, contract, host_id, _res)):
            raise slot_in_slot_error(key, prefix, host_id)
        if spec is None or q is None or prefix is None:
            continue
        held = _res(q["ref"])
        if held is not None:
            refuse_spanned_overlap(f"{prefix}/{host_id}", q["ref"], held, _res,
                                   _conn, occupants)

    def _label(host_id, key):
        return f"occupants/{key}" if key else f"{path}/{host_id}: default"

    # `on` NAMED DIRECTLY, BY PART ID - unlike a device-level `mate-to`
    # naming a wrapper, an `occupants:` key already names the exact cage
    # (`_facet_via_part` below), so this needs no `forwarded_part` search.
    parts_by_id = {q["id"]: q for q in contract.get("parts") or [] if q.get("id")}
    comp_groups = contract.get("groups") or {}

    def _res(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None

    while pending:
        seated_now, chained = [], {}
        for host_id, (key, spec, chain) in pending.items():
            host = hosts.get(host_id)
            if host is None:
                continue
            if spec is None:
                if occ_used is not None:
                    occ_used.add(key)
                seated_now.append(host_id)
                continue
            at, orot, lift = solve_seat(lib, _label(host_id, key), spec["ref"],
                                        f"{path}/{host_id}", host)
            # AN OCCUPANT INHERITS ITS HOST'S TILT (mirrors the device-level
            # `mate-to` resolution in render_view, and the same
            # `_tilt_offset`) - fresh from the cage itself when `host_id`
            # names one of THIS card's own `parts:`, or carried forward
            # when `host_id` names a previously-seated occupant that
            # already carries one (a boot on a tilted optic). No OUTER
            # transform to carry through either way: `og` nests INSIDE `g`,
            # so this stays entirely in the card's own local frame.
            tilt_facet = tilt_node = target = None
            fpart = parts_by_id.get(host_id)
            tilt_facet, part_at, tilt_node = _facet_via_part(contract, fpart, inst_id)
            if tilt_facet:
                core = _res(fpart["ref"])
                hm = presented_interface(core, _res) if core else (None, None, None)
                if hm[1] is not None:
                    ox, oy = _tilt_offset(hm[1], core["size"], fpart.get("rotate"), tilt_facet)
                    target = (part_at[0] + ox, part_at[1] + oy)
                else:
                    tilt_facet = None
            if not tilt_facet and host.get("tilt"):
                tilt_facet, tilt_node = host["tilt"], host.get("tilt-on")
                host_c = _res(host["ref"])
                hm = presented_interface(host_c, _res) if host_c else (None, None, None)
                if hm[1] is not None:
                    ox, oy = _tilt_offset(hm[1], host_c["size"], host.get("rotate"), tilt_facet)
                    target = (host["at"][0] + ox, host["at"][1] + oy)
                else:
                    tilt_facet = None
            # NO AXIS SWAP HERE, unlike the mate-to path below: `og` is
            # drawn INSIDE `g`, the card's own group, so its `rotate` (the
            # CAGE's own local rotate) is turned by that group from
            # OUTSIDE og's transform through ordinary SVG nesting - the
            # same "composed part" situation `_drawn_facet`'s docstring
            # describes, not the "no container" one it swaps for.
            if tilt_facet and target is not None:
                occ_c = _res(spec["ref"])
                om = (occ_c.get("connection-points") or {}).get("mate") if occ_c else None
                if om:
                    ox, oy = _tilt_offset(om["at"], occ_c["size"], orot, tilt_facet)
                    at = [round(target[0] - ox, 4), round(target[1] - oy, 4)]
            local = occupant_local_id(host_id, spec)
            # THE HOST'S GROUP, AS A DEVICE OCCUPANT TAKES ITS HOST'S: the card
            # group's attrs under the occupant's own, its side written by
            # write_group_side, its states if it has them - the same map
            # component_cages publishes as this cage's `occupant-attrs`. An
            # occupant seated on an occupant inherits the chain's group.
            gname = host.get("group")
            grp = comp_groups.get(gname) or {}
            og, _ = instance_group(
                lib, spec["ref"], f"{inst_id}--{local}", at, None,
                group_merged_attrs(grp, spec.get("attrs")),
                None, None, skin_name=spec.get("skin", "default"),
                rotate=orot or None, palette=palette, inst_palette=inst_palette,
                z_inset=z_inset - lift, z_group_lift=z_group_lift + lift,
                skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                path=f"{path}/{local}", resolved=resolved, tilt=tilt_facet,
                # AND A SLOT INSIDE WHAT WAS JUST SEATED, keyed under the
                # occupant's own path - `bay-1/lc01-occupant/a`, half `a` of a
                # duplex plug seated on the adapter `lc01`. The same widening
                # draw_placement makes for a device-level seat, made here so
                # the two directions cannot disagree about whether a composed
                # part of an occupant is reachable.
                occupants=occupants, occ_used=occ_used)
            if tilt_facet:
                og.set("data-tilt-on", tilt_node)
                og.set("data-tilt", f"{tilt_facet['deg']:g}")
                # `data-tilt-facing` is in the frame of the COMPONENT THAT
                # DECLARES THE FACET (the card), same as `data-facet-facing`
                # on the facet node itself - not `og`'s own frame.
                og.set("data-tilt-facing", tilt_facet["facing"])
            if gname:
                write_group_side(og, gname, grp, spec.get("attrs"))
                if grp.get("states"):
                    apply_states(og, grp["states"], inst_palette)
            if lift:
                og.set("data-z-lift", f"{lift:g}")
            og.set("data-for", f"{path}/{host_id}")
            g.append(og)
            hosts[local] = {"ref": spec["ref"], "at": at, "rotate": orot,
                            "host-lift": lift, "group": gname,
                            "tilt": tilt_facet, "tilt-on": tilt_node}
            # AND WHAT THE OCCUPANT ITSELF SHIPS HOLDING. A plug's contract may
            # default a boot onto its own rear slot, and it ships that boot
            # however it got here - composed, configured, or seated as another
            # part's default. The configuration keys this one by the produced
            # id (`tx-occupant`), so it stays overridable. The guard is the
            # CHAIN, not a set of refs seen anywhere in this instance: two
            # sibling bores shipping the same plug each ship its boot, and
            # only a default that names a part already seated on THIS seat is
            # a cycle.
            ships = (lib.resolve(spec["ref"])[0] or {}).get("default")
            here = chain + (spec["ref"],)
            if ships and ships in here:
                raise ValueError(
                    f"{path}/{host_id}: default {ships} is a cycle - "
                    + " ships ".join(here + (ships,)))
            if ships and local not in pending:
                chained[local] = (None, {"ref": ships}, here)
            if occ_used is not None and key:
                occ_used.add(key)
            seated_now.append(host_id)
        if not seated_now:
            raise ValueError(
                ", ".join(sorted(_label(h, k) for h, (k, _, _c) in pending.items()))
                + f": names no cage on {path} (or no occupant seated before it)")
        for host_id in seated_now:
            del pending[host_id]
        pending.update(chained)


def instance_group(lib, ref, inst_id, at, label, attrs, group, rel_pos, skin_name="default", rotate=None, mirror=False, palette=None, skin_overrides=None, attr_overrides=None, path=None, resolved=None, depth=0, centre=None, inst_palette=None, z_inset=0.0, z_group_lift=0.0, seated=None, bay_attrs=None, occupants=None, occ_used=None, in_port=False, tilt=None, inherited_fields=None):
    contract, skins = lib.resolve(ref)
    comp_name = ref.split("/")[-1].split("@")[0]
    if skin_overrides and comp_name in skin_overrides:
        skin_name = skin_overrides[comp_name]
    # BY COMPONENT NAME, AND THEN BY THIS INSTANCE. `component-attrs` was keyed by
    # the component alone, which says a true thing about every copy of a part and
    # cannot say anything about one of them. The ASR 9001-S is the same metal as
    # the 9001 with two of its four SFP+ ports disabled until a licence is
    # applied: both chassis draw six `std/sfp-ganged`, so `{sfp-ganged: ...}`
    # marks all six - the two CLUSTER ports included - when two are meant
    # (roc-ops/Portrayal#193). Keying by the placement or bay id says it exactly,
    # and the two compose: the component entry is the default for every copy and
    # the instance entry narrows it.
    extra_attrs = (attr_overrides or {}).get(comp_name)
    per_instance = (attr_overrides or {}).get(inst_id)
    if per_instance:
        extra_attrs = {**(extra_attrs or {}), **per_instance}
    if palette is not None:
        comp = ref.split("@")[0]
        # every segment name this component's artwork draws, so a shape-changing
        # state can turn the unlit ones off by name rather than by omission
        vocabulary = set()
        for spec in (contract.get("elements") or {}).values():
            for st in spec.get("states") or []:
                if isinstance(st, dict):
                    vocabulary.update(st.get("lights") or ())
        for spec in (contract.get("elements") or {}).values():
            for st in spec.get("states") or []:
                style = state_style(st, vocabulary)
                if style:
                    palette[(comp, st["name"])] = style
        # AND THE STATES A COMPOSER PUTS ON A COMPOSED PART. A component that
        # draws nothing itself still names meanings: dell/rj45-port-14g has no
        # skin and no elements, and exists only to attach ISM table 11 to
        # common/rj45-port@4 through a `states` override on `parts:`. Harvesting
        # `elements` alone let those names reach `data-states` and never reach
        # the stylesheet, so setting one selected a class no rule matched and
        # the lamp did not light.
        for part in contract.get("parts") or []:
            for sts in (part.get("states") or {}).values():
                for st in sts or []:
                    style = state_style(st, vocabulary)
                    if style:
                        palette[(comp, st["name"])] = style
    skin_file = skins / f"{skin_name}.svg"
    if not skin_file.exists():
        # A COMPONENT NEED NOT HAVE A SKIN CALLED `default`, and one deliberately
        # does not: `common/qsfp-transceiver` declares `skins: [lc]` alone,
        # because parts are emitted per skin and an MPO face would need a second
        # skin nobody has drawn. Naming that optic as an occupant therefore
        # failed with a bare FileNotFoundError on default.svg - a stack trace
        # where the answer is "say which face you want".
        #
        # One skin means no choice to make, so make it. More than one is a real
        # question and the error now asks it by name.
        declared = [n for n in (contract.get("skins") or [])
                    if (skins / f"{n}.svg").exists()]
        if len(declared) == 1 and skin_name == "default":
            skin_file = skins / f"{declared[0]}.svg"
        else:
            raise ValueError(
                f"{ref}: no skin {skin_name!r}. It has "
                + (f"{declared} - name one in the configuration's `skins:`, "
                   f"as `skins: {{{comp_name}: {declared[0]}}}`" if declared
                   else "no skin files at all"))
    skin = ET.parse(skin_file).getroot()
    path = path or inst_id
    if resolved is not None:
        resolved[ref] = contract["version"]
    g = ET.Element(f"{{{SVG_NS}}}g")
    g.set("id", inst_id)
    g.set("data-path", path)
    g.set("data-class", contract.get("class", "component"))
    # A PORT INSIDE A PORT - the std core of a composed port - is the inner
    # part of one connector, not a second one (see the `parts:` loop below).
    if in_port and contract.get("class") == "port":
        g.set("data-inner", "1")
    # HOW IT MOVES, beside WHAT IT IS. The 3D viewer decided what could be
    # ejected from a hardcoded class list, so every new removable type meant
    # editing that list - and a transceiver, which is removable, was not on it.
    # See roc-ops/Portrayal#3.
    if contract.get("behaviour"):
        g.set("data-behaviour", contract["behaviour"])
    g.set("data-ref", f"{ref}:{contract['version']}")
    # A cavity is a hole you look INTO - a port aperture, a cage. A MODULE is a
    # solid body that fills its bay, and its depth says how far it reaches into
    # the chassis, not that the face has an N-mm hole in it. Emitting data-depth
    # for one rendered every PSU and fan as an empty recess in 3D. The depth is
    # still carried, as data-body-depth, so it stays addressable.
    #
    # AND SO IS ANYTHING THAT `mounts`, which this stopped one class short of.
    # `mounts` means it attaches to a surface - a rack ear, a label, a ground
    # lug, a bolted handle - so it stands ON the metal and there is no hole
    # behind it. The rear handle read as a 49.59 mm recess the shape of its own
    # outline: from straight on you saw its face at the bottom of the pit, and
    # from any angle you saw the pit's walls and no face at all. Its three
    # protruding boxes were correct the whole time and were being built inside
    # a hole that should never have existed.
    # An explicit `relief.cavity` still wins, because that is a part saying it
    # really does have a recess in it - a screw head's driver slot, for one.
    if contract["size"].get("d"):
        solid = (contract.get("kind") == "module"
                 or contract.get("behaviour") == "mounts")
        aperture = not solid or (contract.get("relief") or {}).get("cavity")
        g.set("data-depth" if aperture else "data-body-depth", str(contract["size"]["d"]))
    relief = contract.get("relief")
    if relief:
        if relief.get("wall"):
            g.set("data-wall", relief["wall"])
        if relief.get("walls") == "inside":
            g.set("data-walls", "inside")
        if relief.get("cavity"):
            g.set("data-cavity", relief["cavity"])
        if relief.get("round"):
            g.set("data-round", "1")
    merged = {}
    merged.update(contract.get("attrs") or {})
    # A HOST'S FIELD REACHES A COMPOSED PART THAT DECLARES THE SAME FIELD.
    # kit/fields.js already paints every matching node inside a part's group at
    # runtime, composed children included; the build now agrees, so a generic can
    # compose a coloured part instead of redrawing it (pluggables-heads decision 4).
    own_fields = contract.get("fields") or {}
    merged.update({k: v for k, v in (inherited_fields or {}).items() if k in own_fields})
    merged.update(extra_attrs or {})
    merged.update(attrs or {})
    for k, v in data_attrs(merged).items():
        g.set(k, v)
    if group:
        g.set("data-group", group)
    if rel_pos is not None:
        g.set("data-rel-pos", str(rel_pos))
    if contract.get("states"):
        g.set("data-states", " ".join(state_names(contract["states"])))
    # HUNG BY ITS CENTRE WHEN A CENTRE IS GIVEN. Read left to right, the
    # transform states the intent directly: go to where this thing belongs,
    # turn it, and put its middle there.
    #
    #     translate(centre) rotate(deg) translate(-w/2, -h/2)
    #
    # The alternative - translate to a pre-compensated top-left and then rotate
    # about the component's own centre - is algebraically the same, and it is
    # where both of today's placement bugs came from. It makes the CALLER solve
    # backwards for an origin that lands the ROTATED box in the right place, and
    # two callers solved it two different ways: render_view derived the offset
    # from the bay, swap.js from the component, and they agreed only when the
    # occupant happened to match its slot. Nothing here is scaled; both forms are
    # a rotation and a translation and the drawing stays at true millimetre scale.
    #
    # `at` is still honoured for placements, which are positioned by their own
    # top-left corner and have no container to be centred in.
    cw, chh = contract["size"]["w"], contract["size"]["h"]
    if centre is not None:
        tf = f"translate({centre[0]:g},{centre[1]:g})"
        if rotate:
            tf += f" rotate({rotate})"
        tf += f" translate({-cw / 2:g},{-chh / 2:g})"
    else:
        tf = f"translate({at[0]},{at[1]})"
        # SCALED BEFORE IT TURNS. A part `on` a facet keeps its true size and
        # is only foreshortened by the facet's own cos, along the facet's
        # axis - `rotate` still turns the true box (facets.projected_box:
        # "the rotated true box, scaled about the part origin"), so the scale
        # has to land between the translate and the rotate, not after it.
        if tilt:
            tf += " " + _facets.scale_transform(tilt)
        if rotate:
            tf += f" rotate({rotate} {cw / 2} {chh / 2})"
    # MIRRORED LAST, so it flips the component about its OWN vertical centre
    # line and leaves the box exactly where `at` and `rotate` put it. Written
    # as a translate-then-negate rather than scale(-1,1) about a computed
    # centre, because the second form has to know where the centre ended up
    # and this one does not.
    # HANDEDNESS IS NOT ROTATION. rotate: 180 is the flip this vocabulary could
    # already express and it is the wrong one for a PCIe bracket: it turns the
    # louvre row to the top and the retention tab to the bottom. A riser whose
    # cards face the other way needs the reflection, not the half-turn.
    if mirror:
        tf += f" translate({cw:g},0) scale(-1,1)"
    g.set("transform", tf)
    title = ET.SubElement(g, f"{{{SVG_NS}}}title")
    title.text = label or inst_id
    # rewrite ids/url-refs across the WHOLE skin at once so a <defs> pattern in
    # one child is still resolvable from url(#...) references in its siblings
    holder = ET.Element(f"{{{SVG_NS}}}g")
    for child in list(skin):
        holder.append(copy.deepcopy(child))
    rewrite_ids(holder, inst_id, contract, path, skip=holder, in_port=in_port)
    # TEXT FROM ATTRS, so one carrier covers a catalogue instead of a file per
    # row. `merged` is the contract's attrs under the placement's, which is
    # already the precedence every other attr consumer uses.
    fill_from_attrs(holder, merged)
    for child in list(holder):
        g.append(child)
    for feat in (contract.get("relief") or {}).get("features") or []:
        raw_feat = feat
        # A FACET COMPILES TO A WEDGE FIRST - before `_inset_feature` gets a
        # look at it, so an inset moves the derived numbers exactly as it
        # would a hand-written `out`/profile (see `_facet_wedge`,
        # `_inset_facet_profile`).
        feat = _facet_wedge(feat, contract)
        pre_out = feat.get("out") if raw_feat.get("facet") else None
        feat = _inset_feature(feat, z_inset, z_group_lift)
        if feat is None:
            continue
        feat = _inset_facet_profile(raw_feat, pre_out, feat)
        want = f"{inst_id}--{feat['node']}"
        for node in g.iter():
            if node.get("id") == want:
                for zk in ("top", "sink", "out", "dome", "vent", "cyl", "lift", "bar", "uhandle", "dia"):
                    if feat.get(zk) is not None:
                        node.set(f"data-z-{zk}", str(feat[zk]))
                if feat.get("profile"):
                    # depth that varies across the node, as x:out pairs; `out`
                    # goes out beside it as the single figure everything else reads
                    node.set("data-z-profile", ",".join(f"{x:g}:{o:g}" for x, o in feat["profile"]))
                if feat.get("profile-y"):
                    node.set("data-z-profile-y", ",".join(f"{y:g}:{o:g}" for y, o in feat["profile-y"]))
                if feat.get("color"):
                    node.set("data-z-color", feat["color"])
                if feat.get("hole-color"):
                    node.set("data-z-hole-color", feat["hole-color"])
                if feat.get("pocket"):
                    # A POCKET IS A CAVITY THE KIT ALREADY KNOWS HOW TO BUILD.
                    # relief.js collects every `[data-depth]` as a recess with
                    # walls and a floor taken from that node's own art, so this
                    # needs no new geometry - only a way for a feature to say it
                    # is a hole in a face rather than a lump on one.
                    node.set("data-depth", str(feat["pocket"]))
                    if (contract.get("relief") or {}).get("wall"):
                        node.set("data-wall", contract["relief"]["wall"])
                if feat.get("shape"):
                    # EXTRUDE THE OUTLINE, NOT THE BOX. Only meaningful next to
                    # `out`; the kit falls back to the box if the node's art
                    # yields no usable contour.
                    node.set("data-z-shape", "1")
                if feat.get("knurl"):
                    node.set("data-z-knurl", "1")
                if feat.get("thread"):
                    node.set("data-z-thread", str(feat["thread"]))
                if feat.get("facet"):
                    # THE FACET ITSELF, for relief.js to build a tilted plane
                    # from rather than a stepped profile - the profile above is
                    # what a viewer with no 3D kit still gets.
                    node.set("data-facet-deg", f"{feat['facet']['deg']:g}")
                    node.set("data-facet-facing", feat["facet"]["facing"])
                break
    part_groups = []
    # WHERE A COMPOSED PART SITS IN THE STACK IS A PROPERTY OF WHAT IT IS.
    # A bezel frames an aperture, so the aperture belongs ON TOP of the plate
    # and the default - skin first, parts after - is right for it. A BLANKING
    # PLATE IS THE OTHER WAY ROUND: it composes the bracket for its outline and
    # then covers the connector opening with vented metal, and drawn in the
    # default order the bracket's own dark opening lands back over the vents and
    # the plate renders as an empty slot. `behind: true` says which.
    behind_at = 1                       # after the <title>, before the skin
    # A CARD'S PORTS CARRY THE CARD'S GROUPS (#511). A part joins a group the
    # component itself declares, and is drawn exactly as a device placement in
    # a device group is: the group's attrs under its own, then the group's side
    # written by write_group_side. This runs wherever the component is drawn -
    # a device placement, a device bay's module, a module in a nested bay - so
    # the depth a card is seated at changes nothing about what its ports say.
    # A device never overrides a card's groups: the bay's own group stays on
    # the bay element (render_view), and names are local to the component.
    comp_groups = contract.get("groups") or {}
    # AN INNER PORT IS MARKED. A composed port - common/rj45-eth around a
    # std/rj45, common/qsfp28-cage around a std/qsfp-ganged - draws its core as a
    # data-class `port` of its own, nested inside the outer one. The outer port
    # is the one that carries the facts (media, speed, group); the core keeps
    # its class, so no selector breaks, and says `data-inner="1"` so an audit
    # can skip it. Handed down the whole composition, not just one level.
    parts_in_port = in_port or contract.get("class") == "port"
    for part in contract.get("parts") or []:
        pgrp = comp_groups.get(part.get("group")) or {}
        # `on` NAMES A FACET, NOT A GROUP. It points at a relief feature on
        # THIS SAME CONTRACT that declares `facet` (design doc: "`on`: the
        # `node` of a relief feature on the same contract"), so the lookup
        # is against `contract`, never the part's own component.
        tilt = _facets.facet_of(contract, part["on"]) if part.get("on") else None
        pg, _ = instance_group(lib, part["ref"], f"{inst_id}--{part['id']}",
                               part["at"], None,
                               group_merged_attrs(pgrp, part.get("attrs")), None, None,
                               skin_name=part.get("skin", "default"),
                               inherited_fields={k: merged[k] for k in (contract.get("fields") or {})
                                                 if k in merged},
                               rotate=part.get("rotate"), mirror=bool(part.get("mirror")),
                               # A LIFTED PART'S FEATURES ARE STILL MEASURED
                               # FROM THE PANEL. `lift` raises where a composed
                               # part sits, and the kit builds a box as
                               # `out - lift` - so a clip whose own `out` is 3.0,
                               # composed onto a shroud lifted 17.76, asked for a
                               # box 14.76 mm DEEP IN THE WRONG DIRECTION and
                               # rendered as nothing. Raising the child's
                               # absolute figures by the lift is what makes the
                               # two agree: 3.0 becomes 20.76, the kit subtracts
                               # 17.76 again, and 3.0 of clip lands on the
                               # shroud's outer face.
                               z_inset=z_inset - (part.get("lift") or 0),
                               z_group_lift=z_group_lift + (part.get("lift") or 0),
                               palette=palette,
                               inst_palette=inst_palette,
                               skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                               path=f"{path}/{part['id']}", resolved=resolved,
                               in_port=parts_in_port, tilt=tilt,
                               # a slot on a composed part, at any depth (B3)
                               occupants=occupants, occ_used=occ_used)
        if tilt:
            # THE FACET NODE'S FULL ID, so a consumer can walk straight from
            # the tilted part to the wedge it stands on without knowing this
            # component's own id scheme.
            pg.set("data-tilt-on", f"{inst_id}--{part['on']}")
            pg.set("data-tilt", f"{tilt['deg']:g}")
            # THE FACET'S OWN FRAME, not the device's - unlike the position
            # math above, this is never rotated to device-frame: relief.js
            # reads it relative to the part's own (pre-rotate) orientation,
            # same as `data-facet-facing` on the facet node itself.
            pg.set("data-tilt-facing", tilt["facing"])
        if part.get("group"):
            write_group_side(pg, part["group"], pgrp, part.get("attrs"))
        # WHAT A COMPOSED LAMP MEANS IS THE COMPOSER'S TO SAY. A component
        # declares what a lamp IS and can only guess what it MEANS - the same
        # reasoning apply_states already carries for device placements, and the
        # same need one level down: a card composing a generic jack has an
        # indicator table for it and had no way to attach one. Without this the
        # only route was a wrapper that redraws the lamps over the ones it
        # composes, which is two nodes for one indicator.
        # A part's own table wins over its group's, as on a device placement.
        part_states = part.get("states") or pgrp.get("states")
        if part_states:
            apply_states(pg, part_states, inst_palette)
        # a part on a protruding parent recesses from THAT surface, not the panel
        if part.get("lift"):
            pg.set("data-z-lift", str(part["lift"]))
        if part.get("behind"):
            g.insert(behind_at, pg)
            behind_at += 1
        else:
            g.append(pg)
        # A `behind` PART MUST NOT JOIN part_groups. That list exists so the
        # re-raise below can put composed parts back on top of a raised bezel,
        # and a part that asked to sit UNDER this component's art would be
        # dragged to the front by it - which is exactly what happened: the
        # blanking plates' vents were drawn, and then the bracket they compose
        # was raised over them again and the slot rendered empty.
        if not part.get("behind"):
            part_groups.append(pg)
    for feat in (contract.get("relief") or {}).get("features") or []:
        raw_feat = feat
        feat = _facet_wedge(feat, contract)
        pre_out = feat.get("out") if raw_feat.get("facet") else None
        feat = _inset_feature(feat, z_inset, z_group_lift)
        if feat is None:
            continue
        feat = _inset_facet_profile(raw_feat, pre_out, feat)
        want = f"{inst_id}--{feat['node']}"
        for node in g.iter():
            if node.get("id") == want:
                for zk in ("top", "sink", "out", "dome", "vent", "cyl", "lift", "bar", "uhandle", "dia"):
                    if feat.get(zk) is not None:
                        node.set(f"data-z-{zk}", str(feat[zk]))
                if feat.get("profile"):
                    # depth that varies across the node, as x:out pairs; `out`
                    # goes out beside it as the single figure everything else reads
                    node.set("data-z-profile", ",".join(f"{x:g}:{o:g}" for x, o in feat["profile"]))
                if feat.get("profile-y"):
                    node.set("data-z-profile-y", ",".join(f"{y:g}:{o:g}" for y, o in feat["profile-y"]))
                if feat.get("color"):
                    node.set("data-z-color", feat["color"])
                if feat.get("hole-color"):
                    node.set("data-z-hole-color", feat["hole-color"])
                if feat.get("pocket"):
                    # A POCKET IS A CAVITY THE KIT ALREADY KNOWS HOW TO BUILD.
                    # relief.js collects every `[data-depth]` as a recess with
                    # walls and a floor taken from that node's own art, so this
                    # needs no new geometry - only a way for a feature to say it
                    # is a hole in a face rather than a lump on one.
                    node.set("data-depth", str(feat["pocket"]))
                    if (contract.get("relief") or {}).get("wall"):
                        node.set("data-wall", contract["relief"]["wall"])
                if feat.get("shape"):
                    # EXTRUDE THE OUTLINE, NOT THE BOX. Only meaningful next to
                    # `out`; the kit falls back to the box if the node's art
                    # yields no usable contour.
                    node.set("data-z-shape", "1")
                if feat.get("knurl"):
                    node.set("data-z-knurl", "1")
                if feat.get("thread"):
                    node.set("data-z-thread", str(feat["thread"]))
                if feat.get("facet"):
                    node.set("data-facet-deg", f"{feat['facet']['deg']:g}")
                    node.set("data-facet-facing", feat["facet"]["facing"])
                # bezel plates ('out') paint over composed parts: raise direct
                # children to the end of the instance group. Only when there ARE
                # composed parts - otherwise this reorders the skin's own draw
                # order and a raised base plate paints over its own detail.
                #
                # AND NEVER THE BASE PLATE, parts or no parts. The "otherwise"
                # above named the failure exactly and then guarded only half of
                # it: a raised base plate paints over its own detail whether or
                # not the component composes anything. smartoptics/dcp-404
                # declares `out` on `body`, composes cages, lamps and warning
                # triangles, and so took this branch - its plate was moved to the
                # end and covered every vent and every silkscreen line on the
                # faceplate. The cages and lamps still showed, because the
                # re-raise below puts composed parts back on top, which is what
                # made it read as "the printing is missing" rather than "the
                # plate is in front".
                #
                # The base plate is the first thing the skin DRAWS; everything
                # else in the skin is drawn ON it. Composed parts are appended
                # after the skin and carry `data-ref`, so the skin's own children
                # are the ones without it - and `defs`, `style` and the rest
                # define without drawing, so they are not the base plate however
                # early they appear. Missing that was worth one wrong answer: the
                # first cut of this guard took `defs` for the plate and changed
                # nothing.
                nondrawing = ("title", "defs", "style", "desc", "metadata")
                skin_children = [c for c in g
                                 if not c.tag.split("}")[-1] in nondrawing
                                 and not c.get("data-ref")]
                is_base_plate = bool(skin_children) and node is skin_children[0]
                if contract.get("parts") \
                        and any(feat.get(k) is not None for k in ("out", "cyl", "bar", "uhandle", "dome")) \
                        and node in list(g) \
                        and not is_base_plate:
                    g.remove(node)
                    g.append(node)
                break

    # AND THEN THE COMPOSED PARTS GO BACK ON TOP, because the raise above put
    # the very thing it was meant to protect them from in front of them.
    #
    # `ufispace/psu-132-ac` composes a C14 inlet and declares `inlet-recess` as
    # a bezel standing 1.8mm proud. The recess is an opaque 28.6 x 31.4 slab and
    # the inlet is 28 x 20 inside it, so raising the bezel to the end of the
    # group painted the inlet out completely: twenty-eight UfiSpace and Juniper
    # supplies drew a blank grey panel where the keyed shroud and three pins
    # should be. The part was in the contract, in the SVG and in the DCIM
    # export - missing only from the picture, which is the one place anybody
    # looks to see whether a supply takes a cord.
    #
    # A composed part is mounted IN its parent, so it is never hidden by the
    # parent's own artwork. The bezel keeps its raise relative to the skin,
    # which is what that code is for.
    for pg in part_groups:
        if pg in list(g):
            g.remove(pg)
            g.append(pg)

    # A CARRIER IS A MODULE WITH BAYS OF ITS OWN. The A9K-MOD80/160/200/400 hold
    # two MPAs each and the SIP-700 holds four SPAs, and until this loop existed
    # those bays were not merely empty, they were UNFILLABLE: render_view seats
    # occupants into the DEVICE's bays and nothing recursed into a seated
    # module's. A MOD card in a slot drew two dark rectangles that nothing could
    # ever occupy.
    #
    # The occupant is appended INSIDE g, which already carries this instance's
    # translate/rotate, so a nested bay's `at` is used as the local coordinate it
    # is - no composing transforms by hand, which is the step that has gone wrong
    # here before.
    #
    # The skin already draws the opening (a <rect id="bay-0">), so this does not
    # add a second one; it makes the existing rect addressable and seats over it.
    for bay_id, bay in sorted((contract.get("bays") or {}).items()):
        if not isinstance(bay, dict) or not bay.get("at"):
            continue
        want = f"{inst_id}--{bay_id}"
        # WHAT THE OPENING IS OFF THE PANEL, THE OCCUPANT IS TOO. `relief.js`'s
        # liftOf sums data-z-lift up the ANCESTOR chain, and the occupant is
        # appended to `g` rather than beside its opening (see the comment on the
        # append below - the flat coordinate space is deliberate), so it inherits
        # nothing from the group the opening sits in. On a carrier whose plate
        # stands proud that buried both: smartoptics/dcp-f-a22 holds its two PPM
        # bays in a block 44 off the chassis, and the modules seated in them sat
        # at the panel plane behind unbroken metal - the dcp-404's blank-face
        # failure, in the one place restructuring the skin cannot reach.
        # A component bay declares no lift of its own; it takes one from a relief
        # feature naming the opening, which the two loops above have already
        # applied by the time this runs.
        # A BAY IS A GROUP HOLDING ITS OPENING AND ITS OCCUPANT, on a component
        # exactly as on a device face. It was a bare rect with the occupant
        # appended somewhere else entirely, and everything downstream assumes the
        # group shape, so both of the symptoms that made nested bays look broken
        # fell out of the difference:
        #   shell.js reads occupancy as `el.querySelector('[data-ref]')` - a
        #   DESCENDANT query - so an occupied nested bay always read "open"; and
        #   swap.js does `g.querySelector('#<id>--module')?.remove()` then
        #   `g.appendChild(...)`, which against a rect removed nothing and
        #   appended the new occupant INSIDE a <rect>, where SVG will not draw
        #   it. The drawing did not change and the DOM claimed two occupants.
        # The skin's rect becomes `--opening`, as a device bay's does, and the
        # group takes its place in the SKIN'S OWN DRAW ORDER rather than at the
        # end - the opening is a hole in the plate and has to stay where the
        # plate put it.
        bay_lift = None
        opening = parent_of = None
        for node in g.iter():
            if node.get("id") == want:
                opening = node
                break
        if opening is not None:
            for cand in g.iter():
                if opening in list(cand):
                    parent_of = cand
                    break
        bay_g = None
        if opening is not None and parent_of is not None:
            bay_lift = opening.get("data-z-lift")
            bay_g = ET.Element(f"{{{SVG_NS}}}g")
            bay_g.set("id", want)
            bay_g.set("data-path", f"{path}/{bay_id}")
            bay_g.set("data-class", "bay")
            # THE LIFT BELONGS TO THE BAY, NOT TO THE HOLE IN IT. relief.js sums
            # data-z-lift up the ancestor chain, so with the occupant inside this
            # group the group is where one reading serves both. Leaving it on the
            # opening AND copying it onto the occupant - which is what this did
            # while they were siblings - would now count it twice.
            if bay_lift:
                bay_g.set("data-z-lift", bay_lift)
                del opening.attrib["data-z-lift"]
            parent_of.insert(list(parent_of).index(opening), bay_g)
            parent_of.remove(opening)
            opening.set("id", f"{want}--opening")
            bay_g.append(opening)
        else:
            # L48 reports a bay whose id names nothing in the skin; without an
            # anchor there is no place in the drawing to put the group, so the
            # occupant is appended as it always was rather than dropped.
            pass
        # A CONFIGURATION CAN SEAT A NESTED BAY. `seated` is the configuration's
        # bay map, keyed by bay path without the `/module` steps - `riser-1/
        # slot-1` - and it wins over the module's own default, an empty string
        # meaning empty. Before this a riser's slots only ever held their
        # default, so no configuration could put a card in one.
        bay_path = f"{path}/{bay_id}".replace("/module/", "/") if path else bay_id
        occupant = seated_ref(seated, bay_path, bay)
        if not occupant or depth >= MAX_BAY_DEPTH:
            continue
        # a module's OWN default has no key inside a bay (B3)
        refuse_bay_module_default(lib, occupant, f"{path}/{bay_id}")
        bw, bh = bay_size(bay)
        b_at = bay["at"]
        if bay.get("rotate") in (90, 270):
            d = (bw - bh) / 2.0
            b_at = [b_at[0] + d, b_at[1] - d]
        # AND ITS RELIEF IS MEASURED FROM THE SAME PLANE THE OPENING IS ON. Giving
        # the occupant the opening's lift moves the module; its own `out` values
        # are absolute distances from the PANEL, so they have to move with it or
        # every feature on it builds inside out. Seating smartoptics/
        # ppm-ad1-1510@1 in the A22's raised block put 24 of them at negative
        # extent - a caption `out: 0.15` against a summed lift of 44 - and it went
        # unseen only because the bay's default is ppm-dummy, which declares no
        # relief at all. The other accepted occupant is the one the ILA set exists
        # for.
        occ_lift = float(bay_lift or 0)
        sub, _ = instance_group(
            lib, occupant, f"{inst_id}--{bay_id}--module", b_at,
            None, (bay_attrs or {}).get(bay_path), None, None, rotate=bay.get("rotate"),
            mirror=bool(bay.get("mirror")), palette=palette,
            inst_palette=inst_palette,
            skin_overrides=skin_overrides, attr_overrides=attr_overrides,
            path=f"{path}/{bay_id}/module", resolved=resolved, depth=depth + 1,
            z_inset=z_inset - occ_lift, z_group_lift=z_group_lift + occ_lift,
            seated=seated, bay_attrs=bay_attrs,
            occupants=occupants, occ_used=occ_used)
        # BEHIND THE FACEPLATE, NOT ON IT. Appending is right for a drive in a
        # cage and wrong for a card in a riser: what shows of a PCIe bracket is
        # its working area through a punched window and its retention tab clear
        # of the plate, with the flange end covered by the metal. `behind: true`
        # inserts the occupant before the skin - the same word and the same
        # mechanism `parts:` has carried all along. It only means anything if
        # the skin has real holes; over a stroked outline the occupant vanishes.
        # `behind` moves the WHOLE BAY to the front, not just its occupant. The
        # group has to stay one node for the tree and the swap to find it, and
        # moving it wholesale is what keeps the skin painting over the card: on
        # the Dell risers the skin is three invisible anchor rects and the plate
        # is a composed part appended after them, so a bay group at behind_at
        # still ends up under the metal, exactly as the loose occupant did.
        if bay_g is not None:
            bay_g.append(sub)
            if bay.get("behind"):
                for holder in g.iter():
                    if bay_g in list(holder):
                        holder.remove(bay_g)
                        break
                g.insert(behind_at, bay_g)
                behind_at += 1
        elif bay.get("behind"):
            g.insert(behind_at, sub)
            behind_at += 1
        else:
            g.append(sub)
    # AN OPTIC IN A CAGE ON A SEATED CARD (#484, R2). A configuration's
    # `occupants:` keys such a cage by the MODULE-LESS path - `front-6/xg0` -
    # the convention its nested `bays:` keys already use (bay_path above), and
    # this is the module those keys address when `path` is `<bay>/module`.
    # AND A SLOT AT ANY DEPTH (B3): every instance with a path seats the keys
    # whose prefix is its own slot key, a composed adapter's bores included.
    # Seated INSIDE g, which carries this instance's translate/rotate, so the
    # occupant inherits the bay transform exactly as the card's own parts do
    # and nothing here composes it by hand; the mate points are the card-frame
    # ones, solved by the same seat_point/seat_at as a device-level seat and
    # published by component_cages as this cage's `mate`.
    _seat_nested_occupants(lib, contract, g, inst_id, path, mirror, occupants,
                           occ_used, z_inset, z_group_lift, palette, inst_palette,
                           skin_overrides, attr_overrides, resolved)
    # EVERY DECLARED CONNECTION POINT REACHES THE DRAWING, not just `mate`.
    # This function read `mate` to place an occupant and dropped the rest, so a
    # part's optical-tx, power or cable point existed in the contract and in no
    # place a consumer could reach. Spec B's cabling library needs `cable`; A's
    # transceivers get their optical axes back for nothing.
    #
    # THE MARKER IS INERT ON PURPOSE. It carries no data-z-*, no data-ref, no
    # data-path and no data-class, because relief.js decides what exists in 3D
    # by querying the DOM for attributes - its own comment warns that every
    # query is a chance to see data it should not - and shell.js reads
    # `[data-ref]` as "this bay is occupied". A marker that carried either would
    # become a phantom box or a phantom module.
    #
    # The point is in THIS PART'S OWN FRAME, under the instance group, which is
    # the node that carries data-z-lift. It does NOT carry data-z-out: `out` is
    # written onto SKIN NODES (see the decor loop's `r.set("data-z-out", ...)`
    # and the relief-feature loop above), which are siblings or descendants of
    # this marker, never its ancestors. So a consumer resolves the point the way
    # relief.js's liftOf resolves a feature - sum data-z-lift up the ancestor
    # chain and apply the group transforms - and finds nothing to add for
    # protrusion on that walk. A point that sits `on:` a relief feature says so
    # with `data-cp-on` instead, naming the node whose rear is its z - the
    # node's absolute data-z-out, or for a `cyl` feature its far end, the
    # node's summed data-z-lift plus its data-z-cyl - the different mechanism
    # kit/relief.js's note on resolveCablePoint asked for.
    #
    # EMITTED LAST, DELIBERATELY, AFTER EVERY `behind_at` INSERTION ABOVE HAS
    # RUN. The `behind_at = 1` initialisation above, with its "after the
    # <title>, before the skin" comment, is an index into `g`'s children that
    # assumes `g` holds only the <title> when the counter is initialised, and
    # every later `g.insert(behind_at, ...)` - behind parts, bay groups -
    # counts on that assumption staying true for the whole function. A marker
    # appended earlier is a child that arithmetic never accounted for, and it
    # silently shifts every one of those inserts one slot off, which is
    # exactly what put a base plate over parts it should sit under. Markers
    # draw nothing, so where they land in the children list is irrelevant to
    # draw order - which is precisely why they belong here and not mixed in
    # with the attribute assignments above.
    for cp_name in sorted(contract.get("connection-points") or {}):
        cp = (contract["connection-points"] or {})[cp_name]
        mk = ET.SubElement(g, f"{{{SVG_NS}}}g")
        mk.set("data-cp", cp_name)
        mk.set("data-cp-at", f"{cp['at'][0]:g} {cp['at'][1]:g}")
        if cp.get("direction"):
            mk.set("data-cp-dir", cp["direction"])
        # THE FEATURE THE POINT SITS ON, BY ITS COMPILED ID (pluggables D). A
        # point `on:` a relief feature is on that feature's far face, not on
        # this part's own face - a cable leaves a boot at the boot's rear end.
        # The feature's data-z-out is where relief.js builds that face (for a
        # `cyl`, its summed data-z-lift plus data-z-cyl), so naming the node
        # lets cablePoints read the numbers the solid is built from rather
        # than re-deriving them. Not a data-z-* key: the
        # marker must stay invisible to every relief query (see above).
        if cp.get("on"):
            mk.set("data-cp-on", f"{inst_id}--{cp['on']}")
    return g, contract


def text_el(x, y, s, size=2.2, anchor="middle", fill="#c7ccd1"):
    t = ET.Element(f"{{{SVG_NS}}}text")
    t.set("x", f"{x:g}")
    t.set("y", f"{y:g}")
    t.set("font-family", "sans-serif")
    t.set("font-size", f"{size:g}")
    t.set("text-anchor", anchor)
    t.set("fill", fill)
    t.text = s
    return t


def bevel_face(svg, faceplate, ch, face, w, h):
    """Draw what a bevelled chassis shows on this face (#735).

    The drawing keeps the chassis's full size and every coordinate in it. A
    bevel along this view's line of sight cuts a corner off the silhouette, so
    the faceplate becomes the solid's outline - a <path> with the same id, which
    is all relief.js and the kit look it up by. A bevel on one of this face's own
    edges is a band of metal at 45 degrees beside the flat face: drawn as a strip
    a shade lighter, with the fold line where it meets the flat, in a group the
    kit can find (`chassis-bevels`). bevel.py builds the solid; the 3D viewer
    builds its mesh from the same polygons, so the two cannot disagree.
    """
    if not ch.get("bevel") or face not in _bevel.FACES:
        return
    bevels = _bevel.parse(ch)
    W, H, D = ch["width"], ch["height"], ch["depth"]
    if (w, h) != _bevel.draw_size(face, W, H, D):
        return       # L126 refuses a bevelled face drawn at another size
    el = _bevel.elevation(face, W, H, D, bevels)
    pts = lambda ps: " ".join(f"{x:.3f},{y:.3f}" for x, y in ps)
    if not _bevel.is_rectangle(el["outline"], w, h):
        faceplate.tag = f"{{{SVG_NS}}}path"
        for k in ("x", "y", "width", "height", "rx"):
            faceplate.attrib.pop(k, None)
        faceplate.set("d", "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in el["outline"]) + " Z")
    if not el["strips"]:
        return
    g = ET.SubElement(svg, f"{{{SVG_NS}}}g")
    g.set("id", "chassis-bevels")
    g.set("data-path", "chassis/bevels")
    for s in el["strips"]:
        strip = ET.SubElement(g, f"{{{SVG_NS}}}polygon")
        strip.set("data-edge", s["edge"])
        strip.set("points", pts(s["points"]))
        strip.set("fill", "#ffffff"); strip.set("fill-opacity", "0.08")
        strip.set("stroke", ch.get("edge", "#22262a")); strip.set("stroke-width", "0.25")


def render_view(device, view_name, view, lib, include=(), config_name="default", config=None,
                silkscreen=True):
    config = config or {}
    ch = device["chassis"]
    # A group carries the facts its members share - the media and speed of a
    # homogeneous port block, declared once instead of forty-eight times. Lint
    # already accepts that (L18), but this function never read groups: at all, so
    # a group-level declaration cleared the warning and changed nothing in the
    # drawing: 48 ports still compiled to data-media="sfp" while the manifest
    # said sfp28. A rule that accepts a fix the renderer ignores is worse than no
    # rule. Placement attrs win, so a specific port can still differ from its
    # block.
    dev_groups = device.get("groups") or {}
    vsize = view.get("size")
    w = vsize["w"] if vsize else ch["width"]
    h = vsize["h"] if vsize else ch["height"]
    svg = ET.Element(f"{{{SVG_NS}}}svg")
    svg.set("width", f"{w}mm")
    svg.set("height", f"{h}mm")
    svg.set("viewBox", f"0 0 {w} {h}")
    svg.set("data-device", device["name"])
    svg.set("data-view", view_name)
    # NO CONFIGURATION NAME ON THE FACE (#665). A drawing is written once and
    # shared by every configuration that draws it the same - the R740xd's 42
    # configurations draw 2 fronts - so a face cannot say which one it is.
    # `<device>.configs.json` `configs[].files` says which file each draws.
    # AN OPEN-FRAME FACE SAYS SO ON ITS ROOT, because what it changes is the
    # chassis and not any one bay: the kit lines the inside of the box when a
    # face declares it, so an empty slot looks into the chassis's interior
    # rather than through a box that has no inside.
    if view.get("open-frame"):
        svg.set("data-open-frame", "1")
    # Sections are a classification, not a namespace: a drawing is opened
    # somewhere else, and `data-power-max-w` is readable there while
    # `data-power-max-w` under some section prefix would only be longer. So the
    # bag is FLATTENED here and every key keeps the exact spelling it had before
    # sections existed - re-filing a key between sections must not change a
    # single byte of a compiled drawing. attrs.flatten is shared with the search
    # index and the exporters so they cannot disagree about what the bag holds.
    for ak, av in attrs_mod.flatten(device.get("attrs")).items():
        svg.set(f"data-{ak}", str(av))
    airflow = config_airflow(device, config)
    if airflow:
        svg.set("data-airflow", airflow)
    # WHAT THIS BUILD IS FED WITH, resolved as airflow is (config_power) and
    # space-separated where a build takes two feeds - `ac dc` - which is how an
    # SVG attribute spells a list and what `~=` in a CSS selector matches.
    power = config_power(device, config)
    if power:
        svg.set("data-power", " ".join(power))
    skin_overrides = config.get("skins") or {}
    attr_overrides = config.get("component-attrs") or {}

    style = ET.SubElement(svg, f"{{{SVG_NS}}}style")
    style.text = STATE_CSS

    meta = ET.SubElement(svg, f"{{{SVG_NS}}}metadata")

    faceplate = ET.SubElement(svg, f"{{{SVG_NS}}}rect")
    faceplate.set("id", "chassis-faceplate")
    faceplate.set("data-path", "chassis")
    faceplate.set("data-class", "chassis")
    faceplate.set("data-model", device.get("model", ""))
    pns = config.get("part-numbers") or {}
    base = next((m for m, v in pns.items() if (v or {}).get("power-cord") in (None, "", "none")), None)
    if base:
        faceplate.set("data-sku", base)
        faceplate.set("data-part-number", (pns[base] or {}).get("part", ""))
    faceplate.set("x", "0"); faceplate.set("y", "0")
    faceplate.set("width", f"{w:g}"); faceplate.set("height", f"{h:g}")
    faceplate.set("rx", "1.2")
    faceplate.set("fill", ch.get("color", "#3a3f45"))
    faceplate.set("stroke", ch.get("edge", "#22262a")); faceplate.set("stroke-width", "0.5")
    bevel_face(svg, faceplate, ch, view.get("face") or view_name, w, h)

    resolved = {}
    palette = {}
    inst_palette = {}
    parts = view_parts(view)

    # A CONFIGURATION CAN CHANGE THE SHEET METAL, not only what is fitted into it.
    # A C40G ordered for AC has one bolted panel across the bottom rear where a DC
    # chassis has two power-entry openings - so on an AC chassis those two bays do
    # not exist. Without this they rendered as two empty black rectangles and the
    # bay picker offered a DC power entry module on a chassis that cannot take one.
    #
    # Applied HERE, before anything else reads `parts`, so a scoped-out bay is
    # invisible to extents, to member boxes, to the silkscreen owner check and to
    # the tree alike - there is no second place that has to remember.
    _scoped_out = set()
    for _sect in ("bays", "placements"):
        _keep = []
        for q in parts[_sect]:
            if q.get("only-in") and config_name not in q["only-in"]:
                _scoped_out.add(q["id"])
            else:
                _keep.append(q)
        parts[_sect] = _keep

    # A LEGEND FOR AN OPENING THAT IS NOT THERE IS NOT PRINTED EITHER. Dropping it
    # is not a guess: the mark NAMES the bay it annotates, and that bay was scoped
    # out of this configuration by the author.
    #
    # Only when EVERY local owner is gone. A mark shared between two parts keeps
    # printing while either survives, and a mark that names nobody - a model name,
    # a warning, a column heading - is never touched by this.
    #
    # NOTHING IN THE LIBRARY NEEDS THIS TODAY, and it is worth saying why rather
    # than leaving it to look like dead weight. The C40G's "PEM 1"/"PEM 2" looked
    # like the case for it and are not: Figure 1-2 is the AC rear and prints both
    # labels in the same place, so they are a legend COLUMN on common sheet metal
    # and carry no `for:` at all - like the slot numbers 0-5 beside them, which
    # name six slots spanning the full width from one column. The rule stands
    # because the invariant is real and the alternative is a silently wrong render
    # the first time somebody scopes a bay whose label does name it; it is covered
    # by a synthetic fixture in spec/tests/test_config_scope.py.
    if _scoped_out:
        _kept_silk = []
        for m in parts["silkscreen"]:
            _own = [t for t in targets(m.get("for")) if not t.startswith("/")]
            if _own and set(_own) <= _scoped_out:
                continue
            _kept_silk.append(m)
        parts["silkscreen"] = _kept_silk

    # WHAT IS PLUGGED IN IS A CONFIGURATION, NOT A DIFFERENT DEVICE. A populated
    # port is the same cage with an optic in it, so `occupants:` sits beside
    # `bays:` and the switch can be drawn bare or fitted without either being a
    # separate model.
    #
    # Expanded into `mate-to` placements HERE, before anything reads `parts`, so
    # there is exactly one positioning path and exactly one interface check. The
    # occupant lands where its `mate` connection point meets the host's, and L12
    # holds the two to the same `interface` - none of which this code knows
    # about, because it is the same code that already runs for a hand-written
    # `mate-to`. A second path would be one bad afternoon from disagreeing with
    # the first about where an optic sits.
    #
    # Occupants for hosts in another view are skipped rather than an error: the
    # configuration describes the whole device, and a front-panel optic has no
    # business appearing in the rear drawing. Lint checks the host exists
    # SOMEWHERE (L12), which is the check that catches a typo.
    # AN OCCUPANT CAN ITSELF BE HOSTED, so this runs to a FIXED POINT rather
    # than over one snapshot. `here` used to be taken ONCE, before the loop
    # appended anything, so `occupants: {port-4: plug, port-4-occupant: boot}`
    # found no `port-4-occupant` in the snapshot and dropped the boot WITHOUT A
    # WORD - the worst outcome available, and the one shape spec B's two-part
    # fit is made of. Recomputing the id set each pass seats the second tier on
    # the first, the third on the second, and so on; a pass that seats nothing
    # ends it. What remains unseated after that is exactly what the paragraph
    # above says to skip - a host in another view - so it is still skipped, not
    # an error: the two cases are told apart by whether progress is possible,
    # not by when the set was sampled.
    remaining = dict(config.get("occupants") or {})
    # {id: chain} for the ids in `remaining` that are a default rather than a
    # configuration's key - `chain` being the refs already seated on that one
    # seat, which is what tells a loop from two slots shipping the same part
    shipped = {}
    # A PLACED SLOT SHIPS HOLDING ITS DEFAULT (B3, "The shipped default"): the
    # placed component's top-level `default:` (manifest.slot_default - a
    # device placement declares none of its own) seats unless this
    # configuration keys the placement, `""` included. Only a slot with its
    # own `at` in this drawing: not an occupant (P3), not a projection (a part
    # seen from another face), not an optional part this build leaves out. A
    # ref that does not resolve is left for draw_placement to report.
    for q in parts["placements"]:
        if (not q.get("id") or not q.get("at") or q.get("mate-to")
                or q.get("projection-of") or q["id"] in remaining
                or (q.get("optional") and q["optional"] not in include)):
            continue
        try:
            ships = slot_default(q, lib.resolve(q["ref"])[0])
        except (FileNotFoundError, ValueError, KeyError):
            continue
        if ships:
            remaining[q["id"]] = ships
            shipped[q["id"]] = ()
    # AND A PLACED SPANNING SLOT IS REFUSED WHILE ITS BORES HOLD SOMETHING (B3,
    # "The duplex host"), the same check `_seat_nested_occupants` makes for a
    # composed one. A device placement's bores are keyed under its own id
    # (`port-1510/1`) and seated by the instance drawn at that path, so this
    # loop never sees them; the configuration does, and so does the placed
    # contract's own `parts:`.
    _conn = _connector_registry()

    def _res_ref(ref):
        try:
            return lib.resolve(ref)[0]
        except (FileNotFoundError, ValueError, KeyError):
            return None
    for q in parts["placements"]:
        if not q.get("id") or q.get("mate-to") or q["id"] not in remaining:
            continue
        try:
            if occupant_spec(q["id"], remaining[q["id"]]) is None:
                continue
        except ValueError:
            continue                    # reported when it seats, below
        held = _res_ref(q.get("ref"))
        if held is not None:
            refuse_spanned_overlap(q["id"], q["ref"], held, _res_ref, _conn,
                                   config.get("occupants"))
    while remaining:
        seated_now = []
        chained, chains = {}, {}
        here = {q.get("id") for q in parts["placements"]}
        for host, spec in remaining.items():
            if host not in here:
                continue
            # A DEFAULT IS NO CONFIGURATION KEY, so it is not reported as one:
            # `occupants/<id>: names no component` would name a key nobody
            # wrote. The same `_label` reading the nested path uses.
            spec = occupant_spec(host, spec,
                                 label=f"{host}: default" if host in shipped else None)
            if spec is None:            # "" empties the slot (P4)
                seated_now.append(host)
                continue
            oid = occupant_local_id(host, spec)
            # AND WHAT THE OCCUPANT ITSELF SHIPS HOLDING (B3): a plug whose
            # contract defaults a boot onto its own rear slot brings the boot
            # with it here too, keyed by the produced id so a configuration
            # can still empty it. The guard is this seat's own CHAIN, so two
            # ports shipping the same plug each ship its boot.
            ships = (lib.resolve(spec["ref"])[0] or {}).get("default")
            chain = shipped.get(host, ()) + (spec["ref"],)
            if ships and ships in chain:
                raise ValueError(f"{host}: default {ships} is a cycle - "
                                 + " ships ".join(chain + (ships,)))
            if ships and oid not in remaining and oid not in here:
                chained[oid] = ships
                chains[oid] = chain
            parts["placements"].append({
                "ref": spec["ref"],
                "id": oid,
                "mate-to": host,
                # nests under the receptacle in the tree, the way an indicator nests
                # under what it indicates - an optic belongs to its port
                "for": host,
                "group": next((q.get("group") for q in parts["placements"]
                               if q.get("id") == host), None),
                **({"attrs": spec["attrs"]} if spec.get("attrs") else {}),
                **({"skin": spec["skin"]} if spec.get("skin") else {}),
            })
            seated_now.append(host)
        if not seated_now:
            # A CONFIGURED KEY WHOSE HOST IS IN ANOTHER VIEW IS SKIPPED (see
            # above) - a front-panel optic has no business in the rear drawing,
            # and L12 catches the typo. A DEFAULT IS NOT THAT CASE: its host is
            # a placement in THIS view by construction, so one left unseated is
            # a fault in this loop and must not vanish without a word.
            left = sorted(h for h in remaining if h in shipped)
            if left:
                raise ValueError(
                    ", ".join(f"{h}: default {remaining[h]!r}" for h in left)
                    + ": nothing seated it - its slot is in this drawing")
            break
        for host in seated_now:
            del remaining[host]
        remaining.update(chained)
        shipped.update(chains)

    # A SEATED PART SEEN FROM THIS FACE TOO. A bay on another view may say its
    # occupant's plan lands here (`plan:`), and the occupant's contract names
    # what draws it from above (`plan.ref`). Each becomes a placement in this
    # view - so `in:`, `under:` and the paint order all apply - marked as a
    # PROJECTION of the seated part: draw_placement swaps its data-path for
    # `data-of`, so it stays one part (this face's tree lists it only where
    # this face draws no part at that path - swap.js faceEntries) and the kit
    # builds nothing from it. The occupants of the occupant's own bays come
    # along at the offsets those bays declare, lowest slot first so the top
    # card paints last. A mirrored plan mirrors the offsets about the plan's own width.
    #
    # `rear:` IS THE SAME PROJECTION FROM THE OTHER END. A drawer whose back is
    # open shows the backs of the cassettes it holds; the occupant's contract
    # names what draws its back (`faces.rear`) and where its body stands
    # (`body.footprint`, which places it in the hole), and the bay says which
    # rear view and which panel `cutout` it is seen through. The
    # projection is drawn INSIDE that cutout, for the 2D rear. In 3D the cutout
    # is a passage the length of the chassis and the module's own body - its
    # back painted with this same face - stands in it at its real depth, so
    # nothing is built from the projection. No slots of slots: nothing seated
    # in a cassette has a back of its own to show.
    cfg_bays = config.get("bays") or {}
    for other_name, other in (device.get("views") or {}).items():
        if other_name == view_name:
            continue
        for b, direction in ((b, d) for b in view_parts(other)["bays"]
                             for d in ("plan", "rear")):
            pl = b.get(direction)
            if not pl or pl.get("view") != view_name:
                continue
            if b.get("only-in") and config_name not in b["only-in"]:
                continue
            occ = cfg_bays.get(b["id"], b.get("default"))
            if not occ:
                continue
            oc, _ = lib.resolve(occ)
            pref = face_ref(oc or {}, direction)
            if not pref:
                continue
            if direction == "rear":
                # WHOSE BACK THIS IS is said by the hole it is drawn in: the
                # cutout carries the seated module as `data-rear-ref` (below,
                # where the panel is drawn), and the projection is that hole's
                # direct child. The explorer finds the slots on a back (its MTP
                # bulkheads) through that module's `faces.rear` (B3, Task 10b).
                # WHERE IT LANDS is the seated module's, not the bay's: its
                # body's footprint, mirrored in the hole (faces.rear_at). HOW
                # IT IS TURNED is the bay's: a module seated on its side shows
                # its back on its side, the other way round (faces.rear_place).
                cut = next(c for c in ((view.get("panel") or {}).get("cutouts") or [])
                           if c.get("id") == pl["cutout"])
                pose = rear_place(b, cut, oc or {}, (lib.resolve(pref)[0] or {}).get("size") or {})
                parts["placements"].append({
                    "ref": pref, "id": f"{b['id']}-rear", "at": pose["at"],
                    **({"rotate": pose["rotate"]} if pose["rotate"] else {}),
                    "projection-of": f"{b['id']}/module",
                    "cutout": pl["cutout"]})
                continue
            pc, _ = lib.resolve(pref)
            pw = float((pc.get("size") or {}).get("w") or 0)
            mirror = bool(pl.get("mirror"))
            X, Y = pl["at"]
            common = {k: pl[k] for k in ("in", "under") if pl.get(k)}
            parts["placements"].append({
                "ref": pref, "id": f"{b['id']}-plan", "at": [X, Y], "mirror": mirror,
                "projection-of": f"{b['id']}/module", **common})
            for slot, sb in sorted(((oc or {}).get("bays") or {}).items(), reverse=True):
                sp = (sb or {}).get("plan")
                if not sp:
                    continue
                socc = cfg_bays.get(f"{b['id']}/{slot}", sb.get("default"))
                if not socc:
                    continue
                sc, _ = lib.resolve(socc)
                sref = face_ref(sc or {}, "plan")
                if not sref:
                    continue
                scc, _ = lib.resolve(sref)
                sw = float((scc.get("size") or {}).get("w") or 0)
                dx, dy = sp["at"]
                x = X + (pw - dx - sw) if mirror else X + dx
                parts["placements"].append({
                    "ref": sref, "id": f"{b['id']}-{slot}-plan", "at": [round(x, 4), round(Y + dy, 4)],
                    "mirror": mirror, "projection-of": f"{b['id']}/module/{slot}/module",
                    "under": [f"{b['id']}-plan"] + list(common.get("under") or []),
                    **({"in": common["in"]} if common.get("in") else {})})

    used_patterns = {d.get("pattern") for d in parts["decor"] if d.get("pattern")}
    if used_patterns:
        defs = ET.SubElement(svg, f"{{{SVG_NS}}}defs")
        if "vent" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "portrayal-vent"); pat.set("width", "8.86"); pat.set("height", "5.11")
            pat.set("patternUnits", "userSpaceOnUse")
            for cx, cy in ((0.0, 0.0), (8.86, 0.0), (4.43, 2.555), (0.0, 5.11), (8.86, 5.11)):
                hexpath = ET.SubElement(pat, f"{{{SVG_NS}}}path")
                pts = [(cx + 2.55, cy), (cx + 1.275, cy + 2.208), (cx - 1.275, cy + 2.208),
                       (cx - 2.55, cy), (cx - 1.275, cy - 2.208), (cx + 1.275, cy - 2.208)]
                hexpath.set("d", "M " + " L ".join(f"{x:g} {y:g}" for x, y in pts) + " Z")
                hexpath.set("fill", "#17191c")
        if "holes" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "portrayal-holes"); pat.set("width", "5"); pat.set("height", "5")
            pat.set("patternUnits", "userSpaceOnUse")
            c = ET.SubElement(pat, f"{{{SVG_NS}}}circle")
            c.set("cx", "2.5"); c.set("cy", "2.5"); c.set("r", "1.1"); c.set("fill", "#3c4046")
        if "grille" in used_patterns:
            # A fan exhaust grille, not perforation: coarse square openings on a
            # thin wire lattice. Roughly 4x the holes pattern, which is what a
            # real C100G fan tray looks like from the front.
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "portrayal-grille"); pat.set("width", "12"); pat.set("height", "12")
            pat.set("patternUnits", "userSpaceOnUse")
            op = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            op.set("x", "0.9"); op.set("y", "0.9")
            op.set("width", "10.2"); op.set("height", "10.2")
            op.set("rx", "1.2"); op.set("fill", "#15181b")
        if "slots-h" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "portrayal-slots-h"); pat.set("width", "14"); pat.set("height", "8")
            pat.set("patternUnits", "userSpaceOnUse")
            rct = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            rct.set("x", "2.5"); rct.set("y", "2.9"); rct.set("width", "9"); rct.set("height", "2.2")
            rct.set("rx", "1.1"); rct.set("fill", "#3c4046")
        if "slots" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "portrayal-slots"); pat.set("width", "8"); pat.set("height", "14")
            pat.set("patternUnits", "userSpaceOnUse")
            rct = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            rct.set("x", "2.9"); rct.set("y", "2.5"); rct.set("width", "2.2"); rct.set("height", "9")
            rct.set("rx", "1.1"); rct.set("fill", "#3c4046")
        if "ribs" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "portrayal-ribs"); pat.set("width", "7.2"); pat.set("height", "6")
            pat.set("patternUnits", "userSpaceOnUse")
            fin = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            fin.set("x", "0"); fin.set("y", "0"); fin.set("width", "4.8"); fin.set("height", "6")
            fin.set("fill", "#e8eaed")
            gap = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            gap.set("x", "5.4"); gap.set("y", "0"); gap.set("width", "1.8"); gap.set("height", "6")
            gap.set("fill", "#6a7075")
    # DECOR USED TO LAND AS LOOSE, UNNAMED RECTS ON THE ROOT. Opening a
    # faceplate in an XML editor showed twenty anonymous rectangles above
    # everything that IS named, and the only way to find out whether one was a
    # port shell, a recess plate or a hole in the sheet metal was to click it
    # and watch what highlighted. The geometry was right and the file could not
    # be read.
    #
    # They are now one group in DOCUMENT ORDER - not sorted by kind, because
    # paint order is meaning here: several of these deliberately overlap, and
    # hoisting every vent into its own group would change which one covers
    # which. Each carries what it IS.
    #
    # `vent-field` is the one that says something the geometry cannot: it is not
    # a grey texture, it is PERFORATION - holes going through the sheet that air
    # passes down. Airflow direction is deliberately not recorded: a chassis is
    # ordered front-to-back or back-to-front as a build option, so the same hole
    # is an intake on one SKU and an exhaust on another, and only the
    # configuration knows which.
    deco_g = ET.SubElement(svg, f"{{{SVG_NS}}}g")
    deco_g.set("id", "--decor")
    deco_g.set("data-class", "decor")
    seen_kinds = {}
    for d in parts["decor"]:
        # PAINT FOLLOWS THE HARDWARE IT SITS BEHIND. Decor could draw a
        # rectangle and a rounded rectangle and nothing else, so a patch printed
        # around a D-subminiature connector - which is what Dell puts behind the
        # serial and VGA ports on this generation - had no shape to be. Same
        # four values the cutouts take, drawn by the same two helpers, so the
        # vocabulary means one thing in both places.
        shape = d.get("shape")
        as_path = shape in ("d-sub", "slot", "octagon")
        r = ET.SubElement(deco_g, f"{{{SVG_NS}}}{'path' if as_path else 'rect'}")
        if d.get("pattern") == "vent" or d.get("vent"):
            kind = "vent-field"
        elif d.get("stroke"):
            kind = "outline"
        elif d.get("pattern"):
            kind = f"{d['pattern']}-field"
        else:
            kind = d.get("kind") or "plate"
        n = seen_kinds[kind] = seen_kinds.get(kind, -1) + 1
        r.set("id", d.get("id") or f"{kind}-{n}")
        r.set("data-kind", kind)
        if kind == "vent-field":
            # a hole, not a texture - stated for anything reading the drawing
            # rather than looking at it
            r.set("data-aperture", "air")
        if as_path:
            dx, dy = d["at"]; dw, dh = d["size"]
            r.set("d", _dsub_path(dx, dy, dw, dh) if shape == "d-sub"
                  else _octagon_path(dx, dy, dw, dh) if shape == "octagon"
                  else _slot_path(dx, dy, dw, dh))
        else:
            r.set("x", f"{d['at'][0]:g}"); r.set("y", f"{d['at'][1]:g}")
            r.set("width", f"{d['size'][0]:g}"); r.set("height", f"{d['size'][1]:g}")
            r.set("rx", f"{d.get('rx', 0.6):g}")
        if d.get("stroke"):
            r.set("fill", "none")
            r.set("stroke", d["stroke"]); r.set("stroke-width", f"{d.get('stroke-width', 1):g}")
        else:
            # A PATTERN IS A TILE, AND EVERY FACE USED TO GET ONE VENDOR'S TILE.
            # `slots-h` is 14 x 8 because that is the louvre pitch of the first
            # hardware it was drawn for, so a bezel whose louvres run eight rows
            # deep in the same height could only be drawn with three, and the
            # most recognisable texture on the face came out as somebody else's
            # grille. `pattern-pitch` states this rect's tile size in mm; the
            # scale is derived from the tile's own width and height rather than
            # a second copy of them, because two names for one number is this
            # library's most repeated defect.
            #
            # Both modifiers reach the tile the same way - a patternTransform on
            # a clone - so a rect can shift the lattice's phase, change its
            # pitch, or do both. TRANSLATE BEFORE SCALE: that lands the scaled
            # tile's own origin on the offset, which is what "align the lattice
            # to this rect" has to mean once the tile is no longer 14 x 8.
            if d.get("pattern") and (d.get("pattern-offset") or d.get("pattern-pitch")):
                base = svg.find(f".//*[@id='portrayal-{d['pattern']}']")
                ox, oy = d.get("pattern-offset") or (0.0, 0.0)
                pw, ph = d.get("pattern-pitch") or (float(base.get("width")),
                                                    float(base.get("height")))
                sx, sy = pw / float(base.get("width")), ph / float(base.get("height"))
                pid = (f"portrayal-{d['pattern']}-o{ox:g}-{oy:g}-s{sx:.6g}-{sy:.6g}"
                       .replace(".", "_"))
                if svg.find(f".//*[@id='{pid}']") is None:
                    clone = ET.fromstring(ET.tostring(base))
                    clone.set("id", pid)
                    clone.set("patternTransform",
                              f"translate({ox:g} {oy:g}) scale({sx:.6g} {sy:.6g})")
                    svg.find(f".//{{{SVG_NS}}}defs").append(clone)
                r.set("fill", f"url(#{pid})")
            else:
                r.set("fill", f"url(#portrayal-{d['pattern']})" if d.get("pattern") else d.get("fill", "#2e3236"))
        if d.get("vent"):
            r.set("data-vent", f"{d['vent']:g}")
        if d.get("out"):
            r.set("data-z-out", f"{d['out']:g}")
        # relief.js sums data-z-lift up the ancestor chain, so a decor rect that
        # carries one spans lift..out rather than 0..out
        if d.get("lift"):
            r.set("data-z-lift", f"{d['lift']:g}")
        if d.get("sink"):
            r.set("data-groove", f"{d['sink']:g}")

    # A REGION WITH NO EXTENT USED TO RENDER AS A 0x0 RECT AT THE ORIGIN, which is
    # a click target that can never highlight anything: selecting it in the tree
    # appeared to work and did nothing. 105 of the library's 137 regions state
    # neither `at`/`size` nor `members`, so that was the common case, not the edge.
    #
    # Order of preference: the stated box, else the union of what `members` names,
    # else NOTHING - and "nothing" is declared rather than faked, so a viewer can
    # say "no extent recorded" instead of offering a target that does not exist.
    def member_box(mid):
        for src in ("cutouts", "bays", "placements"):
            for q in parts[src]:
                if q.get("id") != mid or not q.get("at"):
                    continue
                if q.get("size") is not None:
                    w, h = bay_size(q)
                else:
                    # a placement carries no size of its own; its extent is the
                    # component's, which only the contract knows
                    try:
                        w = h = 0
                        if q.get("ref"):
                            c, _ = lib.resolve(q["ref"])
                            w, h = c["size"]["w"], c["size"]["h"]
                    except Exception:
                        w = h = 0
                return q["at"][0], q["at"][1], w, h
        return None

    def region_extent(region):
        at, size = region.get("at"), region.get("size")
        if at and size:
            return at[0], at[1], size["w"], size["h"]
        boxes = [b for b in (member_box(m) for m in region.get("members") or []) if b]
        if not boxes:
            return None
        x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
        return x0, y0, x1 - x0, y1 - y0

    # regions first (under components)
    for region in parts["regions"]:
        r = ET.SubElement(svg, f"{{{SVG_NS}}}rect")
        r.set("id", f"region--{region['id']}")
        r.set("data-path", f"region:{region['id']}")
        r.set("data-class", "region")
        pc = (config.get("region-context") or {}).get(region["id"], region.get("physical-context"))
        if pc:
            r.set("data-physical-context", pc)
        if region.get("members"):
            r.set("data-members", " ".join(region["members"]))
        box = region_extent(region)
        # rx, ry, rw, rh - NOT w and h. Unpacking into w,h here shadowed the
        # VIEW's width and height for the rest of the function, so the viewBox
        # was computed from the last region's box: the C100G rear came out
        # 420.8 x 471.5 against a 432.95 x 571.0 panel, clipping a card off the
        # right edge and putting both PEMs outside the drawing entirely.
        rx_, ry_, rw, rh = box or (0, 0, 0, 0)
        r.set("x", f"{rx_:g}"); r.set("y", f"{ry_:g}")
        r.set("width", f"{rw:g}"); r.set("height", f"{rh:g}")
        r.set("rx", "0.8")
        # regions are addressable, not visible; highlight CSS gives them a stroke on demand
        r.set("fill", "none")
        r.set("stroke", "none")
        if box and rw > 0 and rh > 0:
            r.set("pointer-events", "all")
        else:
            # not a click target, and it says why rather than looking like one
            r.set("data-extent", "none")
            r.set("pointer-events", "none")
        if box and not (region.get("at") and region.get("size")):
            r.set("data-extent", "derived")

    # CUTOUTS. The panel is punched before anything is printed on it or put into
    # it, so the holes paint first. A hole with nothing in it shows the dark inside
    # of the chassis, which is exactly what the drawing shows too; a placed component
    # covers its hole. Addressable, like regions, so a viewer can list them.
    if parts["cutouts"]:
        cut_g = ET.SubElement(svg, f"{{{SVG_NS}}}g")
        cut_g.set("id", "--cutouts")
        cut_g.set("data-class", "cutouts")
        for c in parts["cutouts"]:
            x, y = c["at"]; cw_, ch_ = c["size"]
            shape = c.get("shape")
            if shape == "circle":
                e = ET.SubElement(cut_g, f"{{{SVG_NS}}}ellipse")
                e.set("cx", f"{x + cw_ / 2:g}"); e.set("cy", f"{y + ch_ / 2:g}")
                e.set("rx", f"{cw_ / 2:g}"); e.set("ry", f"{ch_ / 2:g}")
            elif shape in ("d-sub", "slot", "octagon"):
                # THE SCHEMA OFFERED FOUR SHAPES AND THIS DREW TWO. `d-sub` and
                # `slot` fell through to the rect branch and were punched as
                # rectangles - so a D-subminiature aperture rendered as a black
                # box with the connector's D sitting inside it, and the corners
                # the hole does not have showed as ink. An enum whose values are
                # accepted and then silently ignored is worse than a smaller
                # enum, because the model says the right thing and the drawing
                # does not. Nothing in the library used either value, so this
                # changes no existing render.
                e = ET.SubElement(cut_g, f"{{{SVG_NS}}}path")
                # A D HAS A DIRECTION AND SO DOES THE PART IN IT. The connector
                # beside this hole says which way it faces with `rotate`; the
                # hole says it in the same word and about its own centre, so the
                # two cannot drift.
                # `size` IS THE FOOTPRINT, NOT THE UNROTATED SHAPE, which is the
                # trap here: a quarter turn swaps the box, so building the path
                # at the declared size and then turning it counts the rotation
                # twice and the aperture bulges past the connector on both
                # flanks. The path is built in the unturned frame, on the same
                # centre, and the transform does the rest.
                rot = c.get("rotate") or 0
                cx_, cy_ = x + cw_ / 2, y + ch_ / 2
                pw, ph = (ch_, cw_) if rot % 180 == 90 else (cw_, ch_)
                px_, py_ = cx_ - pw / 2, cy_ - ph / 2
                e.set("d", _dsub_path(px_, py_, pw, ph) if shape == "d-sub"
                      else _octagon_path(px_, py_, pw, ph) if shape == "octagon"
                      else _slot_path(px_, py_, pw, ph))
                if rot:
                    e.set("transform", f"rotate({rot:g} {cx_:g} {cy_:g})")
            else:
                e = ET.SubElement(cut_g, f"{{{SVG_NS}}}rect")
                e.set("x", f"{x:g}"); e.set("y", f"{y:g}")
                e.set("width", f"{cw_:g}"); e.set("height", f"{ch_:g}")
                if c.get("rx") is not None:
                    e.set("rx", f"{c['rx']:g}")
            e.set("fill", "#101214")
            if c.get("depth"):
                # A HOLE WITH A BACK TO IT. The kit builds a `data-depth` group
                # as a recess and lays the group's own art on its floor, so the
                # rect becomes the group's `hole` - the mouth the face texture
                # punches - and anything later drawn INTO the group (a rear
                # projection) is what the recess shows at its far end.
                hole = e
                cut_g.remove(hole)
                e = ET.SubElement(cut_g, f"{{{SVG_NS}}}g")
                e.set("data-depth", f"{float(c['depth']):g}")
                e.set("data-cavity", "hole")
                # WHAT THE KIT NEEDS TO RE-SEAT IT. A runtime swap changes the
                # front bay and nothing else, so a hole a bay is seen through
                # says which bay and where its projection goes - what a swap
                # needs to redraw the back it shows in 2D.
                rear_bay = next((b for ov in (device.get("views") or {}).values()
                                 for b in view_parts(ov)["bays"]
                                 if (b.get("rear") or {}).get("view") == view_name
                                 and b["rear"].get("cutout") == c["id"]), None)
                if rear_bay:
                    e.set("data-rear-of", rear_bay["id"])
                    # WHERE A BACK GOES DEPENDS ON WHOSE BACK IT IS. The hole
                    # carries the bay as seen from behind - its own origin,
                    # the bay's size - and `data-rear-at`, where the SEATED
                    # module's back was drawn in it (faces.rear_at). A swap
                    # reads the first and rewrites the second. A TURNED bay
                    # also says how far a back in it is turned
                    # (`data-rear-rotate`, faces.rear_turn), occupied or not,
                    # since a swap into an empty hole needs it too; `at` is
                    # then the back's unturned top-left, as a placement's is.
                    e.set("data-rear-bay", f"{x:g},{y:g},{float(rear_bay['size']['w']):g},"
                                           f"{float(rear_bay['size']['h']):g}")
                    if rear_turn(rear_bay):
                        e.set("data-rear-rotate", f"{rear_turn(rear_bay):g}")
                    # A HOLE A SLOT IS SEEN THROUGH IS THAT SLOT, FROM BEHIND.
                    # The tree rows it as the bay, in the bay's group and order,
                    # named for what sits in it; the path stays cutout:<id>.
                    occ = (config.get("bays") or {}).get(rear_bay["id"], rear_bay.get("default"))
                    if occ:
                        e.set("data-rear-ref", occ)
                        occ_c = lib.resolve(occ)[0] or {}
                        back_c = lib.resolve(face_ref(occ_c, "rear"))[0] if face_ref(occ_c, "rear") else None
                        rx_, ry_ = rear_place(rear_bay, c, occ_c, (back_c or {}).get("size") or {})["at"]
                        e.set("data-rear-at", f"{rx_:g},{ry_:g}")
                    grp_name = rear_bay.get("group")
                    if grp_name:
                        # ONLY data-group AND data-group-role COME ACROSS. The
                        # rest of group_side_attrs (a group's own attrs, its
                        # description) belongs to the thing drawn IN the bay,
                        # not the hole it is seen through - a `data-media`
                        # here would make the explorer read the cutout itself
                        # as a port.
                        side = group_side_attrs(grp_name, dev_groups.get(grp_name))
                        for k in ("data-group", "data-group-role"):
                            if k in side:
                                e.set(k, side[k])
                    if rear_bay.get("rel-pos") is not None:
                        e.set("data-rel-pos", f"{rear_bay['rel-pos']}")
                e.set("data-wall", c.get("wall") or "#2a2d31")
                hole.set("id", f"cutout--{c['id']}--hole")
                e.append(hole)
            e.set("id", f"cutout--{c['id']}")
            e.set("data-path", f"cutout:{c['id']}")
            e.set("data-class", "cutout")

    # SILKSCREEN. On the real part the panel is punched, the silkscreen is printed
    # onto it, and only then are the modules installed - so chassis silkscreen paints
    # HERE, after the panel and before any component. A legend a module would cover is
    # invisible in the drawing because it is invisible on the hardware, which makes a
    # mispositioned legend show up as missing rather than as a lie. Silkscreen printed
    # on a module's own faceplate lives in that component's skin and travels with it.
    silk_items = parts["silkscreen"] if silkscreen else []
    if silk_items:
        silk_g = ET.SubElement(svg, f"{{{SVG_NS}}}g")
        silk_g.set("id", "--silkscreen")
        silk_g.set("data-class", "silkscreen")
        silk_default = ch.get("silk", "#c7ccd1")
        for i_m, m in enumerate(silk_items):
            x, y = m["at"]
            if m.get("path"):
                # a printed line or symbol - a leader, an arrow, an earth mark
                #
                # A LEADER IS A LINE AND A TRIANGLE IS A SHAPE, and until now
                # both were stroked with `fill: none`. That makes every solid
                # symbol in this library an OUTLINE held shut by a fat stroke:
                # a 1.2mm arrowhead under a 0.6mm stroke leaves a pinhole in
                # the middle that only shows when somebody zooms in, and it
                # cannot be scaled, because the stroke does not grow with the
                # shape - at twice the size the hole is four times as obvious.
                # `filled: true` says this path encloses ink rather than
                # tracing a route.
                t = ET.Element(f"{{{SVG_NS}}}path")
                t.set("d", m["path"])
                if m.get("filled"):
                    t.set("fill", m.get("fill") or silk_default)
                    t.set("stroke", "none")
                    if m.get("fill-rule"):
                        t.set("fill-rule", m["fill-rule"])
                else:
                    t.set("fill", "none")
                    t.set("stroke", m.get("fill") or silk_default)
                    t.set("stroke-width", f"{m.get('stroke-width', 0.6):g}")
                    t.set("stroke-linecap", "round")
                t.set("stroke-linejoin", "round")
                if x or y:
                    t.set("transform", f"translate({x:g} {y:g})")
            else:
                fs = m.get("font-size", 2.2)
                lines = str(m["text"]).split("\n")
                if len(lines) == 1:
                    t = text_el(x, y, lines[0], size=fs, anchor=m.get("anchor", "middle"),
                                fill=m.get("fill") or silk_default)
                else:
                    # multi-line legend: one <text> holding tspans, so it stays one mark
                    t = text_el(x, y, "", size=fs, anchor=m.get("anchor", "middle"),
                                fill=m.get("fill") or silk_default)
                    t.text = None
                    for i_, line in enumerate(lines):
                        ts = ET.SubElement(t, f"{{{SVG_NS}}}tspan")
                        ts.set("x", f"{x:g}"); ts.set("y", f"{y + i_ * fs * 1.15:g}")
                        ts.text = line
                if m.get("rotate"):
                    t.set("transform", f"rotate({m['rotate']:g} {x:g} {y:g})")
            if m.get("id"):
                t.set("id", m["id"])
            # SILKSCREEN IS A LAYER THE TREE COULD NOT SEE. The marks carried an
            # optional id and a `for`, and nothing else - no data-path, so the
            # tree, which builds from data-path, had no row for a single one of
            # the library's 994 printed marks. A legend that is missing, or that
            # sits where a module will cover it, was invisible in exactly the
            # place built to make such things visible.
            #
            # Not one mark in the library declares an id, so the path is
            # positional and namespaced the way `region:` and `cutout:` already
            # are. Positional identity is weaker than a declared one - reordering
            # a view's silkscreen list renumbers these - which is an argument for
            # letting marks carry ids, not for leaving them out of the tree.
            t.set("data-path", f"silk:{m.get('id') or i_m}")
            t.set("data-class", "silkscreen")
            # A mark naming an owner nests under it through the existing `for`
            # rule. One naming nobody has nowhere to be, so it folds into a
            # single chassis-level heading rather than adding a row to the root:
            # on the AS5912-54X that is 58 rows, none of which claim an owner.
            t.set("data-group", "silkscreen")
            t.set("data-group-role", "marking")
            # bind the mark to what it annotates, so a viewer can select both at once.
            # A leader line names both ends.
            df = data_for(m.get("for"))
            if df:
                t.set("data-for", df)
            silk_g.append(t)

    extents = [0.0, 0.0, w, h]
    # HOW DEEP A WELL'S FLOOR IS, for whatever says it is `in:` one - see
    # well_floor. Defined ahead of the mate-to resolution below, which reads
    # it: a host standing in a well hands its sink to what seats on it.
    def floor_of(wid):
        return well_floor(parts["placements"], lib, wid)

    # resolve mate-to before drawing: an occupant is positioned so its `mate`
    # connection-point lands on its host's, which is what keeps centring offsets
    # out of device manifests entirely
    #
    # A SEATED PLACEMENT CAN ITSELF HOST. `hosts` used to be built once, from
    # placements carrying an explicit `at`, so an occupant could never host
    # another and a boot could not sit on a seated plug - which is the whole of
    # spec B's two-part fit. Composition is not an alternative: `parts:` entries
    # have no `optional` and are compile-time flattened, so a composed boot could
    # not be chosen per connector, which is what the spec asks for.
    #
    # Resolution now runs to a FIXED POINT: each pass places the occupants whose
    # hosts are known and adds them to `hosts`, until a pass places nothing. A
    # pass that places nothing while occupants remain is either a dangling
    # `mate-to` (the existing error, unchanged) or a cycle (a new one) - and
    # without the cycle check the loop would not terminate.
    #
    # `mate_resolved` is deliberately NOT named `resolved` - `resolved` is
    # already the component-version bag started below (search this function for
    # `resolved = {}`) and threaded through every `instance_group` call to build
    # `resolved-components` metadata. Reusing the name here would shadow it.
    hosts = {q["id"]: q for q in parts["placements"] if q.get("at")}
    pending = [q for q in parts["placements"] if q.get("mate-to") and not q.get("at")]
    mate_resolved = {}

    def _res(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None

    while pending:
        progressed = []
        for p in pending:
            host = hosts.get(p["mate-to"])
            if host is None:
                progressed.append(p)
                continue
            # THE ONE SEATING RULE (solve_seat): the mate points, the turn,
            # the mirror / rotate / in: refusals and the lift, shared with a
            # seat on a card (_seat_nested_occupants).
            at, orot, total_lift = solve_seat(
                lib, p["id"], p["ref"], p["mate-to"], host,
                occ_rotate=p.get("rotate"), occ_in=p.get("in"), floor_of=floor_of)
            # AN OCCUPANT INHERITS ITS HOST'S TILT. `solve_seat` (through
            # `presented_interface`) knows nothing of facets, so `at` lands
            # on the host's FLAT aperture point. Two sources for a tilt:
            # the host's own contract forwards its mate point from a
            # composed part that sits `on` a facet (`card` wrapping a
            # tilted cage), or the host is ITSELF a seat that already
            # carries one (a boot on a tilted optic). Either way, find the
            # TARGET device point the aperture is actually drawn at
            # (`_tilt_offset`), then solve the occupant's own `at` from it.
            hc = _res(host["ref"])
            tilt_facet = tilt_node = target = None
            if hc:
                fpart = forwarded_part(hc, _res)
                tilt_facet, part_at, tilt_node = _facet_via_part(hc, fpart, p["mate-to"])
                if tilt_facet:
                    # THE APERTURE'S EXACT DRAWN POSITION - p1's own local
                    # mate point, through p1's own `_tilt_offset` (rotate,
                    # then the facet's scale), landed in card's frame, then
                    # carried out by card's own (untilted) placement.
                    core = _res(fpart["ref"])
                    core_mate = presented_point(core)
                    ox, oy = _tilt_offset(core_mate["at"], core["size"],
                                          fpart.get("rotate"), tilt_facet)
                    target = seat_point(host["at"], hc["size"], host.get("rotate"),
                                        (part_at[0] + ox, part_at[1] + oy))
            if not tilt_facet and host.get("tilt") and hc:
                # CHAINED: the host is itself a tilted seat. Its own mate
                # point (`presented_interface`, in its own local frame) is
                # drawn exactly as `part_at`+`_tilt_offset` above, except
                # the host has no further OUTER placement to carry through -
                # a seated occupant's group is a top-level sibling, so
                # `host["at"]` is already device-frame.
                tilt_facet, tilt_node = host["tilt"], host.get("tilt-on")
                _, host_pt, _ = presented_interface(hc, _res)
                if host_pt is not None:
                    # HOST ITSELF WAS DRAWN AXIS-SWAPPED, if it carries its
                    # own rotate 90/270 - it is a seated occupant too, with
                    # the same no-container situation `_drawn_facet` exists
                    # for, so its actual aperture position needs the same
                    # swap this code applied when HOST was resolved.
                    ox, oy = _tilt_offset(host_pt, hc["size"], host.get("rotate"),
                                          _drawn_facet(tilt_facet, host.get("rotate")))
                    target = (host["at"][0] + ox, host["at"][1] + oy)
            # THE OCCUPANT'S OWN SHAPE SWAPS AXIS AT 90/270 too (`_drawn_
            # facet`) - same reasoning, its own transform string.
            drawn_facet = _drawn_facet(tilt_facet, orot) if tilt_facet else None
            if tilt_facet and target is not None:
                # SOLVE THE OCCUPANT'S OWN `at` from the target its `mate`
                # must land on, inverting the SAME `_tilt_offset` the
                # occupant is itself drawn with (it inherits `tilt`, so its
                # own group carries the same scale).
                oc = _res(p["ref"])
                om = (oc.get("connection-points") or {}).get("mate") if oc else None
                if om:
                    ox, oy = _tilt_offset(om["at"], oc["size"], orot, drawn_facet)
                    at = [round(target[0] - ox, 4), round(target[1] - oy, 4)]
            seated = dict(p, at=at)
            if tilt_facet:
                seated["tilt"] = tilt_facet
                seated["tilt-on"] = tilt_node
            # `orot` is the occupant's turn - the host's own plus a spanning
            # host's axis (solve_seat) - omitted when that is none, so an
            # unrotated seat's output does not change. A chained seat (a boot on a plug in a rotated
            # cage) inherits it: `hosts` holds this dict.
            if orot:
                seated["rotate"] = orot
            # WHAT SEATS RECORDS ITS HOST, HOWEVER IT WAS AUTHORED. `occupants:`
            # writes `for: host` when it expands (see above); a HAND-WRITTEN
            # `mate-to` - which the spec offers in the same breath as
            # `occupants:` - wrote nothing, so its group carried no `data-for`
            # and cablePoints' seat-chain grouping never fired for it: a plug
            # and the boot on it came back as TWO points for ONE connector.
            # The host is not a guess here, it is the `mate-to` target, so the
            # default costs nothing and closes the gap. An author's own `for:`
            # still wins - it may name something else entirely (a port an LED
            # belongs to), and this is a default, not an override.
            if not seated.get("for"):
                seated["for"] = p["mate-to"]
            # Carried to draw_placement as `host-lift` - a resolution-time fact,
            # not the `seat_lift` local that trio (z_inset / z_group_lift /
            # data-z-lift) already applies there. Named `host-lift`, not
            # `seat-lift`, to keep it visibly distinct from that local.
            # The sum and the well sink are solve_seat's; see there.
            if total_lift:
                seated["host-lift"] = total_lift
            mate_resolved[p["id"]] = seated
            hosts[p["id"]] = seated
        if len(progressed) == len(pending):
            ids_in_view = {q["id"] for q in parts["placements"]}
            missing = [p for p in progressed if p["mate-to"] not in ids_in_view]
            if missing:
                bad = missing[0]
                raise ValueError(
                    f"{bad['id']}: mate-to {bad['mate-to']!r} is not a placement "
                    "with an explicit position in this view")
            raise ValueError(
                "mate-to cycle among placements: "
                + ", ".join(sorted(p["id"] for p in progressed)))
        pending = progressed

    # WHAT IS BOLTED TO THE OUTSIDE OF THE METAL PAINTS LAST. A bay draws its
    # opening - and an empty bay draws it dark - so anything mounted across that
    # opening has to come after it or the hole paints over the thing covering it.
    # The C40G is the case that found this: a louvred filter cover snaps over all
    # four PSU bays, and with the bays empty the renderer put four dark rectangles
    # on top of the cover that is physically in front of them.
    #
    # `mounts` is exactly the right predicate and it is already on every part -
    # a rack ear, a label, a ground lug, a bolted panel. It is NOT a paint-order
    # field invented for this bug; the ordering falls out of what the word means.
    # Across the library only this one cover overlaps a bay at all, so nothing
    # else moves a pixel.
    def _mounts(q):
        # a bad ref is NOT swallowed here - it is left for draw_placement, which
        # resolves the same ref a few lines down and raises there with the part
        # in hand. Failing in this ordering pass would report the same problem
        # from a place that cannot say which placement it was drawing.
        try:
            c, _ = lib.resolve(q["ref"])
        except Exception:
            return False
        return (c or {}).get("behaviour") == "mounts"

    deferred_ids = {q["id"] for q in parts["placements"] if _mounts(q)}
    # an occupant follows its host over the line, so a part mated onto a cover
    # does not end up painted underneath it
    for _ in range(len(parts["placements"])):
        grew = {q["id"] for q in parts["placements"]
                if q.get("mate-to") in deferred_ids}
        if grew <= deferred_ids:
            break
        deferred_ids |= grew

    # A MOUNTED PART THAT IS UNDER AN OPENING IS NOT IN FRONT OF IT. The second
    # pass exists so a surface-mounted part paints over the bays behind it - a
    # rear handle across two riser slots. The R740xd's heatsinks are `mounts`
    # too, because they lift off, but they say `under:` the mid-drive tray and
    # its four bays: with the tray fitted, the drives lie over them, and the
    # second pass painted heatsinks on top of drives. A part declared under
    # something that is NOT itself deferred - a well, or a bay - is drawn in
    # the first pass, in `under:` order, with the wells it stands among.
    every_bay = {b["id"] for b in parts["bays"]}
    # AND A WELL THAT THINGS STAND IN IS NOT A LID EITHER, whatever its
    # behaviour says. The mid tray is `mounts` because it lifts out, and it is
    # a recess with four drive bays `in:` it; the bays have to paint after it.
    wells_in_use = {q["in"] for q in (*parts["placements"], *parts["bays"]) if q.get("in")}
    for q in parts["placements"]:
        overs = q.get("under") or []
        overs = overs if isinstance(overs, list) else [overs]
        if q["id"] in deferred_ids and (q["id"] in wells_in_use or
                                        any(o in every_bay or o not in deferred_ids for o in overs)):
            deferred_ids.discard(q["id"])

    # HOW TALL THE THING IN A BAY IS, so it can stand on the floor rather than
    # hang from the plane: the deepest acceptable occupant, exactly as the
    # bay's own data-depth is taken.
    def occupant_depth(b):
        ds = []
        for ref in (b.get("accepts") or []):
            try:
                c, _ = lib.resolve(ref)
            except Exception:
                continue
            d = ((c or {}).get("size") or {}).get("d")
            if d:
                ds.append(float(d))
        return max(ds) if ds else 0.0

    def sink(g, floor):
        if not floor:
            return
        g.set("data-z-lift", f"{-floor:g}")
        for node in g.iter():
            if node.get("data-z-out") is not None:
                node.set("data-z-out", f"{float(node.get('data-z-out')) - floor:g}")

    def back_occupants(p):
        """The keys a module's back seats (B3, Task 7i): those whose host is
        on the back (manifest.back_hosts), at any depth. The module's front
        keys are left to the front drawing, where they are checked."""
        prefix = slot_key_prefix(p["projection-of"])
        back = {q["id"] for q in lib.resolve(p["ref"])[0].get("parts") or []
                if q.get("id")}
        on_back = back_hosts(prefix, nested_occupants, back)
        return {k: v for k, v in nested_occupants.items()
                if not k.startswith(prefix + "/")
                or k[len(prefix) + 1:].split("/")[0] in on_back}

    def draw_placement(p):
        # How far off the face the SEAT is - the aperture's own protrusion,
        # nothing the author wrote. Kept separate from `p["lift"]` on purpose;
        # see the trio below.
        seat_lift = 0.0
        if p.get("mate-to") and not p.get("at"):
            # Resolved to a fixed point before any placement was drawn (see
            # `mate_resolved` above `hosts`), which is what lets a seated
            # placement itself host - a boot can now mate to an occupant, not
            # only to something with an explicit `at`. The lookup is guarded,
            # not a bare subscript: a `mate-to` somehow absent from
            # `mate_resolved` must raise the SAME error a dangling `mate-to`
            # always has, not a KeyError with a stack trace. In practice the
            # resolution pass above already raises this for every dangling or
            # cyclic case before drawing starts, so this is a defensive echo of
            # that error, not its only source.
            resolved_p = mate_resolved.get(p["id"])
            if resolved_p is None:
                raise ValueError(f"{p['id']}: mate-to {p['mate-to']!r} is not a "
                                 "placement with an explicit position in this view")
            p = resolved_p
            # WHAT THE APERTURE IS OFF THE FACE, THE OCCUPANT IS TOO, and
            # carrying it takes THREE coordinated moves, not one. `parts:`
            # composition already does the same three (see the `part.get("lift")`
            # call in instance_group): the child's absolute figures come up by
            # the lift (`z_inset -= lift`), the bookkeeping that folds a group
            # lift into them is told about it (`z_group_lift += lift`), and the
            # group itself declares the lift (`data-z-lift`), which is the only
            # one of the three relief.js can see. Doing the first alone - which
            # is all this did - moved nothing: the occupant's group carried no
            # data-z-lift, so liftOf returned 0 for it and a plug seated in a
            # 10 mm-proud bore drew buried in the transceiver body. Doing the
            # third without the second double-counts, because relief.js SUMS
            # data-z-lift up the ancestor chain while reading data-z-out as an
            # absolute distance - the dcp-f-a22 white-spikes defect. The three
            # balance; the other two are below.
            #
            # SCOPED TO THE SEAT. An author's `lift:` on an ordinary placement
            # keeps exactly the meaning _inset_feature's docstring gives it -
            # carried entirely by `back`, writing no attribute - so it stays in
            # `p["lift"]` and out of `seat_lift`.
            seat_lift = float(p.get("host-lift") or 0.0)
        if p.get("optional") and p["optional"] not in include:
            return
        grp = dev_groups.get(p.get("group")) or {}
        # The group's attrs still go into instance_group's `attrs`, under the
        # placement's own: text filled from attrs and the contract-attr
        # precedence both read that merged bag. What the GROUP WRITES on this
        # placement is group_side_attrs, below, and only that.
        merged_attrs = group_merged_attrs(grp, p.get("attrs"))
        rear_face = bool(p.get("projection-of") and p.get("cutout"))
        g, contract = instance_group(lib, p["ref"], p["id"], p["at"],
                                     None, merged_attrs,
                                     None, p.get("rel-pos"),
                                     skin_name=p.get("skin", "default"),
                                     rotate=p.get("rotate"), mirror=bool(p.get("mirror")),
                                     palette=palette,
                                     z_inset=(p.get("inset") or 0.0)
                                     - (p.get("lift") or 0.0) - seat_lift,
                                     z_group_lift=seat_lift,
                                     inst_palette=inst_palette,
                                     skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                     resolved=resolved,
                                     # A SLOT ON A PLACED PART (B3): `port-1510/1`,
                                     # an adapter placed directly - and, since
                                     # the duplex plug, A SLOT ON A SEATED PART
                                     # TOO: `port-1510-occupant/a` is half `a`
                                     # of the plug seated at `port-1510`, where
                                     # a boot lands.
                                     #
                                     # P3 SAID "slots inside a seated part stay
                                     # chained keys" and that is still true -
                                     # `port-1510-occupant` IS the chained key,
                                     # and this only lets it carry a part id
                                     # after it. It was a blanket `None` here
                                     # because until now every occupant that
                                     # could host presented ONE interface, so
                                     # the bare chained key said everything
                                     # there was to say. generic/lc-duplex-plug@2
                                     # composes TWO generic/lc-plug@2, each with
                                     # its own rear point, and the bare key
                                     # cannot name which: the plug as a whole
                                     # presents nothing (presented_interface
                                     # declines to pick between two composed
                                     # parts), so a boot keyed there has no
                                     # point to mate to at all.
                                     #
                                     # A `plan` projection is still excluded: it
                                     # is a part seen from another face, and the
                                     # thing seated on it belongs to that face.
                                     #
                                     # A MODULE'S BACK IS NOT (B3, Task 7i). What
                                     # is seated in a cassette's rear MTP is seen
                                     # from behind and from nowhere else, so the
                                     # `rear:` projection seats it: drawn at the
                                     # module's own path (`bay-1/module`), its
                                     # slots take the module-less keys
                                     # (`bay-1/mtp1`) the front drawing hands on
                                     # (_seat_nested_occupants).
                                     path=p["projection-of"] if rear_face else None,
                                     occupants=(back_occupants(p) if rear_face
                                                else None if p.get("projection-of")
                                                else nested_occupants),
                                     occ_used=nested_used,
                                     tilt=_drawn_facet(p["tilt"], p.get("rotate")) if p.get("tilt") else None)
        # A SEATED OCCUPANT INHERITS ITS HOST'S TILT: the mate-to resolution
        # above sets `p["tilt"]`/`p["tilt-on"]` when it finds one, and `tilt`
        # (axis-swapped by `_drawn_facet` when this group's own `rotate` is
        # 90/270 - it has no container to be turned BY, unlike a part
        # composed `on` a facet) was already passed into `instance_group`
        # so this group is drawn foreshortened along the same PHYSICAL
        # dimension a part composed directly `on` a facet is.
        if p.get("tilt"):
            g.set("data-tilt-on", p["tilt-on"])
            g.set("data-tilt", f"{p['tilt']['deg']:g}")
            # `data-tilt-facing` is in the frame of the COMPONENT THAT
            # DECLARES THE FACET, not this occupant's own (possibly
            # axis-swapped) drawn one - same as `data-facet-facing` on the
            # facet node itself.
            g.set("data-tilt-facing", p["tilt"]["facing"])
        # A PROJECTION IS THE PART SEEN FROM HERE, NOT A SECOND PART. Its
        # data-path becomes data-of, naming the seated part on the face that
        # holds it; no relief, no ref, no behaviour, so the kit builds nothing
        # and ejects nothing from it - the body already stands where this is.
        if p.get("projection-of"):
            g.set("data-projection", "1")
            for node in g.iter():
                dp = node.get("data-path")
                if dp is not None:
                    # a back is drawn AT the seated part's path already (see
                    # `rear_face` above), so its paths are kept as they are
                    own = p["projection-of"]
                    node.set("data-of", dp if dp == own or dp.startswith(own + "/")
                             else own + dp[len(p["id"]):] if dp.startswith(p["id"])
                             else own)
                    del node.attrib["data-path"]
                # `data-cp*` GOES WITH THE REST. A projection is the part seen
                # from another face; the connection point it carries is the
                # SAME physical point the seated part already publishes, and a
                # second copy of it is a second cable landing on one connector.
                # It would also be unshadowable: cablePoints' rule keys on
                # data-path ancestry and the strip above has just removed
                # data-path, so the phantom's owner path is '' and no real
                # marker can be a prefix of it. Zero occurrences today - no
                # part with a connection point has a `plan` face - which is
                # exactly why it is cheaper to close now than to diagnose later.
                for k in list(node.attrib):
                    if (k.startswith("data-z-") or k.startswith("data-cp")
                            or k in ("data-depth", "data-body-depth",
                                     "data-ref", "data-behaviour",
                                     "data-vent", "data-groove")):
                        del node.attrib[k]
        # WHAT THE BLOCK IS FOR travels with every member, because the consumer
        # that needs it is looking at a member and has no way back to `groups:`.
        # A PSU bay and a line-card bay are both data-class `bay`; this is the
        # only thing that separates them. See L37.
        #
        # THE GROUP'S SIDE, from the one function that decides it -
        # cage_entries publishes the same map as a cage's `occupant-attrs`,
        # so the kit seats an optic with what the build writes here. A
        # placement's own attrs and description win over its group's: the
        # attrs were merged that way above, and the description is set below.
        write_group_side(g, p.get("group"), grp, p.get("attrs"))
        if p.get("in"):
            # a projection is flat: nothing is built from it, so it carries no
            # lift - but it keeps data-in, which the pull machinery reads
            if not p.get("projection-of"):
                sink(g, floor_of(p["in"]))
            g.set("data-in", p["in"])
        # THE THIRD OF THE TRIO, and it runs HERE rather than beside the other
        # two because `sink` above ASSIGNS data-z-lift for an `in:` well floor.
        # Set earlier it would be overwritten; added to whatever is already
        # there, a seat inside a well is the sum of the two displacements,
        # which is what relief.js's ancestor walk would compute if they were
        # two groups instead of one.
        if seat_lift and not p.get("projection-of"):
            g.set("data-z-lift", f"{float(g.get('data-z-lift') or 0) + seat_lift:g}")
        # What the lamps on this instance mean. A placement wins over its group,
        # the way attrs already do: a block of eighteen QSFP28 speed lamps says
        # its vocabulary once, and one lamp inside it may still differ.
        states = p.get("states") or grp.get("states")
        if states:
            apply_states(g, states, inst_palette)
        # The sentence the vendor wrote, kept beside the tokens rather than
        # instead of them. "Blue = 100G, Green = 40G" is not a state list and was
        # never usable as one; it is still worth carrying, so it travels as prose.
        if p.get("description"):
            g.set("data-description", p["description"])
        # what this part belongs to - an LED to its port. The tree nests on it and
        # selecting either side highlights both.
        df = data_for(p.get("for"))
        if df:
            g.set("data-for", df)
        # WHAT LIES OVER THIS PART, PUBLISHED. `under:` has ordered the paint
        # since it was added - the lid draws after the shroud it closes over -
        # but the relation itself never left this file, so a viewer that wanted
        # to take the lid off to show a selected DIMM had nothing to read and
        # would have had to guess it from overlapping boxes. The ids are bare
        # because `under:` is by definition ids in THIS view; data_for's
        # cross-view qualification does not arise.
        du = data_for(p.get("under"))
        if du:
            g.set("data-under", du)
        svg.append(g)
        cw, chh_ = contract["size"]["w"], contract["size"]["h"]
        if p.get("rotate") in (90, 270, -90):
            cx, cy = p["at"][0] + cw / 2, p["at"][1] + chh_ / 2
            x0, y0, x1, y1 = cx - chh_ / 2, cy - cw / 2, cx + chh_ / 2, cy + cw / 2
        else:
            x0, y0, x1, y1 = p["at"][0], p["at"][1], p["at"][0] + cw, p["at"][1] + chh_
        extents[0] = min(extents[0], x0); extents[1] = min(extents[1], y0)
        extents[2] = max(extents[2], x1); extents[3] = max(extents[3], y1)

    # WHAT IS UNDER SOMETHING PAINTS BEFORE IT. `under:` is the placement's
    # declaration that another part lies over it - the air shroud under the
    # system cover, the board under the fan wall - and it is the same key L13
    # reads to let the two share a plan. Both are `mounts`, so both are in the
    # second pass, and document order put the cover first: the shroud painted
    # over the lid that hides it. A part that says it is lower goes earlier.
    # Document order is kept for everything the declarations do not touch.
    # `in:` is the same stack read from the other end: what stands on a well
    # is over it, so the well is under it and paints first.
    stands_on = {}
    for q in (*parts["placements"], *parts["bays"]):
        if q.get("in"):
            stands_on.setdefault(q["in"], set()).add(q["id"])

    def _stacked(seq):
        seq = list(seq)
        for _ in range(len(seq)):
            moved = False
            for i, q in enumerate(seq):
                overs = q.get("under") or []
                overs = list(overs if isinstance(overs, list) else [overs])
                overs += stands_on.get(q["id"], ())
                j = min((k for k, r in enumerate(seq) if r["id"] in overs), default=None)
                if j is not None and j < i:
                    seq.insert(j, seq.pop(i))
                    moved = True
                    break
            if not moved:
                break
        return seq

    ordered = _stacked(parts["placements"])

    # OCCUPANTS KEYED INSIDE A SEATED MODULE (#484, R2) - `front-6/xg0` - go
    # down with the bay's module and are seated in its instance group; the
    # device-level expansion above never matches them (no placement id holds
    # a slash). So do slots at any depth (B3), and a slot on a placed part
    # (`port-1510/1`) goes down with that placement. `nested_used` collects
    # what seated, for the check after the bays are drawn.
    nested_occupants = {k: v for k, v in (config.get("occupants") or {}).items()
                        if "/" in k}
    nested_used = set()
    this_view_bays = {b["id"] for b in parts["bays"]}
    this_view_placements = {q["id"] for q in parts["placements"]
                            if not q.get("mate-to") and not q.get("projection-of")}
    drawn_placements = {q.get("id") for _face, (_n, v) in resolve_views(device, config).items()
                        for q in view_parts(v)["placements"] if q.get("at")}
    # AND THE OCCUPANTS THOSE PLACEMENTS SEAT. A device-level occupant is a
    # placement the build SYNTHESISES, so no view lists it - but it is a real
    # drawing path in whichever view holds its host, and since the duplex plug
    # it can carry keys of its own (`port-1510-occupant/a`, one half of a
    # seated plug). Without this the view that does NOT hold the host reports
    # such a key as naming nothing, which is the same false alarm the loop
    # above already avoids for the host's own key.
    drawn_placements |= {occupant_local_id(k, v if isinstance(v, dict) else {})
                         for k, v in (config.get("occupants") or {}).items()
                         if "/" not in k and v != ""}
    # the views THIS configuration draws: a bay only on an unbound variant
    # face is not drawn anywhere, so a key naming it is reported, not skipped
    drawn_bays = {b["id"] for _face, (_n, v) in resolve_views(device, config).items()
                  for b in view_parts(v)["bays"]}

    def draw_bay(b):
        bay_lift = 0.0
        bay_g = ET.SubElement(svg, f"{{{SVG_NS}}}g")
        bay_g.set("id", b["id"])
        bay_g.set("data-path", b["id"])
        bay_g.set("data-class", "bay")
        if b.get("in"):
            # A MODULE STANDS ON THE FLOOR AND RISES TO ITS OWN HEIGHT. A bay's
            # plane is where the module's face is and the body reaches back
            # from it - on a faceplate, into the chassis. In a well the body
            # reaches DOWN, so the plane has to sit the module's height above
            # the floor or a DIMM sinks 31 mm into the board and a drive hangs
            # under its tray. The well's `d` is the floor its occupants stand
            # on; this is what puts their tops where the model measured them.
            floor = floor_of(b["in"])
            # A SHELF IN THE WELL. `floor:` says the occupant stands this far
            # down rather than on the well's own floor - a card on its slot -
            # and the well is still what it is in.
            if b.get("floor"):
                floor = float(b["floor"])
                # a shelf is not a hole: the kit leaves a dark bay box behind
                # a pulled module, and for a card on a shelf that box stood on
                # the card below it
                bay_g.set("data-shelf", "1")
            if floor:
                bay_lift = -(floor - occupant_depth(b))
                bay_g.set("data-z-lift", f"{bay_lift:g}")
            bay_g.set("data-in", b["in"])
        if b.get("group"):
            bay_g.set("data-group", b["group"])
            brole = (dev_groups.get(b["group"]) or {}).get("role")
            if brole:
                bay_g.set("data-group-role", brole)
        if b.get("rel-pos") is not None:
            bay_g.set("data-rel-pos", str(b["rel-pos"]))
        title = ET.SubElement(bay_g, f"{{{SVG_NS}}}title")
        title.text = b["id"]
        # THE HOLE, NOT THE RESERVED SPACE. `size` is what the slot reserves -
        # where the occupant is placed and what it is checked against - and on a
        # card cage that is the card INCLUDING its ejector brackets. The hole its
        # plate covers is smaller, and the hole is what you see when the bay is
        # empty. Painting `size` dark put 21.5 mm of opening over sheet metal at
        # each end of every ASR 9006 slot, which is the black the owner could see
        # past the edges of an installed card.
        #
        # One field was doing two jobs. `opening` names the second one; absent, it
        # falls back to `size` and nothing changes - which is 140 of the library's
        # bays, where the two really are the same.
        #
        # It is CENTRED on the bay, because a hole and the space reserved around it
        # share a centre. Nothing here is derived from the occupant: an opening is
        # measured off the drawing or it is not stated.
        op = b.get("opening") or b["size"]
        ox = b["at"][0] + (b["size"]["w"] - op["w"]) / 2.0
        oy = b["at"][1] + (b["size"]["h"] - op["h"]) / 2.0
        opening = ET.SubElement(bay_g, f"{{{SVG_NS}}}rect")
        opening.set("id", f"{b['id']}--opening")
        opening.set("x", f"{ox:g}"); opening.set("y", f"{oy:g}")
        opening.set("width", f"{op['w']:g}"); opening.set("height", f"{op['h']:g}")
        opening.set("fill", "#101214")
        default = seated_ref(config.get("bays"), b["id"], b)
        if not default:
            # AN EMPTY BAY IS A HOLE, NOT A BLACK RECTANGLE. Without a depth the
            # opening is a flat dark patch painted on the panel, so in 3D an
            # unpopulated slot reads as a sticker rather than a recess - which is
            # what the C40G's optional secondary fan slot and its AC power bays
            # looked like, both of which are CORRECTLY empty.
            #
            # The depth is the depth of what the bay ACCEPTS: a bay that takes a
            # 300 mm power supply is a 300 mm hole whether or not one is fitted.
            # Taken from the deepest acceptable occupant, because a bay must be at
            # least as deep as the longest thing that goes in it, and stated as
            # derived rather than measured - nothing here is a new claim about the
            # chassis, it is the occupant's own published depth read through the
            # bay that holds it.
            depths = []
            for _ref in (b.get("accepts") or []):
                try:
                    _c, _ = lib.resolve(_ref)
                except Exception:
                    continue                     # L5 reports the broken ref
                _d = (_c.get("size") or {}).get("d")
                if _d:
                    depths.append(_d)
            if depths:
                opening.set("data-depth", f"{max(depths):g}")
                opening.set("data-wall", "#2a2e31")
        # A BAY ON AN OPEN FRAME OPENS INTO THE CHASSIS. Its slot is two guide
        # rails and a mid-plane, not a box, so the pocket above - walls, a floor
        # and a back as deep as the deepest occupant - is exactly what the
        # hardware does not have: sixteen of them made the CH3000 a row of closed
        # tubes. It is a see-through mouth like an open-backed bay's, and
        # `data-open-frame` asks the kit for no collar either. Occupied or not,
        # as the open-backed bay's is: the kit draws a seated module over the
        # mouth from unpunched art, and a pulled one leaves the open frame
        # rather than a dark box.
        if view.get("open-frame"):
            bay_g.set("data-open-back", "1")
            opening.set("data-see-through", "1")
            opening.set("data-open-frame", "1")
            if opening.get("data-depth") is None:
                opening.set("data-depth", f"{ch['depth']:g}")
                opening.set("data-wall", "#2a2e31")
        # A BAY WITH AN OPEN BACK IS A PASSAGE, NOT A POCKET. When the bay is
        # seen from behind (`rear:`), the rear-panel hole it names runs the
        # length of the chassis with walls of its own, so a pocket here - walls,
        # a dark floor, a back - would close the passage at the front: an empty
        # slot read as a black rectangle instead of daylight at the far end, and
        # a pulled module left the same dark box behind. The kit punches this
        # opening and builds nothing else for it.
        if b.get("rear"):
            bay_g.set("data-open-back", "1")
            opening.set("data-see-through", "1")
            # occupied or not: a pulled module must leave the same mouth an
            # empty build does, so the collar is there to meet the passage
            if opening.get("data-depth") is None:
                opening.set("data-depth", f"{occupant_depth(b):g}")
                opening.set("data-wall", "#2a2e31")
        if default:
            # THE BAY'S CENTRE, and nothing else. instance_group hangs the
            # occupant by its own middle, so there is no origin to solve for and
            # no rotation to pre-compensate: `bay.size` is already the rotated
            # footprint, so its centre is the right point at every angle.
            #
            # This replaces two special cases that each got half of it - a
            # rotation offset derived from the bay, and a centring step that
            # skipped rotated bays. An A9K-RSP880-LT-SE in an ASR 9006 hung 14 mm
            # off one end and 19 mm off the other, through the side of the
            # chassis, because the card is 428.5 long in a 395.7 slot and the
            # overhang all landed on one side.
            #
            # It RECONCILES NOTHING. The bay stays the bay, the module stays the
            # module, and L33 still reports every mismatch. A card too long for
            # its slot is still too long; it now overhangs evenly, which is what
            # a faceplate overlapping its aperture does.
            bay_centre = [b["at"][0] + b["size"]["w"] / 2.0,
                          b["at"][1] + b["size"]["h"] / 2.0]
            # THE OCCUPANT'S OWN VALUES: a configuration's `bay-attrs` reach the
            # part seated in THIS bay, the way a placement's `attrs` reach a
            # placed part - a supply's wattage, a drive's capacity
            # a module's OWN default has no key inside a bay (B3)
            refuse_bay_module_default(lib, default, f"bays/{b['id']}")
            g, contract = instance_group(lib, default, f"{b['id']}--module", b["at"],
                                         None, (config.get("bay-attrs") or {}).get(b["id"]), None, None,
                                         rotate=b.get("rotate"), palette=palette,
                                         inst_palette=inst_palette,
                                         centre=bay_centre,
                                         skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                         path=f"{b['id']}/module", resolved=resolved,
                                         seated=config.get("bays"),
                                         bay_attrs=config.get("bay-attrs"),
                                         occupants=nested_occupants,
                                         occ_used=nested_used)
            bay_g.append(g)
        df = data_for(b.get("for"))
        if df:
            bay_g.set("data-for", df)
        du = data_for(b.get("under"))
        if du:
            bay_g.set("data-under", du)
        # A MODULE'S `out` IS MEASURED FROM ITS OWN FACE, and its face is now
        # the bay's sunk plane. The kit builds a raised feature as a box from
        # its summed lift to its ABSOLUTE `out`, so a fan's release tab at
        # `out: 1.0` in a bay 3.48 down ran from -3.48 to +1.0 - through the
        # lid, whose top is at exactly 1.0, which is the shimmer and the orange
        # showing through it. Pull every `out` in here down by the bay's lift,
        # as sink() does for a placement.
        if bay_lift:
            for node in bay_g.iter():
                if node.get("data-z-out") is not None:
                    node.set("data-z-out", f"{float(node.get('data-z-out')) + bay_lift:g}")

    # FIRST PASS: the wells and the openings, interleaved by `under:`. Bays
    # paint after placements by default - a cage draws before the drives it
    # frames - but a bay that says it is under a placement paints before it:
    # the R740xd's DIMM sockets are under the mid-drive tray, and drawing every
    # bay after every well put twenty-four DIMMs on top of the tray's sheet
    # metal, so that on a mid-tray configuration the tray highlighted and
    # showed nothing. A bay has no `ref`, which is how the two are told apart.
    first = [q for q in ordered if q["id"] not in deferred_ids]
    for item in _stacked(first + list(parts["bays"])):
        if "ref" in item:
            draw_placement(item)
        else:
            draw_bay(item)

    # second pass: the surface-mounted parts, now safely in front of the openings
    for p in ordered:
        if p["id"] in deferred_ids:
            draw_placement(p)

    # A NESTED KEY THAT SEATED NOTHING IS AN ERROR, not a skip - checked once
    # both passes have drawn, since a keyed placement may be a deferred one.
    # A key whose bay or placement is on another face belongs to that face's
    # drawing, as a device-level occupant does; one whose bay or placement is
    # on THIS face and seated nothing names a bay that is empty or a part
    # without that slot, and a key whose head is on no face at all is a typo. Keys on a seated module that name no
    # cage are raised where the module is drawn (_seat_nested_occupants).
    # The resolver lint uses (manifest.nested_key_host) says what a dangling
    # key failed to reach - `'lc99'` - where it can; the generic message is
    # the fallback for a key it resolves that still seated nothing here.
    def _dangling(key, fallback):
        def _res(r):
            try:
                return lib.resolve(r)[0]
            except Exception:
                return None
        try:
            nested_key_host(key, device, config, _res)
        except ValueError as e:
            return ValueError(str(e))
        return ValueError(fallback)
    def _res_key(r):
        try:
            return lib.resolve(r)[0]
        except Exception:
            return None
    for key in sorted(set(nested_occupants) - nested_used):
        top = key.split("/", 1)[0]
        if top in this_view_bays and key_on_back(key, device, config, _res_key):
            # ON THE MODULE'S BACK, so the rear drawing seats it (B3, Task
            # 7i) - provided the bay shows its back somewhere; the resolver
            # raises when it does not, rather than the key vanishing
            nested_key_host(key, device, config, _res_key)
            continue
        if top in this_view_bays:
            raise _dangling(
                key, f"occupants/{key}: names no cage - bay {top!r} seats no module "
                "carrying it in this configuration")
        if top in this_view_placements:
            raise _dangling(
                key, f"occupants/{key}: names no slot on placement {top!r} in "
                "this configuration")
        if top not in drawn_bays and top not in drawn_placements:
            raise ValueError(
                f"occupants/{key}: {top!r} is no bay in any view this "
                "configuration draws, and no placement either")

    # A REAR PROJECTION GOES INTO THE HOLE IT IS SEEN THROUGH (see `rear:`).
    for p in parts["placements"]:
        if not p.get("cutout"):
            continue
        g = next((n for n in svg if n.get("id") == p["id"]), None)
        cg = svg.find(f".//*[@id='cutout--{p['cutout']}']")
        if g is None or cg is None:
            raise ValueError(f"{p['id']}: rear projection names cutout "
                             f"{p['cutout']!r}, which is not in this view")
        if cg.get("data-depth") is None:
            raise ValueError(f"{p['id']}: cutout {p['cutout']!r} has no `depth`, "
                             "so it is a painted hole and cannot show a back set in")
        svg.remove(g)
        cg.append(g)

    if palette or inst_palette:
        kf_name = seq_css_name
        extra = "".join(
            state_rule(f"g[data-ref^='{comp}@'] .state-{name}",
                       f"g[data-ref^='{comp}@'] .state-{name}", *style,
                       seq_name=kf_name(comp, name))
            for (comp, name), style in sorted(palette.items()))
        # An instance rule has to beat the component rule for the same name, so it
        # is written as an id selector: one id beats any number of attribute
        # selectors whatever the source order. The state class lands on the lamp
        # element from the tree, or on the whole instance from a viewer that
        # states the part rather than the lamp - so both are matched for colour,
        # which inherits. Behaviour does not inherit: an animation on the instance
        # would blink the bezel along with the lamp, so it is aimed at the lamps.
        def sels(ids, name):
            color, anim = [], []
            for i, is_lamp in ids:
                color.append(f"#{i}.state-{name}" if is_lamp
                             else f"#{i}.state-{name}, #{i} .state-{name}")
                anim.append(f"#{i}.state-{name}" if is_lamp
                            else f"#{i}.state-{name} [data-class='led'], #{i} .state-{name}")
            return ", ".join(color), ", ".join(anim)

        extra += "".join(
            state_rule(*sels(ids, name), color, alt, mode, rate=rate,
                       phases=phases, seq_name=kf_name("inst", name, i))
            for i, ((name, color, alt, mode, _seg, rate, phases), ids) in
            enumerate(sorted(inst_palette.items(),
                             key=lambda kv: tuple(str(x) for x in kv[0]))))
        style.text = STATE_CSS + extra + "\n"

    # A component's own <g id="silkscreen"> is printed on ITS faceplate, so it
    # travels with the part and is never occluded by it - unlike chassis silkscreen,
    # which the part covers. Both come out together under --without silkscreen, which
    # is what makes a bare panel-and-components drawing possible.
    if not silkscreen:
        # Two passes, because component skins have not all adopted the grouping yet.
        # The group is the convention and L38 requires it; the <text> sweep is the
        # backstop, and it is sound rather than a bodge - printed text on a faceplate
        # IS silkscreen, so a text node in a skin is silkscreen whether or not its
        # author put it in the right group. Geometry is unaffected either way.
        #
        # A LABEL IS NOT SILKSCREEN AND MUST SURVIVE. Silkscreen is ink on the metal;
        # a sticker is a separate part applied over it, and its printing belongs to
        # that part the way a cage's walls belong to the cage. The backstop could not
        # tell the difference, so `--without silkscreen` erased the text of every
        # label on the device - the AGR420's top face carries three, and a bare-panel
        # drawing rendered them as blank rectangles. A part that is nothing BUT its
        # printing, reduced to an empty box, is a picture of a device that does not
        # exist. Skip the whole subtree of an applied part rather than its text
        # nodes alone, so anything else printed on one survives with it.
        exempt = set()
        for node in svg.iter():
            if node.get("data-class") in APPLIED_CLASSES:
                exempt.update(id(d) for d in node.iter())
        for parent in svg.iter():
            if id(parent) in exempt:
                continue
            for node in [n for n in list(parent)
                         if id(n) not in exempt
                         and (n.get("id", "").endswith("silkscreen")
                              or n.get("data-class") == "silkscreen"
                              or n.tag == f"{{{SVG_NS}}}text")]:
                parent.remove(node)

    meta_payload = {
        "generator": {"tool": "portrayal-render", "version": TOOL_VERSION},
        "device": f"{device['manufacturer']} {device['model']}",
        "device-version": device["version"],
        "view": view_name,
        "resolved-components": dict(sorted(resolved.items())),
        # THE SOURCE IS NAMED, NOT CARRIED (#665). Every face of a device held
        # the same manifest - 139 MB of a 249 MB build, and 107 KB in each of
        # the R740xd's 252 faces. It is written once, as <device>.source.json,
        # and a face carries the digest of those exact bytes, so one SVG on its
        # own still says which source it was drawn from and can be checked.
        "source-sha256": hashlib.sha256(source_bytes(device)).hexdigest(),
    }
    meta.text = json.dumps(meta_payload, sort_keys=True, separators=(",", ":"))
    if extents != [0.0, 0.0, w, h]:
        vw, vh = extents[2] - extents[0], extents[3] - extents[1]
        svg.set("viewBox", f"{extents[0]:g} {extents[1]:g} {vw:g} {vh:g}")
        svg.set("width", f"{vw:g}mm"); svg.set("height", f"{vh:g}mm")
    return svg


def _inputs(device, device_yaml, lib):
    """Every file this drawing is made from.

    OVER-INCLUSIVE ON PURPOSE. All of a component's skins are counted, not the
    one a given placement picks, and this file and manifest.py are counted too.
    The failure modes are not symmetric: rebuilding something that did not need
    it costs a second, and skipping something that did leaves a stale drawing
    that looks fresh and is believed. When in doubt, rebuild.
    """
    # elements.py writes the file beside each face, so a change to it changes
    # an output as surely as a change to this file does
    files = {Path(device_yaml), Path(__file__),
             Path(__file__).with_name("manifest.py"),
             Path(__file__).with_name("elements.py")}
    seen, queue = set(), list(component_refs(device))
    while queue:
        ref = queue.pop()
        if ref in seen:
            continue
        seen.add(ref)
        try:
            contract, skins = lib.resolve(ref)
        except Exception:
            continue                      # a bad ref is the linter's to report
        if skins is not None:
            files.add(Path(skins).parent / "contract.yaml")
            files.update(Path(skins).glob("*.svg"))
        # a part's ref, every default it ships holding and every face it
        # names (drawn_refs) - a redrawn rear must rebuild its device
        queue.extend(drawn_refs(contract))
    return {f for f in files if f.exists()}


def source_bytes(device):
    """<device>.source.json, byte for byte. Faces hash exactly this."""
    return (json.dumps(device, sort_keys=True, indent=1) + "\n").encode()


def _face_files(device, outdir):
    """The per-configuration face files the last build wrote for this device."""
    return [p.name for p in Path(outdir).glob(f"{device['name']}.*.*.svg")
            if len(p.name.split(".")) == 4]


def _outputs(device, configs, default_cfg, outdir):
    """What a fresh build of this device leaves behind.

    Which configurations' names the faces carry depends on what they draw, so
    it is not known before rendering. configs.json says, when there is one: its
    `files` for every configuration it lists. When it lists a different set of
    configurations than the manifest has, the build is stale anyway.
    """
    names = {f"{device['name']}.configs.json", f"{device['name']}.source.json"}
    for view_name in device.get("views") or {}:
        names.add(f"{device['name']}.{view_name}.svg")
    idx = Path(outdir) / f"{device['name']}.configs.json"
    try:
        listed = {c["name"]: c.get("files") for c in json.loads(idx.read_text())["configs"]}
    except (OSError, ValueError, KeyError, TypeError):
        listed = {}
    for cfg_name in configs:
        if not listed.get(cfg_name):
            names.add(f"{device['name']}.{cfg_name}.__unbuilt__.svg")   # never exists: stale
            continue
        names.update(listed[cfg_name].values())
    # EVERY FACE HAS ITS ELEMENTS FILE (#727), so a dist built before there
    # were any - or one an elements file is missing from - is stale, and
    # `--if-stale` writes them rather than trusting the SVGs beside them.
    names.update(elements_mod.elements_name(n) for n in list(names) if n.endswith(".svg"))
    return {Path(outdir) / n for n in names}


def is_stale(device, device_yaml, lib, configs, default_cfg, outdir):
    """True unless every output exists and is newer than every input."""
    outs = _outputs(device, configs, default_cfg, outdir)
    if not all(o.exists() for o in outs):
        return True
    newest_in = max(f.stat().st_mtime_ns for f in _inputs(device, device_yaml, lib))
    oldest_out = min(o.stat().st_mtime_ns for o in outs)
    return newest_in >= oldest_out



# --- pluggable cage accept lists (Task 3) ------------------------------------
#
# spec/schemas/pluggables.yaml holds nine cage families - the physical envelope
# a `media` value belongs to, the rate ladder it climbs, and (`also-accepts`)
# which OTHER family's modules the cage takes wholesale. `cages[]` in the
# compiled index turns that registry, plus what the LIBRARY actually carries,
# into a per-placement accept list: what could seat here, derived, never
# declared.


def _pluggable_families():
    """family name -> {interface, rates, also-accepts, source}, or {} if the
    checkout is broken.

    Read straight from the file rather than through lint.py's own copy of this
    loader - render.py has never imported lint, and a rendered device's cage
    list is not the place to start. The two are separate readings of the same
    YAML, the way render.py and lint.py already both read device.yaml without
    either going through the other.
    """
    try:
        doc = yaml.safe_load((SCHEMAS / "pluggables.yaml").read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return doc.get("families") or {}


@functools.lru_cache(maxsize=1)
def _connector_registry():
    """interface -> {standard, note, spans}, from spec/schemas/connectors.yaml,
    or {} if the checkout is broken.

    Cached because the seating path asks for it once per drawn instance now
    (`_seat_nested_occupants`), and the file is a fact of the checkout.

    The second registry `slot_entry` answers from (B3,
    docs/pluggables-caps-design.md). A part presenting a pluggables FAMILY is a
    cage; a part presenting one of THESE interfaces is a connector slot. Read
    the same way `_pluggable_families` reads its file, for the same reason.
    """
    try:
        doc = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return doc.get("interfaces") or {}


def _family_by_interface(families, interface):
    """The (name, family) whose `interface` equals `interface`, or None.

    A cage PRESENTS an interface (`manifest.presented_interface`); a module
    MATES one (`mates:` on its contract). Both are checked against this, which
    is why it takes a bare interface string rather than a component.
    """
    for name, fam in families.items():
        if fam.get("interface") == interface:
            return name, fam
    return None


def _family_by_rate(families, media):
    """The (name, family) whose `rates` ladder carries `media`, or None.

    The reverse of `_family_by_interface`: that answers whose CAGE this is,
    this answers whose LADDER `media` is a rung of. The two usually agree -
    see `cage_entries` for the corpus fact (lint L104) where they do not.
    """
    for name, fam in families.items():
        if media in (fam.get("rates") or []):
            return name, fam
    return None


def _pluggable_candidates(lib_roots):
    """Every library component that could seat in SOME pluggable cage or
    connector slot, indexed by the interface it `mates`: `{interface: [(ref, contract), ...]}`.

    BUILT ONCE PER PROCESS. `libwalk.iter_components` is a GENERATOR - the
    same shape as `iter_devices`, which spent this very branch's last three
    commits paying for having been bound at module scope and silently
    yielding nothing on a second pass. Consumed here, in full, exactly once
    per render.py invocation, so a device with 54 ports looks a candidate up
    54 times rather than walking 633 contracts 54 times.

    NOT `library/dist/components.json`. That index does not carry `mates`,
    `interface` or `superseded-by` - it holds attrs, bays, behaviour, class,
    conforms, description, elements, fields, files, kind, major, name, ns,
    parts, size and skins, and none of the three fields this needs. Worse,
    `__main__.py` runs a renderer process per device under `xargs -P` against
    six parallel indexer pids, so that file may be stale or simply not written
    yet while this process is running - depending on it here would be a race.
    `libwalk` reads contracts off disk directly, which is what every renderer
    already does for every placement it draws.

    `mates:` IS THE GATE, NOT `behaviour`. The six plugs - generic/lc-plug@2,
    lc-duplex-plug@2, sc-plug@1, mpo12-plug@1, mpo24-plug@1 and rj45-plug@1 -
    are `class: port` and so carry no `behaviour` (their own provenance says
    why: test_behaviour.py holds every port to none), yet each is exactly what
    a connector slot must offer (B3). Every other part that declares `mates:`
    is `behaviour: occupies`, and no plug mates a pluggables family's
    interface, so no cage's accept list changes by this.
    """
    out = {}
    for cf in libwalk.iter_components(lib_roots):
        c = load_yaml(cf) or {}
        if c.get("superseded-by"):
            continue
        mates = c.get("mates")
        if not mates:
            continue
        out.setdefault(mates, []).append((libwalk.ref_of(cf), c))
    return out


def _cage_accepts(candidates, families, family, media):
    """The accept list for one cage: every candidate its family, or a family
    named in its `also-accepts`, offers - generics first (by namespace, never
    a hardcoded list of names or vendors, so a partner's part appears the
    moment it lints), then everything else alphabetically.

    THE RATE CEILING APPLIES ONLY TO A DIRECT MATCH, against THIS family's own
    ladder. `media` is a value from THIS family's vocabulary (`sfp28`,
    `qsfp-dd`, ...); it has no meaning on a DIFFERENT family's ladder, so
    there is nothing for a ceiling to compare a foreign candidate against -
    and nothing declares a rate outside its own `mates` family in the first
    place (L102). `also-accepts` is correspondingly a bare list of family
    names, not a per-entry cutoff: the registry states no per-family cutoff
    to apply, so none is invented here. That is the whole argument. The
    registry's citations describe particular rungs a particular cage takes;
    they are not a general rule about foreign ladders and are not leaned on
    as one.

    RATED PARTS NOW EXIST (the cable-end wrappers state `attrs.rate`), and a
    rated QSFP part reaches a QSFP-DD cage through `also-accepts` unfiltered.
    That is right for every rung the library carries: QSFP-DD HW 6.3 section 1
    makes a QSFP-DD cage compatible with QSFP28 and QSFP112, so no rung of the
    foreign ladder is too fast for it. The day that stops being true, the fix
    is a `rates:` cutoff on `also-accepts` in spec/schemas/pluggables.yaml,
    sourced the way every other entry in that file is.

    A CANDIDATE THAT DECLARES NO `attrs.rate` FITS EVERY RUNG of whichever
    family matched it - that is what a GENERIC is (docs/pluggables-design.md
    decision 5). A vendor part states its rung as `rate`, never `media`; L102
    holds it to that, because a rung written as `media` is invisible here.
    """
    rates = family.get("rates") or []
    ceiling = rates.index(media) if media in rates else None

    def _direct_fits(c):
        if ceiling is None:
            return True
        rate = attrs_mod.flatten(c.get("attrs")).get("rate")
        if not rate:
            return True
        return rate in rates and rates.index(rate) <= ceiling

    refs = [ref for ref, c in candidates.get(family.get("interface"), [])
            if _direct_fits(c)]
    for other in family.get("also-accepts") or []:
        other_iface = (families.get(other) or {}).get("interface")
        if not other_iface:
            continue
        refs.extend(ref for ref, _c in candidates.get(other_iface, []))

    def _sort_key(ref):
        ns = ref.split("/", 1)[0]
        return (0 if ns == "generic" else 1, ref)
    return sorted(set(refs), key=_sort_key)


def cage_entry(p, lib, families, candidates, group=None, extra_lift=0.0,
               occupant=None):
    """`slot_entry` with the connector registry read here - the name every
    caller before B3 used, kept so none of them has to change."""
    return slot_entry(p, lib, families, _connector_registry(), candidates,
                      group=group, extra_lift=extra_lift, occupant=occupant)


def slot_entry(p, lib, families, connectors, candidates, group=None,
               extra_lift=0.0, occupant=None):
    """ONE cage or connector-slot entry for ONE placement, or None when it is
    neither - the core that a device view's `cages[]` (cage_entries) and a component's own
    `cages` (component_cages, which components_index.py publishes) both call,
    so a cage on a card and a cage on a switch face are the same answer to
    the same question.

    `p` is a placement dict - a device view's placement, or a contract's
    `parts:` entry, which has the same keys that matter here (`ref`, `id`,
    `at`, `rotate`, `attrs`, `mirror`). Everything that is a FACT OF THE
    FRAME the placement sits in is handed in rather than looked up, because
    the two frames answer it differently:
      group       the placement's port group ({} or None where it has none) -
                  a device group for a device cage, the card's own COMPONENT
                  group for a card cage (#511); a card part in no group has
                  only its own `attrs.media` and empty occupant-attrs;
      extra_lift  added to the presented lift - a device cage's well sink
                  (negative), a composed part's own `lift` (see
                  component_cages);
      occupant    the configured occupant, if any.
    `mate` and `at` are in the frame `p["at"]` is written in.

    TWO REGISTRIES, ONE CORE (B3, docs/pluggables-caps-design.md). The
    presented interface is looked up in `families` (spec/schemas/
    pluggables.yaml) first and, failing that, in `connectors` (spec/schemas/
    connectors.yaml). Every entry says which it is by `kind`: `cage` or
    `connector`. A connector slot has no ladder and so no ceiling: its
    `accepts` is every candidate whose `mates:` is the interface - dust caps
    and plugs alike, never a boot, which mates a plug - and its `media` is
    None. Everything else - `mate`, `lift`, `rotate`, `mirror`,
    `group-states`, `occupant-attrs` - is the same answer to the same question.

    A PLACEMENT SEATED BY `mate-to` HAS NO `at` in this frame - the build
    solves its position from its host's mate point - so it is not published
    here. Its own slots ride on it in components.json (component_cages), the
    way a seated transceiver's two `lc` bores do. Before B3 no seated
    placement presented a registered interface, so this never arose; a
    std/lc-bore@3 seated by `mate-to` (test_chained_seats.py) is the first.
    """
    if "at" not in p:
        return None
    contract, _skins = lib.resolve(p["ref"])

    def _resolve(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None

    interface, mate_at, lift = presented_interface(contract, _resolve)
    found = _family_by_interface(families, interface) if interface else None
    if found is None:
        if not interface or interface not in (connectors or {}):
            return None
        refs = sorted({ref for ref, _c in candidates.get(interface, [])})
        return _slot_dict(p, contract, interface, None, refs, occupant, mate_at,
                          lift, extra_lift, group, "connector",
                          spanned_slots(contract, _resolve, connectors),
                          presented_turn(contract, _resolve, connectors))
    _family_name, family = found
    # `media` is the port's declared media - the cage's ceiling on its
    # family's ladder. THE PLACEMENT'S OWN `attrs.media` IS READ FIRST,
    # then its group's, which is the precedence lint.py has applied since
    # L18 (`declared = (p.get("attrs") or {}).get("media") or
    # gattrs.get("media")`) and L22/L23 read the same way. The corpus
    # declares a port's media in both places - 83 cage placements across 22
    # devices declare one their group does not, 48 of them on
    # `maiaedge/port-extender`, whose `ports` group says in its own `mixed:`
    # note that each port carries its own media rather than the group's -
    # and L22 makes a placement/group contradiction an ERROR, so
    # the two can never disagree and reading the placement first is
    # strictly safe and strictly more informative. A placement in no group
    # that declares none of its own has NO CEILING: it accepts every rate
    # of its family.
    #
    # NOT the contract's own `attrs.media`: that is the ambiguous family
    # token (`std/sfp-ganged@1` says `sfp`), and reading it here would cap
    # every SFP cage at the lowest rung of its ladder.
    media = ((p.get("attrs") or {}).get("media")
             or ((group or {}).get("attrs") or {}).get("media"))
    # THE GROUP'S MEDIA GOVERNS WHEN IT DISAGREES WITH THE APERTURE. A
    # group declaring `media: qsfp-dd` on a placement modelled with
    # `std/qsfp-ganged@1` (a QSFP aperture - the drawing may well be
    # correct; QSFP-DD and QSFP share a face opening and differ mainly in
    # depth) still needs to offer the QSFP-DD optic, because the group is
    # what SAYS what the port is; the aperture only says what it looks
    # like. `lint_device_cage_media_disagreement` (L104) flags every case
    # this fires for, so the disagreement stays visible rather than being
    # silently settled by this precedence rule.
    accept_family = family
    if media:
        media_found = _family_by_rate(families, media)
        if media_found and media_found[0] != _family_name:
            accept_family = media_found[1]
    return _slot_dict(p, contract, interface, media,
                      _cage_accepts(candidates, families, accept_family, media),
                      occupant, mate_at, lift, extra_lift, group, "cage",
                      spanned_slots(contract, _resolve, connectors),
                      presented_turn(contract, _resolve, connectors))


def _slot_dict(p, contract, interface, media, accepts, occupant, mate_at, lift,
               extra_lift, group, kind, bores, axis):
    """The published entry, one shape for a cage and a connector slot alike;
    only `kind`, `media` and how `accepts` was derived differ."""
    return {
        "id": p["id"], "at": p["at"], "interface": interface, "media": media,
        "group": p.get("group"), "rel-pos": p.get("rel-pos"),
        # HOW AN OCCUPANT IS TURNED, which for a SPANNING slot is not only the
        # placement's own rotation (B3, "The duplex host"). A duplex connector
        # is one moulding with two ferrules on an axis and cannot turn itself,
        # and the two adapters in the library disagree about that axis - one
        # puts its bores side by side, the other stacks them. So a spanning
        # slot adds `manifest.spanning_axis`, the turn that carries the
        # canonical drawing axis onto its own pair, and `solve_seat` seats its
        # occupant at the same sum - through the same `summed_rotate`, so the
        # published entry and the drawing cannot come apart. A slot that spans
        # nothing publishes its placement's `rotate` unchanged, `None` included.
        "rotate": summed_rotate(p.get("rotate"), axis),
        "accepts": accepts,
        "occupant": (occupant.get("ref") if isinstance(occupant, dict) else occupant)
                    if occupant else None,
        # WHERE AN OCCUPANT MATES, in the frame the placement is written in
        # (the device's for a device cage, the card's for a component's own)
        # with the cage's own rotation applied - the point the build's `mate-to` resolution
        # seats on (seat_point), so a consumer seating an optic here lands
        # it where the build would. `lift` is the host's presented lift,
        # what that resolution carries as `host-lift`.
        "mate": (seat_point(p["at"], contract["size"], p.get("rotate"), mate_at)
                 if mate_at is not None else None),
        "lift": float(lift or 0.0) + float(extra_lift or 0.0),
        "occupant-attrs": group_side_attrs(p.get("group"), group),
        # TWO THINGS THE BUILD DOES TO A SEATED OPTIC THAT A CONSUMER MAY
        # NOT, published so it can decline rather than seat it wrong (the
        # kit refuses both; a lift it seats, since B3 Task 9, through
        # `lift` above):
        #   mirror        this build RAISES for an occupant in a mirrored
        #                 host (the D3 refusal in the mate-to resolution);
        #   group-states  the host's group carries `states`, which
        #                 draw_placement applies to the occupant too - it
        #                 takes its host's group - and `group_side_attrs`
        #                 does not carry.
        "mirror": bool(p.get("mirror")),
        "group-states": bool((group or {}).get("states")),
        "kind": kind,
        # WHAT THE SLOT SHIPS HOLDING (B3, P5): the placement's own `default:`
        # over the placed component's top-level one (manifest.slot_default),
        # or None. The build seats it in every configuration that does not key
        # this slot; `occupant` stays the configured answer alone.
        "default": slot_default(p, contract),
        # THE SLOTS THIS ONE TAKES THE PLACE OF (B3, "The duplex host"):
        # `manifest.spanned_slots` - the ids, under this entry's own key, of the
        # bores a connector seated HERE would fill. Filling this slot and one of
        # them is an error (`refuse_spanned_overlap`), so a reader offering a
        # swap offers one level or the other. Always present, empty where the
        # slot spans nothing, for the reason `accepts: []` is always present:
        # "this slot stands alone" and "not a question this entry answers" have
        # to be tellable apart.
        "bores": bores,
    }


def cage_entries(device, view_name, lib, families, candidates, default_occupants,
                 connectors=None):
    """`cages[]` for one view: one entry per placement that presents a
    pluggable interface (`manifest.presented_interface`, looked through a
    wrapper's own `parts:` the same way a `mate-to` occupant already is), with
    the derived accept list and the configured occupant, if the DEFAULT
    configuration seats one.

    `occupant` IS THE DEFAULT CONFIGURATION'S ANSWER and cannot be anything
    else: these entries are view-static and `occupants:` is per-configuration.
    Every configuration's own map is published beside its `bays` in
    `configs[].occupants`, and that is what a consumer holding a particular
    configuration reads. The emitted shape says so where it is documented -
    see the `cages` key in `main()`.

    An entry is emitted only when the presented interface names a family in
    spec/schemas/pluggables.yaml - a placement that presents nothing (an LED,
    a jack, a fixed connector) or an interface this registry does not cover is
    silently not a cage, the same way it is silently not a bay.

    A placement presenting a connector interface in spec/schemas/
    connectors.yaml is emitted too, as `kind: connector` (B3; see slot_entry).
    `connectors` is that registry, read here when the caller has not.
    """
    if connectors is None:
        connectors = _connector_registry()
    view = device["views"][view_name] or {}
    groups = device.get("groups") or {}
    out = []
    placements = view_parts(view)["placements"]
    for p in placements:
        # A CAGE IN A WELL IS SUNK BY ITS FLOOR, and the mate-to resolution
        # carries that sink into its occupant's `host-lift` (render_view). The
        # published `lift` is documented as that same figure, so it takes the
        # same term - so a consumer seating into a lifted cage (the kit does,
        # since B3 Task 9) puts the optic on the floor, and one that does not
        # declines this one rather than seating the optic at the panel above
        # a floor it cannot see.
        extra = 0.0
        if p.get("in") and not p.get("projection-of"):
            extra = -well_floor(placements, lib, p["in"])
        entry = slot_entry(p, lib, families, connectors, candidates,
                           group=groups.get(p.get("group")), extra_lift=extra,
                           occupant=default_occupants.get(p["id"]))
        if entry is not None:
            out.append(entry)
    return out


# What a device cage carries and a component's own cage does not: a configured
# occupant, the device's port group and a group position. A card's own group
# (#511) reaches its cages through `occupant-attrs` (`data-group`), not as a
# `group` key that a consumer would read as a device group.
COMPONENT_CAGE_DROPS = ("occupant", "group", "rel-pos")


def component_presents(ref, lib, families, candidates, connectors=None):
    """WHAT A COMPONENT OFFERS THE NEXT TIER WHEN IT IS ITSELF SEATED (#611),
    in its own frame, or None.

    A seated occupant that presents an interface is a slot at its OWN key: a
    generic/lc-plug@2 in `port-4` presents `lc-plug` at its boot point, and
    the build seats common/lc-boot@1 there under the chained key
    `port-4-occupant`; a generic/sfp-lc-simplex@2 forwards its one bore and
    takes a plug under `xg0-occupant` (manifest.slot_in_slot_at - its bore is
    not a second slot). The build resolves that through `presented_interface`
    on the host (the `mate-to` path), for ANY interface something mates -
    `lc-plug` is registered as neither a cage family nor a connector slot,
    because an LC bore takes a plug and never a boot. A consumer seating
    through slots had nothing to read it from, so the chained tier was
    build-only.

    ONLY A PART THAT MATES INTO SOMETHING is ever a seat, so only one carries
    this: a card in a bay or a port wrapper on a face presents its jack as a
    slot of whatever places it, which component_cages and cage_entries
    already publish.

    THE SLOT ENTRY'S OWN SHAPE (`_slot_dict`), for a placement at the origin
    unturned: `mate` is the presented point in the component's frame and
    `lift` its presented `out` - the two numbers the build's mate-to
    resolution seats on - and `accepts` every part that mates the interface.
    A consumer carries `mate` through the seat's own placement and adds the
    seat's lift, as the build stacks a chain.
    """
    contract, _skins = lib.resolve(ref)
    if not contract.get("mates"):
        return None

    def _resolve(r):
        try:
            return lib.resolve(r)[0]
        except Exception:
            return None

    interface, mate_at, lift = presented_interface(contract, _resolve)
    if not interface or mate_at is None:
        return None
    if connectors is None:
        connectors = _connector_registry()
    kind = "cage" if _family_by_interface(families, interface) else "connector"
    refs = sorted({r for r, _c in candidates.get(interface, [])})
    if not refs:
        return None        # a slot nothing in the library can fill offers nothing
    entry = _slot_dict({"id": "", "at": [0.0, 0.0]}, contract, interface, None, refs,
                       None, mate_at, lift, 0.0, None, kind,
                       spanned_slots(contract, _resolve, connectors),
                       presented_turn(contract, _resolve, connectors))
    for k in ("id", "at", "group", "rel-pos", "occupant", "occupant-attrs"):
        entry.pop(k, None)
    return entry


def _forwarded_part(contract, lib):
    """(part, interface) for the `parts:` entry whose aperture `contract`
    presents AS ITS OWN, or None when it presents its own interface or
    forwards nothing.

    The same reading `manifest.presented_interface` makes: a contract with its
    own `interface` and point forwards nothing; otherwise, exactly one composed
    part whose contract has an `interface` and a presented point
    (`manifest.presented_point`: `interface-at`, default `mate`) is the one
    forwarded.
    """
    if contract.get("interface") and presented_point(contract):
        return None
    cores = []
    for part in contract.get("parts") or []:
        if not part.get("ref"):
            continue
        try:
            core = lib.resolve(part["ref"])[0]
        except Exception:
            continue
        if core.get("interface") and presented_point(core):
            cores.append((part, core["interface"]))
    return cores[0] if len(cores) == 1 else None


def component_cages(contract, lib, families, candidates, connectors=None, face=False,
                    module=False):
    """A component's OWN cages, in its own frame: one entry per `parts:` entry
    that presents a pluggable interface, by the same core as a device view's
    `cages[]` (cage_entry). components_index.py publishes it on the
    component, so a module swapped into a bay at runtime brings its cages
    with it (#484) - a configuration cannot say where the cages of a card it
    does not seat are.

    A WRAPPER INSIDE A COMPONENT IS LOOKED THROUGH exactly as a device wrapper
    is: `presented_interface` reads the part's contract and, failing its own
    interface, its one composed aperture. Nothing deeper is walked, on either
    side.

    THE CARD'S OWN GROUP, NO OCCUPANT. A part in one of the component's own
    `groups:` (#511) is read exactly as a device placement in a device group:
    `media` from the part and then the group, `occupant-attrs` the group's
    side (group_side_attrs) - which is what _seat_nested_occupants writes on
    an optic the build seats here, so the kit seats the same thing. A part in
    no group has its own `attrs.media` only (none: no ceiling) and empty
    `occupant-attrs`. A contract seats no occupant: which optic a card's cage
    holds is a configuration's answer, not the card's. So `occupant`, and the
    device-frame `group` and `rel-pos` keys, are DROPPED here rather than
    published as nulls that look like answers (COMPONENT_CAGE_DROPS); the
    group's name still reaches a consumer, as `data-group` in
    `occupant-attrs`.

    THE PART'S OWN `lift` IS ADDED, where a device placement's is not. The two
    words mean different things: a device placement's `lift:` is carried by
    `back` and writes no attribute (see render_view), while a composed part's
    is written as `data-z-lift` on its group (instance_group), which raises
    everything in it. An occupant seated inside the card sits BESIDE the cage
    group, not in it, so it takes that raise only if the published figure
    carries it - so the kit, which seats at a lift (B3 Task 9), raises the
    optic with the cage, and a consumer that refuses a lifted cage refuses
    it for the right reason rather than seating the optic 44 mm under a
    shelf card's raised cage.

    A WRAPPER THAT FORWARDS ITS ONE APERTURE IS THE SLOT (B3, P2). When this
    contract presents a composed part's interface as its own
    (`_forwarded_part`), that part is where the WRAPPER's placement seats an
    occupant, published once in whatever frame places the wrapper - not a
    second slot here. A contract that declares its OWN interface forwards
    nothing, and every composed part of it is still offered.

    CONNECTOR SLOTS ONLY. A pluggables cage forwarded the same way is still
    published on its wrapper, as it was before B3: a card that IS one cage
    (cisco/a9k-mpa-1x40ge@1, a CFP MIC) is seated in a bay, not a cage, so no
    frame above it lists that cage and dropping it here would lose it
    entirely (#484). Whether a cage wrapper should follow P2 is a question for
    the cage side; this does not change it.

    A FACE DRAWING FORWARDS NOTHING (B3, Task 7i). `face` is True for a
    component some module names as one of its `faces:` - a cassette's back.
    P2 publishes a forwarded slot in the frame that PLACES the wrapper, and
    nothing places a face: the module's back is drawn at the module's own
    path, never as a `parts:` entry. So a back composing ONE bulkhead - six
    FHD single-MTP backs compose `common/mpo-flange-adapter@2` and nothing
    else - would publish its only slot nowhere, while the two- and three-MTP
    backs published theirs. On a face the bulkhead is published as its own
    slot, under the id the build keys it by (`bay-1/mtp`).

    A MODULE IN A BAY FORWARDS NOTHING EITHER (#610). `module` is True for a
    component some bay can hold. The build never treats a module in a bay as a
    placed slot (manifest.slot_in_slot_at), so a card composing exactly one
    interface-bearing part - a supervisor's lone console jack - keeps it as its
    own slot, keyed `front-6/console` as the build keys it. An OCCUPANT still
    forwards: an optic with one bore is a slot at its own key, and its bore is
    not a second one.
    """
    if connectors is None:
        connectors = _connector_registry()
    fwd = _forwarded_part(contract, lib)
    forwarded = (fwd[0] if not face and not module and fwd and fwd[1] in (connectors or {})
                 and _family_by_interface(families, fwd[1]) is None else None)
    out = []
    groups = contract.get("groups") or {}
    for p in contract.get("parts") or []:
        if p is forwarded:
            continue
        entry = slot_entry(p, lib, families, connectors, candidates,
                           group=groups.get(p.get("group")),
                           extra_lift=float(p.get("lift") or 0.0))
        if entry is not None:
            for k in COMPONENT_CAGE_DROPS:
                entry.pop(k, None)
            entry["tilt"] = component_cage_tilt(contract, p)
            out.append(entry)
    return out


def component_cage_tilt(contract, part):
    """The facet a card's cage stands `on`, as the cage entry publishes it:
    `{"deg", "facing", "on"}`, or None for a cage on no facet.

    WHAT _seat_nested_occupants DOES TO AN OPTIC IN A TILTED CAGE, published so
    the kit can do the same (P3 amended). The build finds the facet from the
    cage's own `parts:` entry (`_facet_via_part`), draws the optic
    `translate(at) scale(...) rotate(...)` with the facet's cos along its axis,
    solves `at` so the optic's foreshortened mate lands on the cage's
    foreshortened one (`_tilt_offset`, both sides), and writes `data-tilt-on`
    (`<card instance id>--<on>`), `data-tilt` and `data-tilt-facing`. The
    entry's `mate` stays the flat seat_point: with the cage's `at` and this
    facet a consumer has both ends of that solve. `facing` is in the card's
    frame, as `data-tilt-facing` is.

    A COMPONENT'S CAGES ONLY. A device placement stands on no facet; a part
    that does is on a card, whose own group is where the optic is drawn.
    """
    facet, _at, _node = _facet_via_part(contract, part, "")
    if not facet:
        return None
    return {"deg": facet["deg"], "facing": facet["facing"], "on": part["on"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device_yaml")
    ap.add_argument("--library", action="append", required=True,
                    help="library root (repeatable, searched in order)")
    ap.add_argument("--out", default="dist")
    # SKIP A DEVICE WHOSE DRAWING IS ALREADY NEWER THAN EVERYTHING IT IS MADE
    # FROM. `build.sh` wipes dist and re-renders all of them, so editing one
    # manifest costs a full rebuild - fine at 21 devices, not at 200.
    ap.add_argument("--if-stale", action="store_true",
                    help="do nothing when every output is newer than every input")
    ap.add_argument("--without", dest="without", action="append", default=[],
                    choices=["silkscreen"],
                    help="omit a layer. --without silkscreen emits the punched panel and "
                         "the components installed in it, with nothing printed on either - "
                         "the drawing you hand to whoever does the artwork")
    ap.add_argument("--with", dest="include", action="append", default=[],
                    help="include optional placements tagged with this name (e.g. ears)")
    args = ap.parse_args()

    device = load_yaml(args.device_yaml)
    lib = Library(args.library)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    configs = device.get("configurations") or {"default": {"default": True}}
    default_cfg = next((n for n, c in configs.items() if c.get("default")), next(iter(configs)))
    if args.if_stale and not is_stale(device, args.device_yaml, lib,
                                      configs, default_cfg, outdir):
        print(f"up to date {device['name']}")
        return

    # EACH DISTINCT DRAWING IS WRITTEN ONCE (#665). Configurations that differ
    # only in a part one face cannot see draw that face identically: the
    # R740xd's 42 draw 2 fronts, 1 left and 10 tops, and wrote 252 files for
    # them. The first configuration (in manifest order) to draw a face names
    # its file; every later one that draws the same bytes points at it through
    # `files` in configs.json. Configurations are rendered in the same order
    # every build, so the names are deterministic.
    old = set(_face_files(device, outdir))
    # `faces` is each distinct drawing's elements document, by its SVG's name;
    # `copies` maps each default-configuration copy to the face it copies
    written, files, faces, copies = {}, {}, {}, {}
    for cfg_name, cfg in configs.items():
        # THE FACE IS THE NAME, whichever panel this configuration binds to it.
        # A consumer asks for `front` and gets this configuration's front.
        files[cfg_name] = {}
        for view_name, (_src, view) in resolve_views(device, cfg).items():
            svg = render_view(device, view_name, view or {}, lib, include=tuple(args.include),
                              silkscreen=("silkscreen" not in args.without),
                              config_name=cfg_name, config=cfg)
            ET.indent(svg, space="  ")
            data = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                    + ET.tostring(svg, encoding="unicode", xml_declaration=False) + "\n")
            key = (view_name, hashlib.sha256(data.encode()).digest())
            if key not in written:
                written[key] = f"{device['name']}.{cfg_name}.{view_name}.svg"
                (outdir / written[key]).write_text(data)
                # READ FROM THE TREE JUST SERIALISED, so the file and the
                # drawing cannot disagree (elements.py says why)
                faces[written[key]] = elements_mod.face_elements(svg, cfg_name, view_name)
            files[cfg_name][view_name] = written[key]
            if cfg_name == default_cfg:
                (outdir / f"{device['name']}.{view_name}.svg").write_text(data)
                copies[f"{device['name']}.{view_name}.svg"] = written[key]
        print(f"wrote config {cfg_name}")
    # a face the last build wrote and this one shares is stale, not a spare
    for stale in old - {n for f in files.values() for n in f.values()}:
        (outdir / stale).unlink(missing_ok=True)
        (outdir / elements_mod.elements_name(stale)).unlink(missing_ok=True)
    # THE ELEMENTS FILES, written once every configuration has said which faces
    # it draws, so a shared face lists all of them in `configs`. A default
    # copy is the same bytes as the file it copies, exactly as its SVG is.
    for name, doc in faces.items():
        doc["configs"] = sorted(c for c, f in files.items() if f.get(doc["view"]) == name)
        text = elements_mod.dumps(doc)
        (outdir / elements_mod.elements_name(name)).write_text(text)
        for copy_name in sorted(c for c, of in copies.items() if of == name):
            (outdir / elements_mod.elements_name(copy_name)).write_text(text)
    (outdir / f"{device['name']}.source.json").write_bytes(source_bytes(device))
    ch = device.get("chassis") or {}
    # What this model can and cannot do, and why. The viewer has to know before
    # it offers a control: a two-view device opened in 3D used to draw a wrong
    # box rather than say it has no top or bottom face, which is the demo lying
    # instead of declining.
    cap = capability.report(Path(args.device_yaml), device, args.library, SCHEMAS)
    # `cages[]` (Task 3) - what the library could seat in each pluggable
    # placement, derived from spec/schemas/pluggables.yaml and the library
    # itself. Computed ONCE per process: `_pluggable_candidates` materialises
    # `libwalk.iter_components` in full rather than re-walking the library for
    # every placement in every view.
    _families = _pluggable_families()
    _connectors = _connector_registry()
    _candidates = _pluggable_candidates(args.library)
    _default_occupants = (configs.get(default_cfg) or {}).get("occupants") or {}
    cfg_index = {"device": device["name"], "model": device.get("model", ""),
                 # THE OTHER NAMES THIS BOX IS SOLD OR LISTED UNDER - an HCL's
                 # AS number, a marketing name, an OEM's name (#514). Names
                 # only; kind and note stay in the manifest. `model` remains
                 # the canonical one and is never repeated here.
                 "aliases": alias_names(device),
                 "capability": cap["capability"], "gaps": cap["gaps"],
                 # FACES ONLY. A view carrying `face:` is a VARIANT - the
                 # 12 x 3.5in front is drawn when a configuration redirects the
                 # front to it, never on its own - and listing it here offered
                 # `front-lff-12` in the viewer as a seventh face beside front,
                 # rear, top, bottom, left and right. There is no such face and
                 # no file named for one: a bound variant renders as
                 # `<device>.<config>.front.svg`, under the face it replaces.
                 # `bays` below still keys every view including the variants,
                 # because a viewer holding a configuration that binds one has
                 # to know what that view holds.
                 "views": [v for v, w in device["views"].items()
                           if not (w or {}).get("face")],
                 # `airflow` is the chassis's own statement - the value every
                 # configuration that states none inherits - or null where the
                 # device says nothing. Each configuration's RESOLVED answer is
                 # `configs[].airflow` below; read that, not this, to learn how
                 # a particular build breathes.
                 "chassis": {"w": ch.get("width"), "h": ch.get("height"), "d": ch.get("depth"),
                             "ru": ch.get("ru"), "airflow": ch.get("airflow"),
                             # how the box is installed; `rack` where the
                             # device states nothing (#734)
                             "mount": ch.get("mount", "rack"),
                             # the chassis's own feed, where one feed is the
                             # whole story; `configs[].power` is each build's
                             # resolved answer, as for airflow
                             "power": ch.get("power"),
                             # a bevelled body, as the polygons the viewer
                             # builds its mesh from; absent on a plain box
                             **({"solid": _bevel.published(ch)} if ch.get("bevel") else {})},
                 # WHAT THE DEVICE CAN BE BOUGHT WITH - the union over its
                 # orderable and base builds of `configs[].power` and
                 # `configs[].airflow`. The filter an HCL runs ("DC, back-to-
                 # front") is one lookup here instead of a walk (#513).
                 "options": device_options(device),
                 # facts about the device that belong to no view. They reach the
                 # drawing as data-* on the SVG root, which meant a viewer had to
                 # load and scrape a picture to answer "how much memory" - and
                 # provenance never reached it at all.
                 #
                 # SECTIONED here, flat on the SVG root, and that asymmetry is
                 # deliberate. An SVG attribute list has no nesting to offer, and
                 # a panel that prints 24 rows in one column is a wall - the
                 # sections are what make it readable. Both shapes come from the
                 # same manifest, so neither can drift from the other.
                 "attrs": device.get("attrs") or {},
                 "provenance": device.get("provenance") or {},
                 "default": default_cfg,
                 "configs": [{"name": n, "description": c.get("description", ""),
                              # WHAT KIND OF CONFIGURATION THIS IS - `base`,
                              # `orderable`, `example` or `model` (#51). Without
                              # it a page reading the index saw the bare chassis,
                              # a SKU and somebody's illustration as three equal
                              # entries and guessed from the name (#66). A parts
                              # list refuses to price a base; a configurator
                              # starts from one. `null` only for the `default`
                              # this renderer makes up when a device declares no
                              # configurations - nothing is invented for it.
                              "kind": c.get("kind"),
                              # WHICH WAY THIS BUILD BREATHES - front-to-back,
                              # back-to-front, side or passive, the library's
                              # own words - resolved exactly as the drawing's
                              # `data-airflow` is (config_airflow: the
                              # configuration's value, else the chassis's), so
                              # a page filtering builds by airflow reads it here
                              # instead of parsing `ac-b2f` out of a name or
                              # "exhaust airflow" out of a description (#513).
                              # `null` where the device states no airflow.
                              "airflow": config_airflow(device, c),
                              # WHAT THIS BUILD IS FED WITH - `ac`, `dc`,
                              # `hvdc` - always a list, `[]` where the device
                              # states nothing (config_power). Read this rather
                              # than `ac`/`dc` out of the name.
                              "power": config_power(device, c),
                              "part-numbers": c.get("part-numbers") or {},
                              "bays": c.get("bays") or {},
                              # WHAT THIS CONFIGURATION SEATS IN ITS CAGES,
                              # keyed by placement id - the per-configuration
                              # half of `cages[]` below, exactly as `bays`
                              # here is the per-configuration half of `bays`
                              # at the top level. `occupants:` is a
                              # per-configuration key, so without this a
                              # device offering a bare and a fitted
                              # configuration published one of them and
                              # dropped the other on the floor: the
                              # view-level `cages[].occupant` can only ever
                              # report ONE configuration's answer, and it
                              # reports the DEFAULT one.
                              "occupants": c.get("occupants") or {},
                              # WHICH VARIANT VIEW STANDS IN FOR A FACE on this
                              # configuration - `{front: front-lff-12}`. The
                              # `bays` map below is keyed by view name, variants
                              # included, and a consumer looking up a face's bays
                              # on a configuration that binds a variant has to
                              # go through this or it reads the wrong front.
                              # `views` at the top level stays the six faces, so
                              # a loader that fetches a face per name never asks
                              # for a variant's file, which does not exist.
                              "views": c.get("views") or {},
                              # WHICH FILE DRAWS EACH FACE of this configuration
                              # - `{front: "r740xd.sff24-rc0-noriser.front.svg"}`.
                              # A drawing is written once and shared by every
                              # configuration that draws it identically, so the
                              # file is looked up here, never built from the
                              # configuration's name (#665).
                              "files": files.get(n, {})}
                             for n, c in sorted(configs.items())],
                 # what each bay will take, so a viewer can offer the swap rather
                 # than guessing from component class
                 "bays": {v: [{"id": b["id"], "accepts": b.get("accepts") or [],
                               "default": b.get("default"), "group": b.get("group"),
                               "rel-pos": b.get("rel-pos"),
                               # a viewer swapping an occupant has to place it the
                               # way this bay holds it. Without `rotate` the C40G's
                               # horizontal slots re-rendered their card upright.
                               "rotate": b.get("rotate"),
                               "at": b["at"], "size": b["size"]}
                              for b in view_parts(device["views"][v])["bays"]]
                          for v in device["views"]},
                 # what a pluggable placement could take, derived - never
                 # declared - from the library and spec/schemas/pluggables.yaml.
                 # Keyed by view exactly as `bays` is, variants included.
                 #
                 # `cages[].occupant` IS THE DEFAULT CONFIGURATION'S ANSWER,
                 # and only that one. These entries are view-static facts -
                 # where the cage is, what it looks like, what the library
                 # could seat in it - and `occupants:` is not one: it is
                 # declared per configuration. A consumer asking what a
                 # PARTICULAR configuration seats reads
                 # `configs[<name>].occupants`, the same way it reads
                 # `configs[<name>].bays` rather than `bays[view][].default`;
                 # `occupant` here is the convenience answer for the
                 # configuration named by `default` at the top level.
                 #
                 # THREE KEYS SAY HOW TO SEAT ONE, so a consumer (kit/swap.js)
                 # can put an optic in a cage without re-deriving the build:
                 #   mate            [x, y], where an occupant's own `mate`
                 #                   point lands, in the DEVICE frame with the
                 #                   cage's `rotate` applied (seat_point). An
                 #                   occupant takes the cage's `rotate` too
                 #                   (D3), and its `at` is seat_at(mate, rotate,
                 #                   occupant size, occupant mate).
                 #   lift            float, the cage's presented lift - what
                 #                   `mate-to` resolution carries as
                 #                   `host-lift`, and the occupant's
                 #                   data-z-lift when non-zero.
                 #   occupant-attrs  {data-attr: string}, every attribute the
                 #                   build writes on a seated occupant from the
                 #                   HOST's side (its group's attrs,
                 #                   data-group, data-group-role,
                 #                   data-description), overlaid on what the
                 #                   occupant's own contract says.
                 # and TWO SAY WHEN NOT TO: `mirror` (the build refuses an
                 # occupant in a mirrored host) and `group-states` (the host's
                 # group carries `states`, which the build applies to the
                 # seated optic). A consumer that cannot do what the build
                 # does for either declines to seat there.
                 "cages": {v: cage_entries(device, v, lib, _families, _candidates,
                                            _default_occupants,
                                            connectors=_connectors)
                           for v in device["views"]}}
    (outdir / f"{device['name']}.configs.json").write_text(json.dumps(cfg_index, indent=1, sort_keys=True))
    print(f"wrote {device['name']}.configs.json")


def _cli():
    """`main()` with the failures a person actually hits turned into messages.

    THE COMMAND IN README.md PRODUCED A TRACEBACK. A mistyped `ref:` reaches
    `Library.resolve`, which raises FileNotFoundError with a perfectly good
    sentence in it, and nothing caught it - so the first thing a newcomer saw
    after the quickstart was forty lines of Python ending in the answer
    (roc-ops/Portrayal#180). A missing skin is the same shape: `instance_group`
    raises ValueError naming the skin and what the part has.

    ONLY THE FAILURES THAT ARE ABOUT THE FILE. A KeyError or an AttributeError
    from inside the renderer is a bug in the renderer, and swallowing it into a
    one-line message would hide the traceback that gets it fixed. These three
    carry a sentence written for the reader and mean the input is wrong.
    """
    import yaml as _yaml
    argv = sys.argv[1:]
    where = next((a for a in argv if a.endswith(".yaml")), "device")
    try:
        return main()
    except (FileNotFoundError, ValueError, _yaml.YAMLError) as e:
        print(f"render: {where}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_cli() or 0)
