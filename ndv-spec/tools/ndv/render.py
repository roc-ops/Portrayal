#!/usr/bin/env python3
"""NDV renderer v0: compile a device manifest + component skins into flat SVG.

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

TOOL_VERSION = "0.1.0"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

STATE_CSS = """
    [data-path] { cursor: pointer; }
    .state-up    { --led-color: #22c55e; }
    .state-activity { --led-color: #86efac; }
    .state-ok    { --led-color: #22c55e; }
    .state-fault { --led-color: #ef4444; }
    .state-fail  { --led-color: #ef4444; }
    .state-locate { --led-color: #3b82f6; }
    .state-absent { opacity: 0.35; }
    .ndv-highlight { filter: drop-shadow(0 0 1.2px #f59e0b) drop-shadow(0 0 0.5px #f59e0b); }
    .ndv-dim { opacity: 0.25; }
    [data-class='region'].ndv-highlight { stroke: #f59e0b; stroke-width: 0.7; filter: none; }
    .state-fail[data-class='psu'], .state-fail[data-class='fan'] { filter: drop-shadow(0 0 1.4px #ef4444); }
"""


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


def state_colors(states):
    return {st["name"]: st["color"] for st in states or []
            if isinstance(st, dict) and st.get("color")}


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
    for node in el.iter():
        for attr, val in list(node.attrib.items()):
            if "url(#" in val:
                node.set(attr, URL_REF.sub(
                    lambda m: f"url(#{renamed.get(m.group(1), m.group(1))})", val))


def instance_group(lib, ref, inst_id, at, label, attrs, group, rel_pos, skin_name="default", rotate=None, palette=None, skin_overrides=None, attr_overrides=None, path=None, resolved=None):
    contract, skins = lib.resolve(ref)
    comp_name = ref.split("/")[-1].split("@")[0]
    if skin_overrides and comp_name in skin_overrides:
        skin_name = skin_overrides[comp_name]
    extra_attrs = (attr_overrides or {}).get(comp_name)
    if palette is not None:
        comp = ref.split("@")[0]
        for spec in (contract.get("elements") or {}).values():
            for name, color in state_colors(spec.get("states")).items():
                palette[(comp, name)] = color
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
    if contract["size"].get("d"):
        g.set("data-depth", str(contract["size"]["d"]))
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
    return g, contract


def label_el(svg, at, size_wh, label, label_at, anchor, chassis_h, font_size=None, fill=None):
    """Place a label: at label_at (relative to component origin) if given,
    else centered below the component (falling back to above near the bottom edge)."""
    fs = font_size or 2.2
    if label_at:
        lx, ly = at[0] + label_at[0], at[1] + label_at[1]
    else:
        lx = at[0] + size_wh[0] / 2
        ly = at[1] + size_wh[1] + 2.6
        if ly > chassis_h - 0.5:
            ly = max(2.2, at[1] - 1.0)
    for i, line in enumerate(label.split("\n")):
        svg.append(text_el(lx, ly + i * fs * 1.15, line, size=fs, anchor=anchor or "middle",
                           fill=fill or "#c7ccd1"))


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


def render_view(device, view_name, view, lib, include=(), config_name="default", config=None):
    config = config or {}
    ch = device["chassis"]
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
    for ak, av in (device.get("attrs") or {}).items():
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
    pending_labels = []
    palette = {}

    used_patterns = {d.get("pattern") for d in (view.get("decor") or []) if d.get("pattern")}
    if used_patterns:
        defs = ET.SubElement(svg, f"{{{SVG_NS}}}defs")
        if "vent" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "ndv-vent"); pat.set("width", "8.86"); pat.set("height", "5.11")
            pat.set("patternUnits", "userSpaceOnUse")
            for cx, cy in ((0.0, 0.0), (8.86, 0.0), (4.43, 2.555), (0.0, 5.11), (8.86, 5.11)):
                hexpath = ET.SubElement(pat, f"{{{SVG_NS}}}path")
                pts = [(cx + 2.55, cy), (cx + 1.275, cy + 2.208), (cx - 1.275, cy + 2.208),
                       (cx - 2.55, cy), (cx - 1.275, cy - 2.208), (cx + 1.275, cy - 2.208)]
                hexpath.set("d", "M " + " L ".join(f"{x:g} {y:g}" for x, y in pts) + " Z")
                hexpath.set("fill", "#17191c")
        if "holes" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "ndv-holes"); pat.set("width", "5"); pat.set("height", "5")
            pat.set("patternUnits", "userSpaceOnUse")
            c = ET.SubElement(pat, f"{{{SVG_NS}}}circle")
            c.set("cx", "2.5"); c.set("cy", "2.5"); c.set("r", "1.1"); c.set("fill", "#3c4046")
        if "slots-h" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "ndv-slots-h"); pat.set("width", "14"); pat.set("height", "8")
            pat.set("patternUnits", "userSpaceOnUse")
            rct = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            rct.set("x", "2.5"); rct.set("y", "2.9"); rct.set("width", "9"); rct.set("height", "2.2")
            rct.set("rx", "1.1"); rct.set("fill", "#3c4046")
        if "slots" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "ndv-slots"); pat.set("width", "8"); pat.set("height", "14")
            pat.set("patternUnits", "userSpaceOnUse")
            rct = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            rct.set("x", "2.9"); rct.set("y", "2.5"); rct.set("width", "2.2"); rct.set("height", "9")
            rct.set("rx", "1.1"); rct.set("fill", "#3c4046")
        if "ribs" in used_patterns:
            pat = ET.SubElement(defs, f"{{{SVG_NS}}}pattern")
            pat.set("id", "ndv-ribs"); pat.set("width", "7.2"); pat.set("height", "6")
            pat.set("patternUnits", "userSpaceOnUse")
            fin = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            fin.set("x", "0"); fin.set("y", "0"); fin.set("width", "4.8"); fin.set("height", "6")
            fin.set("fill", "#e8eaed")
            gap = ET.SubElement(pat, f"{{{SVG_NS}}}rect")
            gap.set("x", "5.4"); gap.set("y", "0"); gap.set("width", "1.8"); gap.set("height", "6")
            gap.set("fill", "#6a7075")
    for d in view.get("decor", []) or []:
        if d.get("text"):
            t = text_el(d["at"][0], d["at"][1], d["text"],
                        size=d.get("font-size", 2.2), anchor=d.get("anchor", "middle"),
                        fill=d.get("fill") or ch.get("silk", "#c7ccd1"))
            if d.get("rotate"):
                t.set("transform", f"rotate({d['rotate']:g} {d['at'][0]:g} {d['at'][1]:g})")
            svg.append(t)
            continue
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
                pid = f"ndv-{d['pattern']}-o{ox:g}-{oy:g}".replace(".", "_")
                if svg.find(f".//*[@id='{pid}']") is None:
                    base = svg.find(f".//*[@id='ndv-{d['pattern']}']")
                    clone = ET.fromstring(ET.tostring(base))
                    clone.set("id", pid)
                    clone.set("patternTransform", f"translate({ox:g} {oy:g})")
                    base.getparent().append(clone) if hasattr(base, "getparent") else svg.find(".//{http://www.w3.org/2000/svg}defs").append(clone)
                r.set("fill", f"url(#{pid})")
            else:
                r.set("fill", f"url(#ndv-{d['pattern']})" if d.get("pattern") else d.get("fill", "#2e3236"))
        if d.get("vent"):
            r.set("data-vent", f"{d['vent']:g}")
        if d.get("out"):
            r.set("data-z-out", f"{d['out']:g}")
        if d.get("sink"):
            r.set("data-groove", f"{d['sink']:g}")

    # regions first (under components)
    for region in view.get("regions", []) or []:
        r = ET.SubElement(svg, f"{{{SVG_NS}}}rect")
        r.set("id", f"region--{region['id']}")
        r.set("data-path", f"region:{region['id']}")
        r.set("data-class", "region")
        pc = (config.get("region-context") or {}).get(region["id"], region.get("physical-context"))
        if pc:
            r.set("data-physical-context", pc)
        if region.get("members"):
            r.set("data-members", " ".join(region["members"]))
        at = region.get("at", [0, 0]); size = region.get("size", {"w": 0, "h": 0})
        r.set("x", f"{at[0]:g}"); r.set("y", f"{at[1]:g}")
        r.set("width", f"{size['w']:g}"); r.set("height", f"{size['h']:g}")
        r.set("rx", "0.8")
        # regions are addressable, not visible; highlight CSS gives them a stroke on demand
        r.set("fill", "none")
        r.set("stroke", "none")
        r.set("pointer-events", "all")

    extents = [0.0, 0.0, w, h]
    for p in view.get("placements", []) or []:
        if p.get("optional") and p["optional"] not in include:
            continue
        g, contract = instance_group(lib, p["ref"], p["id"], p["at"],
                                     p.get("label"), p.get("attrs"),
                                     p.get("group"), p.get("rel-pos"),
                                     skin_name=p.get("skin", "default"),
                                     rotate=p.get("rotate"), palette=palette,
                                     skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                     resolved=resolved)
        svg.append(g)
        cw, chh_ = contract["size"]["w"], contract["size"]["h"]
        if p.get("rotate") in (90, 270, -90):
            cx, cy = p["at"][0] + cw / 2, p["at"][1] + chh_ / 2
            x0, y0, x1, y1 = cx - chh_ / 2, cy - cw / 2, cx + chh_ / 2, cy + cw / 2
        else:
            x0, y0, x1, y1 = p["at"][0], p["at"][1], p["at"][0] + cw, p["at"][1] + chh_
        extents[0] = min(extents[0], x0); extents[1] = min(extents[1], y0)
        extents[2] = max(extents[2], x1); extents[3] = max(extents[3], y1)
        if p.get("label"):
            pending_labels.append((p["at"], (contract["size"]["w"], contract["size"]["h"]),
                                   p["label"], p.get("label-at"), p.get("label-anchor"),
                                   p.get("label-size"), p.get("label-color")))

    for b in view.get("bays", []) or []:
        bay_g = ET.SubElement(svg, f"{{{SVG_NS}}}g")
        bay_g.set("id", b["id"])
        bay_g.set("data-path", b["id"])
        bay_g.set("data-class", "bay")
        if b.get("group"):
            bay_g.set("data-group", b["group"])
        if b.get("rel-pos") is not None:
            bay_g.set("data-rel-pos", str(b["rel-pos"]))
        title = ET.SubElement(bay_g, f"{{{SVG_NS}}}title")
        title.text = b.get("label") or b["id"]
        opening = ET.SubElement(bay_g, f"{{{SVG_NS}}}rect")
        opening.set("id", f"{b['id']}--opening")
        opening.set("x", f"{b['at'][0]:g}"); opening.set("y", f"{b['at'][1]:g}")
        opening.set("width", f"{b['size']['w']:g}"); opening.set("height", f"{b['size']['h']:g}")
        opening.set("fill", "#101214")
        default = (config.get("bays") or {}).get(b["id"], b.get("default"))
        if default:
            g, contract = instance_group(lib, default, f"{b['id']}--module", b["at"],
                                         b.get("label"), None, None, None, palette=palette,
                                         skin_overrides=skin_overrides, attr_overrides=attr_overrides,
                                         path=f"{b['id']}/module", resolved=resolved)
            bay_g.append(g)
        if b.get("label"):
            pending_labels.append((b["at"], (b["size"]["w"], b["size"]["h"]),
                                   b["label"], b.get("label-at"), b.get("label-anchor"),
                                   b.get("label-size"), b.get("label-color")))

    if palette:
        extra = "".join(
            f"\n    g[data-ref^='{comp}@'] .state-{name} {{ --led-color: {color}; }}"
            for (comp, name), color in sorted(palette.items()))
        style.text = STATE_CSS + extra + "\n"

    # labels paint above all components/bays (silkscreen is on top of the chassis)
    silk = ch.get("silk", "#c7ccd1")
    for at, wh, label, label_at, anchor, fsize, lcolor in pending_labels:
        label_el(svg, at, wh, label, label_at, anchor, h, fsize, fill=lcolor or silk)

    meta_payload = {
        "generator": {"tool": "ndv-render", "version": TOOL_VERSION},
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
    cfg_index = {"device": device["name"], "model": device.get("model", ""),
                 "views": list(device["views"].keys()),
                 "chassis": {"w": ch.get("width"), "h": ch.get("height"), "d": ch.get("depth")},
                 "default": default_cfg,
                 "configs": [{"name": n, "description": c.get("description", ""),
                              "part-numbers": c.get("part-numbers") or {}}
                             for n, c in sorted(configs.items())]}
    (outdir / f"{device['name']}.configs.json").write_text(json.dumps(cfg_index, indent=1, sort_keys=True))
    print(f"wrote {device['name']}.configs.json")


if __name__ == "__main__":
    main()
