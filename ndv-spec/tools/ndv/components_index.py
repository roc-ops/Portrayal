#!/usr/bin/env python3
"""Publish every library component COMPILED (skin + composed parts flattened)
to dist/components/ with a JSON index for the demo component browser."""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from render import SVG_NS, STATE_CSS, Library, instance_group  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "components").mkdir(parents=True, exist_ok=True)
    lib = Library(args.library)
    index = []
    for root in args.library:
        for cf in sorted(Path(root).glob("components/*/*/v*/contract.yaml")):
            data = yaml.safe_load(cf.read_text())
            ns = cf.parents[2].name
            major = cf.parent.name
            ref = f"{ns}/{data['name']}@{major[1:]}"
            entry = {
                "ns": ns, "name": data["name"], "major": major,
                "version": data["version"], "kind": data.get("kind"),
                "class": data.get("class"), "conforms": data.get("conforms"),
                "size": data["size"], "description": data.get("description", ""),
                "attrs": data.get("attrs") or {},
                "provenance": data.get("provenance") or {},
                "skins": data.get("skins", ["default"]),
                "elements": sorted((data.get("elements") or {}).keys()),
                "parts": [p["ref"] for p in data.get("parts") or []],
            }
            files = {}
            for skin in entry["skins"]:
                if not (cf.parent / "skins" / f"{skin}.svg").exists():
                    continue
                w, h = data["size"]["w"], data["size"]["h"]
                svg = ET.Element(f"{{{SVG_NS}}}svg")
                svg.set("width", f"{w}mm"); svg.set("height", f"{h}mm")
                svg.set("viewBox", f"0 0 {w} {h}")
                style = ET.SubElement(svg, f"{{{SVG_NS}}}style")
                palette = {}
                g, _ = instance_group(lib, ref, data["name"], [0, 0], None, None,
                                      None, None, skin_name=skin, palette=palette,
                                      resolved={})
                extra = "".join(
                    f"\n    g[data-ref^='{comp}@'] .state-{name} {{ --led-color: {color}; }}"
                    for (comp, name), color in sorted(palette.items()))
                style.text = STATE_CSS + extra
                svg.append(g)
                ET.indent(svg, space="  ")
                fname = f"{ns}--{data['name']}--{major}--{skin}.svg"
                (out / "components" / fname).write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    + ET.tostring(svg, encoding="unicode") + "\n")
                files[skin] = f"components/{fname}"
            entry["files"] = files
            if data.get("body"):
                sides = {}
                for side in ("left", "right", "top", "bottom", "rear"):
                    sp2 = cf.parent / "skins" / f"body-{side}.svg"
                    if sp2.exists():
                        fname = f"{ns}--{data['name']}--{major}--body-{side}.svg"
                        (out / "components" / fname).write_text(sp2.read_text())
                        sides[side] = f"components/{fname}"
                entry["body"] = {**data["body"], "sides": sides}
            index.append(entry)
    (out / "components.json").write_text(json.dumps({"components": index}, indent=1, sort_keys=True))
    print(f"compiled {len(index)} components -> {out}/components.json")


if __name__ == "__main__":
    main()
