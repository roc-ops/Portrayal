#!/usr/bin/env python3
"""The rack catalogue: rack.json, beside devices.json in the build.

What a rack tool needs of every device without opening it: its rack units,
depth, how it mounts, whether its body is sheet, the cable capacity its vendor
states, and the ids a cable route can pass through on each view of its default
configuration. The kit's rack/catalog.js reads it through `dist`, so a rack is
checked against the same numbers wherever it is built.

Run by build.sh after the compiled faces and the indexes it reads exist.

    rack_index.py --dist library/dist
"""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

RU = 44.45
FORMAT = 1


def marked(path):
    """The ids a route can pass through on one compiled face, as a route names
    them: a ring component carrying `data-guide`, or a component instance in the
    `guides` group, is its own id (`guide-1`); a ring's end on a front or rear
    view, `<id>-end` with `data-kind="ring"`, stands for the same ring; a duct
    rect `guide--<id>` is `<id>`; a pass-through `pass--<id>` is `<id>`."""
    if not Path(path).is_file():
        return [], []
    root = ET.parse(path).getroot()
    guides, passes = set(), set()
    for e in root.iter():
        i = e.get("id") or ""
        if not i:
            continue
        if e.get("data-class") == "pass" and i.startswith("pass--"):
            passes.add(i[len("pass--"):])
        elif e.get("data-class") == "guide" and i.startswith("guide--"):
            guides.add(i[len("guide--"):])
        elif e.get("data-kind") == "ring" and i.endswith("-end"):
            guides.add(i[:-len("-end")])
        elif e.get("data-guide") or (e.get("data-group") == "guides" and e.get("data-ref")):
            guides.add(i)
    return sorted(guides), sorted(passes)


def build(dist):
    dist = Path(dist)
    devices = json.loads((dist / "devices.json").read_text())["devices"]
    out = {}
    for d in sorted(devices, key=lambda d: d["name"]):
        p = dist / f"{d['name']}.configs.json"
        if not p.is_file():
            continue
        idx = json.loads(p.read_text())
        c = idx.get("chassis") or {}
        # a stated 0 (a zero-U part's face) is a height, not a missing one
        h = c.get("h") if c.get("h") is not None else RU
        entry = {
            "manufacturer": d.get("manufacturer"),
            "model": d.get("model") or d["name"],
            "family": (d.get("portfolio") or {}).get("family"),
            # chassis.ru when stated - 0 included, a zero-U part - else from the height
            "ru": c["ru"] if c.get("ru") is not None else max(1, round(h / RU)),
            "h": h, "w": c.get("w"), "d": c.get("d"), "airflow": c.get("airflow"),
            "default": idx.get("default"),
            "configs": [x["name"] for x in idx.get("configs", [])],
        }
        # only what a device has, so the file barely grows
        if c.get("mount") and c["mount"] != "rack":
            entry["mount"] = c["mount"]
        if c.get("shell"):
            entry["shell"] = c["shell"]
        perf = (idx.get("attrs") or {}).get("performance") or {}
        if perf.get("cable-capacity") is not None:
            entry["capacity"] = {"count": perf["cable-capacity"], "basis": perf.get("cable-capacity-basis", "")}
        for view in ("top", "front", "rear"):
            g, ps = marked(dist / f"{d['name']}.{idx.get('default')}.{view}.svg")
            if g:
                entry.setdefault("guides", {})[view] = g
            if ps:
                entry.setdefault("passes", {})[view] = ps
        out[d["name"]] = entry
    return {"format": FORMAT,
            "generated-from": "devices.json and <name>.configs.json, by rack_index.py",
            "devices": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", required=True)
    a = ap.parse_args()
    data = build(a.dist)
    (Path(a.dist) / "rack.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(f"rack_index: {len(data['devices'])} devices -> {a.dist}/rack.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
