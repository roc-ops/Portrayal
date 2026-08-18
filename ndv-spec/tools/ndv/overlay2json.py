#!/usr/bin/env python3
"""Compile a device's NOS overlays to JSON for browser consumption."""
import argparse
import json
from pathlib import Path

import yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device_dir", help="devices/<vendor>/<model> directory")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    ddir = Path(args.device_dir)
    device = yaml.safe_load((ddir / "device.yaml").read_text())
    overlays = {}
    for f in sorted((ddir / "overlays").glob("*.yaml")):
        o = yaml.safe_load(f.read_text())
        overlays[o["nos"]] = o
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"device": device["name"], "overlays": overlays},
                              indent=1, sort_keys=True))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
