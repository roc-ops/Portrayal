#!/usr/bin/env python3
"""Compile lab topologies to dist/labs.json for the rack viewer.

A lab is a rack elevation plus a link list. It references devices by name and
ports by placement id; nothing about geometry lives here, because the viewer
resolves port positions from the compiled device SVGs at load time. That keeps
one source of truth - move a port in the device manifest and the cable follows.

WHERE A DEVICE IS, though, is resolved here. A rack-face part placed `on` a
host says which unit of the host, not which unit of the rack, so every placement
is written with its position worked out (`labs.check`): `ru` the lowest absolute
rack unit, `face`, `mount`, `host` and `unit`. Every key the lab wrote is kept,
so a viewer that knows none of the new ones still finds `ru` and draws the part
on the right unit. A lab that fails the schema or a check is not written: the
build stops and says why, the same findings `lint.py` reports as L1 and
L132-L135.
"""
import argparse
import json
from pathlib import Path

from portrayal import labs as labcheck
from portrayal import libwalk
from portrayal.manifest import load_yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    labs, failed = [], []
    for root in args.library:
        for f in libwalk.iter_labs([root]):
            d = load_yaml(f) or {}
            bad = [f"{f}: [L1] {m}" for m in labcheck.schema_errors(d)]
            if bad:
                failed += bad
                continue
            found, placed = labcheck.check(d, args.library)
            bad = [f"{f}: [{code}] {msg}" for code, sev, msg in found if sev == "error"]
            if bad:
                failed += bad
                continue
            labs.append({
                "name": d["name"],
                "title": d.get("title") or d["name"],
                "description": d.get("description", ""),
                "rack": d.get("rack") or {"height-ru": labcheck.DEFAULT_HEIGHT_RU},
                "devices": placed,
                "links": d.get("links") or [],
            })
    if failed:
        print(f"labs_index: {len(failed)} error(s); labs.json not written")
        for line in failed:
            print(f"  {line}")
        return 1
    (out / "labs.json").write_text(json.dumps({"labs": labs}, indent=1))
    print(f"compiled {len(labs)} lab(s) -> {out}/labs.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
