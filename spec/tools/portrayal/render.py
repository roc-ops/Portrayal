#!/usr/bin/env python3
"""Portrayal renderer v0: compile a device manifest + component skins into flat SVG.

One SVG per view. Deterministic output: no timestamps; tool version stamped in
<metadata> along with resolved component versions and the embedded source manifest.
"""
import argparse
import copy
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

# PARTS APPLIED OVER THE PANEL RATHER THAN PRINTED INTO IT. Their text is the
# part, not silkscreen, so `--without silkscreen` leaves them alone and L38 does
# not ask them to group text they were never meant to group.
APPLIED_CLASSES = {"sticker", "label", "marking"}

import attrsections as attrs_mod
from faces import face_ref
from manifest import (view_parts, targets, split_target, component_refs,
                      presented_interface,
                      load_yaml)
import capability

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
        nsname, major = ref.rsplit("@", 1)
        for root in self.roots:
            base = root / "components" / nsname / f"v{major}"
            if (base / "contract.yaml").exists():
                contract = load_yaml(base / "contract.yaml")
                self.cache[ref] = (contract, base / "skins")
                return self.cache[ref]
        raise FileNotFoundError(f"component ref not found in library path: {ref}")


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


def rewrite_ids(el, prefix, contract, path_prefix, skip=None):
    """Prefix all ids (and url(#...) references to them); attach data-* to contracted elements."""
    elements = contract.get("elements", {}) or {}
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
            if spec.get("states"):
                node.set("data-states", " ".join(state_names(spec["states"])))
            if spec.get("description"):
                node.set("data-description", spec["description"])
    for node in el.iter():
        for attr, val in list(node.attrib.items()):
            if "url(#" in val:
                node.set(attr, URL_REF.sub(
                    lambda m: f"url(#{renamed.get(m.group(1), m.group(1))})", val))


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
    for node in list(root.iter()):
        paint = node.get("data-fill-from")
        if paint is not None and attrs.get(paint) not in (None, ""):
            node.set("fill", str(attrs[paint]).strip())
        # AND THE OUTLINE WITH IT. A coloured part is not a fill on its own: every
        # red latch in this library is `fill="#c22f2f" stroke="#8c1f1f"`, and the
        # blue variant changed both. Converting those skins to an attr with only
        # `data-fill-from` would have left a blue handle wearing a dark red
        # outline - a drawing nobody would have written by hand, arrived at by a
        # mechanism that could only say half of what the art said (#177).
        line = node.get("data-stroke-from")
        if line is not None and attrs.get(line) not in (None, ""):
            node.set("stroke", str(attrs[line]).strip())
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
    top = None
    for k in ("cyl", "bar", "uhandle"):
        if f.get(k) is not None:
            top = (f.get("lift") or 0.0) + f[k]
    if f.get("out") is not None:
        f["out"] = round(f["out"] - back, 4)
        if f["out"] <= 0:
            return None
    if f.get("lift") is not None:
        f["lift"] = round(max(0.0, f["lift"] - lb), 4)
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


def instance_group(lib, ref, inst_id, at, label, attrs, group, rel_pos, skin_name="default", rotate=None, mirror=False, palette=None, skin_overrides=None, attr_overrides=None, path=None, resolved=None, depth=0, centre=None, inst_palette=None, z_inset=0.0, z_group_lift=0.0, seated=None, bay_attrs=None):
    contract, skins = lib.resolve(ref)
    comp_name = ref.split("/")[-1].split("@")[0]
    if skin_overrides and comp_name in skin_overrides:
        skin_name = skin_overrides[comp_name]
    extra_attrs = (attr_overrides or {}).get(comp_name)
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
    merged.update(extra_attrs or {})
    merged.update(attrs or {})
    for k, v in sorted(merged.items()):
        g.set(f"data-{k}", str(v))
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
    rewrite_ids(holder, inst_id, contract, path, skip=holder)
    # TEXT FROM ATTRS, so one carrier covers a catalogue instead of a file per
    # row. `merged` is the contract's attrs under the placement's, which is
    # already the precedence every other attr consumer uses.
    fill_from_attrs(holder, merged)
    for child in list(holder):
        g.append(child)
    for feat in (contract.get("relief") or {}).get("features") or []:
        feat = _inset_feature(feat, z_inset, z_group_lift)
        if feat is None:
            continue
        want = f"{inst_id}--{feat['node']}"
        for node in g.iter():
            if node.get("id") == want:
                for zk in ("top", "sink", "out", "dome", "vent", "cyl", "lift", "bar", "uhandle"):
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
    for part in contract.get("parts") or []:
        pg, _ = instance_group(lib, part["ref"], f"{inst_id}--{part['id']}",
                               part["at"], None, part.get("attrs"), None, None,
                               skin_name=part.get("skin", "default"),
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
                               path=f"{path}/{part['id']}", resolved=resolved)
        # WHAT A COMPOSED LAMP MEANS IS THE COMPOSER'S TO SAY. A component
        # declares what a lamp IS and can only guess what it MEANS - the same
        # reasoning apply_states already carries for device placements, and the
        # same need one level down: a card composing a generic jack has an
        # indicator table for it and had no way to attach one. Without this the
        # only route was a wrapper that redraws the lamps over the ones it
        # composes, which is two nodes for one indicator.
        if part.get("states"):
            apply_states(pg, part["states"], inst_palette)
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
        feat = _inset_feature(feat, z_inset, z_group_lift)
        if feat is None:
            continue
        want = f"{inst_id}--{feat['node']}"
        for node in g.iter():
            if node.get("id") == want:
                for zk in ("top", "sink", "out", "dome", "vent", "cyl", "lift", "bar", "uhandle"):
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
        occupant = (seated or {}).get(bay_path, bay.get("default"))
        if not occupant or depth >= MAX_BAY_DEPTH:
            continue
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
            seated=seated, bay_attrs=bay_attrs)
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
    svg.set("data-config", config_name)
    # Sections are a classification, not a namespace: a drawing is opened
    # somewhere else, and `data-power-max-w` is readable there while
    # `data-power-max-w` under some section prefix would only be longer. So the
    # bag is FLATTENED here and every key keeps the exact spelling it had before
    # sections existed - re-filing a key between sections must not change a
    # single byte of a compiled drawing. attrs.flatten is shared with the search
    # index and the exporters so they cannot disagree about what the bag holds.
    for ak, av in attrs_mod.flatten(device.get("attrs")).items():
        svg.set(f"data-{ak}", str(av))
    airflow = config.get("airflow") or (device.get("chassis") or {}).get("airflow")
    if airflow:
        svg.set("data-airflow", airflow)
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
    here = {q.get("id") for q in parts["placements"]}
    for host, spec in (config.get("occupants") or {}).items():
        if host not in here:
            continue
        if isinstance(spec, str):
            spec = {"ref": spec}
        parts["placements"].append({
            "ref": spec["ref"],
            "id": spec.get("id") or f"{host}-occupant",
            "mate-to": host,
            # nests under the receptacle in the tree, the way an indicator nests
            # under what it indicates - an optic belongs to its port
            "for": host,
            "group": next((q.get("group") for q in parts["placements"]
                           if q.get("id") == host), None),
            **({"attrs": spec["attrs"]} if spec.get("attrs") else {}),
            **({"skin": spec["skin"]} if spec.get("skin") else {}),
        })

    # A SEATED PART SEEN FROM THIS FACE TOO. A bay on another view may say its
    # occupant's plan lands here (`plan:`), and the occupant's contract names
    # what draws it from above (`plan.ref`). Each becomes a placement in this
    # view - so `in:`, `under:` and the paint order all apply - marked as a
    # PROJECTION of the seated part: draw_placement swaps its data-path for
    # `data-of`, so the tree lists the part once and the kit builds nothing
    # from it. The occupants of the occupant's own bays come along at the
    # offsets those bays declare, lowest slot first so the top card paints
    # last. A mirrored plan mirrors the offsets about the plan's own width.
    cfg_bays = config.get("bays") or {}
    for other_name, other in (device.get("views") or {}).items():
        if other_name == view_name:
            continue
        for b in view_parts(other)["bays"]:
            pl = b.get("plan")
            if not pl or pl.get("view") != view_name:
                continue
            if b.get("only-in") and config_name not in b["only-in"]:
                continue
            occ = cfg_bays.get(b["id"], b.get("default"))
            if not occ:
                continue
            oc, _ = lib.resolve(occ)
            pref = face_ref(oc or {}, "plan")
            if not pref:
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
            e.set("id", f"cutout--{c['id']}")
            e.set("data-path", f"cutout:{c['id']}")
            e.set("data-class", "cutout")
            e.set("fill", "#101214")

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
    # resolve mate-to before drawing: an occupant is positioned so its `mate`
    # connection-point lands on its host's, which is what keeps centring offsets
    # out of device manifests entirely
    hosts = {q["id"]: q for q in parts["placements"] if q.get("at")}

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

    # HOW DEEP A WELL'S FLOOR IS, for whatever says it is `in:` one. The
    # aperture rule again: an unmounted, non-module part's `size.d` is the
    # depth of the recess it draws as, and the floor of that recess is where a
    # part on it sits. Emitted as a NEGATIVE data-z-lift - relief.js sums lifts
    # up the ancestor chain, so a sunk group sinks everything in it - and the
    # part's own `out` figures, which are measured from the face, are pulled
    # down by the same amount so they rise from the floor instead.
    def floor_of(wid):
        q = next((z for z in parts["placements"] if z.get("id") == wid), None)
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

    def draw_placement(p):
        if p.get("mate-to") and not p.get("at"):
            host = hosts.get(p["mate-to"])
            if host is None:
                raise ValueError(f"{p['id']}: mate-to {p['mate-to']!r} is not a "
                                 "placement with an explicit position in this view")
            hc, _ = lib.resolve(host["ref"])
            oc, _ = lib.resolve(p["ref"])
            def _res(ref):
                try:
                    return lib.resolve(ref)[0]
                except Exception:
                    return None

            # The host's mate point may be FORWARDED from a composed aperture -
            # see manifest.presented_interface. The occupant's is its own: a
            # module is the thing that mates, not a wrapper around one.
            _, hm_at = presented_interface(hc, _res)
            om = (oc.get("connection-points") or {}).get("mate")
            if hm_at is None or om is None:
                raise ValueError(f"{p['id']}: mate-to needs a 'mate' connection-point "
                                 f"on both {p['ref']} and {host['ref']} - the host may "
                                 "also present one through a composed aperture")
            p = dict(p, at=[round(host["at"][0] + hm_at[0] - om["at"][0], 4),
                            round(host["at"][1] + hm_at[1] - om["at"][1], 4)])
        if p.get("optional") and p["optional"] not in include:
            return
        grp = dev_groups.get(p.get("group")) or {}
        gattrs = grp.get("attrs") or {}
        merged_attrs = {**gattrs, **(p.get("attrs") or {})} or None
        g, contract = instance_group(lib, p["ref"], p["id"], p["at"],
                                     None, merged_attrs,
                                     p.get("group"), p.get("rel-pos"),
                                     skin_name=p.get("skin", "default"),
                                     rotate=p.get("rotate"), mirror=bool(p.get("mirror")),
                                     palette=palette,
                                     z_inset=(p.get("inset") or 0.0)
                                     - (p.get("lift") or 0.0),
                                     inst_palette=inst_palette,
                                     skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                     resolved=resolved)
        # A PROJECTION IS THE PART SEEN FROM HERE, NOT A SECOND PART. Its
        # data-path becomes data-of, naming the seated part on the face that
        # holds it; no relief, no ref, no behaviour, so the kit builds nothing
        # and ejects nothing from it - the body already stands where this is.
        if p.get("projection-of"):
            g.set("data-projection", "1")
            for node in g.iter():
                dp = node.get("data-path")
                if dp is not None:
                    node.set("data-of", p["projection-of"] + dp[len(p["id"]):]
                             if dp.startswith(p["id"]) else p["projection-of"])
                    del node.attrib["data-path"]
                for k in list(node.attrib):
                    if k.startswith("data-z-") or k in ("data-depth", "data-body-depth",
                                                        "data-ref", "data-behaviour",
                                                        "data-vent", "data-groove"):
                        del node.attrib[k]
        # WHAT THE BLOCK IS FOR travels with every member, because the consumer
        # that needs it is looking at a member and has no way back to `groups:`.
        # A PSU bay and a line-card bay are both data-class `bay`; this is the
        # only thing that separates them. See L37.
        if grp.get("role"):
            g.set("data-group-role", grp["role"])
        if p.get("in"):
            # a projection is flat: nothing is built from it, so it carries no
            # lift - but it keeps data-in, which the pull machinery reads
            if not p.get("projection-of"):
                sink(g, floor_of(p["in"]))
            g.set("data-in", p["in"])
        # What the lamps on this instance mean. A placement wins over its group,
        # the way attrs already do: a block of eighteen QSFP28 speed lamps says
        # its vocabulary once, and one lamp inside it may still differ.
        states = p.get("states") or grp.get("states")
        if states:
            apply_states(g, states, inst_palette)
        # The sentence the vendor wrote, kept beside the tokens rather than
        # instead of them. "Blue = 100G, Green = 40G" is not a state list and was
        # never usable as one; it is still worth carrying, so it travels as prose.
        desc = p.get("description") or grp.get("description")
        if desc:
            g.set("data-description", desc)
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
        default = (config.get("bays") or {}).get(b["id"], b.get("default"))
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
            g, contract = instance_group(lib, default, f"{b['id']}--module", b["at"],
                                         None, (config.get("bay-attrs") or {}).get(b["id"]), None, None,
                                         rotate=b.get("rotate"), palette=palette,
                                         inst_palette=inst_palette,
                                         centre=bay_centre,
                                         skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                         path=f"{b['id']}/module", resolved=resolved,
                                         seated=config.get("bays"),
                                         bay_attrs=config.get("bay-attrs"))
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
        "config": config_name,
        "resolved-components": dict(sorted(resolved.items())),
        "source": device,
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
    files = {Path(device_yaml), Path(__file__),
             Path(__file__).with_name("manifest.py")}
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
        for part in ((contract or {}).get("parts") or []):
            if part.get("ref"):
                queue.append(part["ref"].split(":")[0])
    return {f for f in files if f.exists()}


def _outputs(device, configs, default_cfg, outdir):
    names = {f"{device['name']}.configs.json"}
    for cfg_name in configs:
        for view_name in device.get("views") or {}:
            names.add(f"{device['name']}.{cfg_name}.{view_name}.svg")
            if cfg_name == default_cfg:
                names.add(f"{device['name']}.{view_name}.svg")
    return {outdir / n for n in names}


def is_stale(device, device_yaml, lib, configs, default_cfg, outdir):
    """True unless every output exists and is newer than every input."""
    outs = _outputs(device, configs, default_cfg, outdir)
    if not all(o.exists() for o in outs):
        return True
    newest_in = max(f.stat().st_mtime_ns for f in _inputs(device, device_yaml, lib))
    oldest_out = min(o.stat().st_mtime_ns for o in outs)
    return newest_in >= oldest_out



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

    for cfg_name, cfg in configs.items():
        # THE FACE IS THE NAME, whichever panel this configuration binds to it.
        # A consumer asks for `front` and gets this configuration's front.
        for view_name, (_src, view) in resolve_views(device, cfg).items():
            svg = render_view(device, view_name, view or {}, lib, include=tuple(args.include),
                              silkscreen=("silkscreen" not in args.without),
                              config_name=cfg_name, config=cfg)
            ET.indent(svg, space="  ")
            data = ET.tostring(svg, encoding="unicode", xml_declaration=False)
            names = [f"{device['name']}.{cfg_name}.{view_name}.svg"]
            if cfg_name == default_cfg:
                names.append(f"{device['name']}.{view_name}.svg")
            for nm in names:
                (outdir / nm).write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + data + "\n")
        print(f"wrote config {cfg_name}")
    ch = device.get("chassis") or {}
    # What this model can and cannot do, and why. The viewer has to know before
    # it offers a control: a two-view device opened in 3D used to draw a wrong
    # box rather than say it has no top or bottom face, which is the demo lying
    # instead of declining.
    cap = capability.report(Path(args.device_yaml), device, args.library, SCHEMAS)
    cfg_index = {"device": device["name"], "model": device.get("model", ""),
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
                 "chassis": {"w": ch.get("width"), "h": ch.get("height"), "d": ch.get("depth"),
                             "ru": ch.get("ru")},
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
                              "part-numbers": c.get("part-numbers") or {},
                              "bays": c.get("bays") or {},
                              # WHICH VARIANT VIEW STANDS IN FOR A FACE on this
                              # configuration - `{front: front-lff-12}`. The
                              # `bays` map below is keyed by view name, variants
                              # included, and a consumer looking up a face's bays
                              # on a configuration that binds a variant has to
                              # go through this or it reads the wrong front.
                              # `views` at the top level stays the six faces, so
                              # a loader that fetches a face per name never asks
                              # for a variant's file, which does not exist.
                              "views": c.get("views") or {}}
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
                          for v in device["views"]}}
    (outdir / f"{device['name']}.configs.json").write_text(json.dumps(cfg_index, indent=1, sort_keys=True))
    print(f"wrote {device['name']}.configs.json")


if __name__ == "__main__":
    main()
