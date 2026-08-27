#!/usr/bin/env python3
"""Compile library/dist/gaps.json - every gap across the portfolio.

The register is BUILT, not maintained. Adding a device produces its gap list
automatically, and fixing a manifest removes the entry on the next build. That
is what makes it scale to hundreds of models: nobody has to remember to file
anything, and nothing has to be closed by hand.

A device model is never finished, and the reason is usually not laziness - it is
that the information does not exist in any document we hold. The S9510-28DC's
port lamps are the worked example: its hardware installation guide has LED
tables for GNSS, SYNC, STAT, FAN, PWR, the PSU and fan FRUs and the management
jack, and no table at all for the port lamps. That is a durable fact about the
world and it will still be true next year. This file is where it lives so that
somebody else can close it.
"""
import argparse
import json
from pathlib import Path

import yaml
from manifest import load_yaml

import capability

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    gaps, blocked, devices = [], {}, 0
    for root in args.library:
        for man in sorted(Path(root).glob("devices/*/*/device.yaml")):
            d = load_yaml(man)
            if d.get("kind") != "device":
                continue
            devices += 1
            rep = capability.report(man, d, args.library, SCHEMAS)
            for g in rep["gaps"]:
                gaps.append(dict(g, device=d["name"],
                                 manufacturer=d.get("manufacturer", "")))
            # The chain gets its own field rather than a gap record per level.
            # It used to be both, which meant every unsatisfied level printed
            # its one sentence twice and left consumers de-duplicating by string
            # equality. One statement, one place.
            if rep["capability"]["blocked"]:
                blocked[d["name"]] = rep["capability"]["blocked"]

    by_kind = {}
    for g in gaps:
        by_kind[g["kind"]] = by_kind.get(g["kind"], 0) + 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "gaps.json").write_text(json.dumps(
        {"gaps": gaps, "blocked": blocked, "devices": devices,
         "by-kind": by_kind},
        indent=1, sort_keys=True))
    print(f"compiled {len(gaps)} gaps across {devices} devices "
          f"({by_kind.get('declared', 0)} declared, {by_kind.get('derived', 0)} "
          f"derived) -> {out}/gaps.json")


if __name__ == "__main__":
    main()
