#!/usr/bin/env python3
"""Compile lab topologies to dist/labs.json for the rack viewer.

A lab is a rack elevation plus a link list. It references devices by name and
ports by placement id; nothing about geometry lives here, because the viewer
resolves port positions from the compiled device SVGs at load time. That keeps
one source of truth - move a port in the device manifest and the cable follows.
"""
import argparse
import json
from pathlib import Path

import yaml
from portrayal.manifest import load_yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    labs = []
    for root in args.library:
        for f in sorted(Path(root).glob("labs/**/lab.yaml")):
            d = load_yaml(f) or {}
            labs.append({
                "name": d["name"],
                "title": d.get("title") or d["name"],
                "description": d.get("description", ""),
                "rack": d.get("rack") or {"height-ru": 42},
                "devices": d.get("devices") or [],
                "links": d.get("links") or [],
            })
    (out / "labs.json").write_text(json.dumps({"labs": labs}, indent=1))
    print(f"compiled {len(labs)} lab(s) -> {out}/labs.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
