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

import attrsections as attrs_mod
from manifest import view_parts, targets, split_target
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


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


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


def state_style(st):
    """(color, alt-color, mode) for one state, or None if it needs no CSS.

    A bare token needs none: it names a state with no declared presentation, and
    whatever the base stylesheet says about `state-<name>` still applies.
    """
    if not isinstance(st, dict):
        return None
    beh = st.get("behavior")
    mode = beh if isinstance(beh, str) else (beh or {}).get("mode", "solid")
    alt = None if isinstance(beh, str) else (beh or {}).get("color")
    color = st.get("color")
    if not color and mode == "solid":
        return None
    return (color, alt, mode)


def state_rule(sel_color, sel_anim, color, alt, mode):
    """The CSS for one state at one scope: what colour, and how it is lit."""
    out = ""
    decls = [d for d in (f"--led-color: {color};" if color else "",
                         f"--led-color-alt: {alt};" if alt else "") if d]
    if decls:
        out += f"\n    {sel_color} {{ {' '.join(decls)} }}"
    if mode in BLINK_KEYFRAMES:
        out += (f"\n    {sel_anim} {{ animation: {BLINK_KEYFRAMES[mode]} "
                f"1s linear infinite; }}")
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


def instance_group(lib, ref, inst_id, at, label, attrs, group, rel_pos, skin_name="default", rotate=None, palette=None, skin_overrides=None, attr_overrides=None, path=None, resolved=None, depth=0):
    contract, skins = lib.resolve(ref)
    comp_name = ref.split("/")[-1].split("@")[0]
    if skin_overrides and comp_name in skin_overrides:
        skin_name = skin_overrides[comp_name]
    extra_attrs = (attr_overrides or {}).get(comp_name)
    if palette is not None:
        comp = ref.split("@")[0]
        for spec in (contract.get("elements") or {}).values():
            for st in spec.get("states") or []:
                style = state_style(st)
                if style:
                    palette[(comp, st["name"])] = style
    skin_file = skins / f"{skin_name}.svg"
    skin = ET.parse(skin_file).getroot()
    path = path or inst_id
    if resolved is not None:
        resolved[ref] = contract["version"]
    g = ET.Element(f"{{{SVG_NS}}}g")
    g.set("id", inst_id)
    g.set("data-path", path)
    g.set("data-class", contract.get("class", "component"))
    g.set("data-ref", f"{ref}:{contract['version']}")
    # A cavity is a hole you look INTO - a port aperture, a cage. A MODULE is a
    # solid body that fills its bay, and its depth says how far it reaches into
    # the chassis, not that the face has an N-mm hole in it. Emitting data-depth
    # for one rendered every PSU and fan as an empty recess in 3D. The depth is
    # still carried, as data-body-depth, so it stays addressable.
    if contract["size"].get("d"):
        aperture = contract.get("kind") != "module" or (contract.get("relief") or {}).get("cavity")
        g.set("data-depth" if aperture else "data-body-depth", str(contract["size"]["d"]))
    relief = contract.get("relief")
    if relief:
        if relief.get("wall"):
            g.set("data-wall", relief["wall"])
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
    tf = f"translate({at[0]},{at[1]})"
    if rotate:
        cw, chh = contract["size"]["w"], contract["size"]["h"]
        tf += f" rotate({rotate} {cw / 2} {chh / 2})"
    g.set("transform", tf)
    title = ET.SubElement(g, f"{{{SVG_NS}}}title")
    title.text = label or inst_id
    # rewrite ids/url-refs across the WHOLE skin at once so a <defs> pattern in
    # one child is still resolvable from url(#...) references in its siblings
    holder = ET.Element(f"{{{SVG_NS}}}g")
    for child in list(skin):
        holder.append(copy.deepcopy(child))
    rewrite_ids(holder, inst_id, contract, path, skip=holder)
    for child in list(holder):
        g.append(child)
    for feat in (contract.get("relief") or {}).get("features") or []:
        want = f"{inst_id}--{feat['node']}"
        for node in g.iter():
            if node.get("id") == want:
                for zk in ("top", "sink", "out", "dome", "vent", "cyl", "lift", "bar", "uhandle"):
                    if feat.get(zk) is not None:
                        node.set(f"data-z-{zk}", str(feat[zk]))
                if feat.get("color"):
                    node.set("data-z-color", feat["color"])
                if feat.get("knurl"):
                    node.set("data-z-knurl", "1")
                if feat.get("thread"):
                    node.set("data-z-thread", str(feat["thread"]))
                break
    for part in contract.get("parts") or []:
        pg, _ = instance_group(lib, part["ref"], f"{inst_id}--{part['id']}",
                               part["at"], None, part.get("attrs"), None, None,
                               skin_name=part.get("skin", "default"),
                               rotate=part.get("rotate"), palette=palette,
                               skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                               path=f"{path}/{part['id']}", resolved=resolved)
        # a part on a protruding parent recesses from THAT surface, not the panel
        if part.get("lift"):
            pg.set("data-z-lift", str(part["lift"]))
        g.append(pg)
    for feat in (contract.get("relief") or {}).get("features") or []:
        want = f"{inst_id}--{feat['node']}"
        for node in g.iter():
            if node.get("id") == want:
                for zk in ("top", "sink", "out", "dome", "vent", "cyl", "lift", "bar", "uhandle"):
                    if feat.get(zk) is not None:
                        node.set(f"data-z-{zk}", str(feat[zk]))
                if feat.get("color"):
                    node.set("data-z-color", feat["color"])
                if feat.get("knurl"):
                    node.set("data-z-knurl", "1")
                if feat.get("thread"):
                    node.set("data-z-thread", str(feat["thread"]))
                # bezel plates ('out') paint over composed parts: raise direct
                # children to the end of the instance group. Only when there ARE
                # composed parts - otherwise this reorders the skin's own draw
                # order and a raised base plate paints over its own detail.
                if contract.get("parts") \
                        and any(feat.get(k) is not None for k in ("out", "cyl", "bar", "uhandle", "dome")) \
                        and node in list(g):
                    g.remove(node)
                    g.append(node)
                break

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
        for node in g.iter():
            if node.get("id") == want:
                node.set("data-path", f"{path}/{bay_id}")
                node.set("data-class", "bay")
                break
        occupant = bay.get("default")
        if not occupant or depth >= MAX_BAY_DEPTH:
            continue
        bw, bh = bay_size(bay)
        b_at = bay["at"]
        if bay.get("rotate") in (90, 270):
            d = (bw - bh) / 2.0
            b_at = [b_at[0] + d, b_at[1] - d]
        sub, _ = instance_group(
            lib, occupant, f"{inst_id}--{bay_id}--module", b_at,
            None, None, None, None, rotate=bay.get("rotate"), palette=palette,
            skin_overrides=skin_overrides, attr_overrides=attr_overrides,
            path=f"{path}/{bay_id}/module", resolved=resolved, depth=depth + 1)
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
    for d in parts["decor"]:
        r = ET.SubElement(svg, f"{{{SVG_NS}}}rect")
        r.set("x", f"{d['at'][0]:g}"); r.set("y", f"{d['at'][1]:g}")
        r.set("width", f"{d['size'][0]:g}"); r.set("height", f"{d['size'][1]:g}")
        r.set("rx", f"{d.get('rx', 0.6):g}")
        if d.get("stroke"):
            r.set("fill", "none")
            r.set("stroke", d["stroke"]); r.set("stroke-width", f"{d.get('stroke-width', 1):g}")
        else:
            if d.get("pattern") and d.get("pattern-offset"):
                ox, oy = d["pattern-offset"]
                pid = f"portrayal-{d['pattern']}-o{ox:g}-{oy:g}".replace(".", "_")
                if svg.find(f".//*[@id='{pid}']") is None:
                    base = svg.find(f".//*[@id='portrayal-{d['pattern']}']")
                    clone = ET.fromstring(ET.tostring(base))
                    clone.set("id", pid)
                    clone.set("patternTransform", f"translate({ox:g} {oy:g})")
                    base.getparent().append(clone) if hasattr(base, "getparent") else svg.find(".//{http://www.w3.org/2000/svg}defs").append(clone)
                r.set("fill", f"url(#{pid})")
            else:
                r.set("fill", f"url(#portrayal-{d['pattern']})" if d.get("pattern") else d.get("fill", "#2e3236"))
        if d.get("vent"):
            r.set("data-vent", f"{d['vent']:g}")
        if d.get("out"):
            r.set("data-z-out", f"{d['out']:g}")
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
            if c.get("shape") == "circle":
                e = ET.SubElement(cut_g, f"{{{SVG_NS}}}ellipse")
                e.set("cx", f"{x + cw_ / 2:g}"); e.set("cy", f"{y + ch_ / 2:g}")
                e.set("rx", f"{cw_ / 2:g}"); e.set("ry", f"{ch_ / 2:g}")
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
        for m in silk_items:
            x, y = m["at"]
            if m.get("path"):
                # a printed line or symbol - a leader, an arrow, an earth mark
                t = ET.Element(f"{{{SVG_NS}}}path")
                t.set("d", m["path"])
                t.set("fill", "none")
                t.set("stroke", m.get("fill") or silk_default)
                t.set("stroke-width", f"{m.get('stroke-width', 0.6):g}")
                t.set("stroke-linecap", "round"); t.set("stroke-linejoin", "round")
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
    for p in parts["placements"]:
        if p.get("mate-to") and not p.get("at"):
            host = hosts.get(p["mate-to"])
            if host is None:
                raise ValueError(f"{p['id']}: mate-to {p['mate-to']!r} is not a "
                                 "placement with an explicit position in this view")
            hc, _ = lib.resolve(host["ref"])
            oc, _ = lib.resolve(p["ref"])
            hm = (hc.get("connection-points") or {}).get("mate")
            om = (oc.get("connection-points") or {}).get("mate")
            if hm is None or om is None:
                raise ValueError(f"{p['id']}: mate-to needs a 'mate' connection-point "
                                 f"on both {p['ref']} and {host['ref']}")
            p = dict(p, at=[round(host["at"][0] + hm["at"][0] - om["at"][0], 4),
                            round(host["at"][1] + hm["at"][1] - om["at"][1], 4)])
        if p.get("optional") and p["optional"] not in include:
            continue
        grp = dev_groups.get(p.get("group")) or {}
        gattrs = grp.get("attrs") or {}
        merged_attrs = {**gattrs, **(p.get("attrs") or {})} or None
        g, contract = instance_group(lib, p["ref"], p["id"], p["at"],
                                     None, merged_attrs,
                                     p.get("group"), p.get("rel-pos"),
                                     skin_name=p.get("skin", "default"),
                                     rotate=p.get("rotate"), palette=palette,
                                     skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                     resolved=resolved)
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
        svg.append(g)
        cw, chh_ = contract["size"]["w"], contract["size"]["h"]
        if p.get("rotate") in (90, 270, -90):
            cx, cy = p["at"][0] + cw / 2, p["at"][1] + chh_ / 2
            x0, y0, x1, y1 = cx - chh_ / 2, cy - cw / 2, cx + chh_ / 2, cy + cw / 2
        else:
            x0, y0, x1, y1 = p["at"][0], p["at"][1], p["at"][0] + cw, p["at"][1] + chh_
        extents[0] = min(extents[0], x0); extents[1] = min(extents[1], y0)
        extents[2] = max(extents[2], x1); extents[3] = max(extents[3], y1)

    for b in parts["bays"]:
        bay_g = ET.SubElement(svg, f"{{{SVG_NS}}}g")
        bay_g.set("id", b["id"])
        bay_g.set("data-path", b["id"])
        bay_g.set("data-class", "bay")
        if b.get("group"):
            bay_g.set("data-group", b["group"])
        if b.get("rel-pos") is not None:
            bay_g.set("data-rel-pos", str(b["rel-pos"]))
        title = ET.SubElement(bay_g, f"{{{SVG_NS}}}title")
        title.text = b["id"]
        opening = ET.SubElement(bay_g, f"{{{SVG_NS}}}rect")
        opening.set("id", f"{b['id']}--opening")
        opening.set("x", f"{b['at'][0]:g}"); opening.set("y", f"{b['at'][1]:g}")
        opening.set("width", f"{b['size']['w']:g}"); opening.set("height", f"{b['size']['h']:g}")
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
            # instance_group rotates a component about its OWN centre, so for a
            # rotated bay the card has to be offset or it spins out of the opening.
            # The bay's size is the rotated footprint, so the unrotated component is
            # that transposed, and the offset is half the difference.
            mod_at = b["at"]
            if b.get("rotate") in (90, 270):
                d = (b["size"]["w"] - b["size"]["h"]) / 2.0
                mod_at = [b["at"][0] + d, b["at"][1] - d]
            # AN OCCUPANT IS CENTRED IN ITS BAY, not aligned to its corner. A
            # module sits in the middle of its opening, and a faceplate that is
            # LARGER than the aperture - which is the normal case once a card has
            # ejector brackets - overlaps it on both sides rather than hanging off
            # one. Aligning to the origin made an undersized cover sit flush
            # top-left with the dark opening showing along two edges, which is the
            # black seam visible on every ASR RSP slot: a 41.4 x 395.7 cover in a
            # 46.0 x 406.4 bay.
            #
            # This does NOT reconcile the two numbers and must not be read as
            # doing so. The bay stays the bay and the module stays the module;
            # L33 still reports every mismatch. All that changes is that the
            # difference is shared evenly instead of accumulating on one side.
            try:
                _c, _ = lib.resolve(default)
                _e = _c.get("insert") or _c.get("size") or {}
                if _e.get("w") and _e.get("h") and not b.get("rotate"):
                    mod_at = [mod_at[0] + (b["size"]["w"] - _e["w"]) / 2.0,
                              mod_at[1] + (b["size"]["h"] - _e["h"]) / 2.0]
            except Exception:
                pass                     # L5 reports an unresolvable ref
            g, contract = instance_group(lib, default, f"{b['id']}--module", mod_at,
                                         None, None, None, None,
                                         rotate=b.get("rotate"), palette=palette,
                                         skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                         path=f"{b['id']}/module", resolved=resolved)
            bay_g.append(g)
        df = data_for(b.get("for"))
        if df:
            bay_g.set("data-for", df)

    if palette or inst_palette:
        extra = "".join(
            state_rule(f"g[data-ref^='{comp}@'] .state-{name}",
                       f"g[data-ref^='{comp}@'] .state-{name}", *style)
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
            state_rule(*sels(ids, name), color, alt, mode)
            for (name, color, alt, mode), ids in sorted(
                inst_palette.items(), key=lambda kv: tuple(str(x) for x in kv[0])))
        style.text = STATE_CSS + extra + "\n"

    # A component's own <g id="silkscreen"> is printed on ITS faceplate, so it
    # travels with the part and is never occluded by it - unlike chassis silkscreen,
    # which the part covers. Both come out together under --without silkscreen, which
    # is what makes a bare panel-and-components drawing possible.
    if not silkscreen:
        # Two passes, because component skins have not all adopted the grouping yet.
        # The group is the convention and lint will come to require it; the <text>
        # sweep is the backstop, and it is sound rather than a bodge - printed text on
        # a faceplate IS silkscreen, so a text node in a skin is silkscreen whether or
        # not its author put it in the right group. Geometry is unaffected either way.
        for parent in svg.iter():
            for node in [n for n in list(parent)
                         if n.get("id", "").endswith("silkscreen")
                         or n.get("data-class") == "silkscreen"
                         or n.tag == f"{{{SVG_NS}}}text"]:
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device_yaml")
    ap.add_argument("--library", action="append", required=True,
                    help="library root (repeatable, searched in order)")
    ap.add_argument("--out", default="dist")
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
    for cfg_name, cfg in configs.items():
        for view_name, view in device["views"].items():
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
                 "views": list(device["views"].keys()),
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
                              "part-numbers": c.get("part-numbers") or {},
                              "bays": c.get("bays") or {}}
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
