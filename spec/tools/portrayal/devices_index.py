#!/usr/bin/env python3
"""Compile a devices.json index from the device manifests.

The demo's device picker reads this. It used to be hand-maintained, which meant
it silently went stale (and vanished entirely on a clean rebuild) - generate it
from the manifests instead, the same way components.json is generated.
"""
import argparse
import json
from pathlib import Path

import yaml

import capability

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    devices = []
    for root in args.library:
        for man in sorted(Path(root).glob("devices/*/*/device.yaml")):
            d = yaml.safe_load(man.read_text())
            if d.get("kind") != "device":
                continue
            cap = capability.report(man, d, args.library, SCHEMAS)
            devices.append({
                "name": d["name"],
                # the picker greys out what a model cannot do rather than
                # offering it and drawing something wrong, so it needs this
                # before it has loaded the device
                "capability": cap["capability"],
                "gaps": cap["gaps"],
                "model": d.get("model", d["name"]),
                "manufacturer": d.get("manufacturer", ""),
                "version": d.get("version", ""),
                "description": d.get("description", ""),
                # where it sits in the vendor's catalogue. The picker groups on
                # this; absent is fine and sorts under the manufacturer alone.
                "portfolio": d.get("portfolio") or {},
            })
    devices.sort(key=lambda x: (x["manufacturer"], x["name"]))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "devices.json").write_text(
        json.dumps({"devices": devices}, indent=1, sort_keys=True))
    print(f"compiled {len(devices)} devices -> {out}/devices.json")


if __name__ == "__main__":
    main()
