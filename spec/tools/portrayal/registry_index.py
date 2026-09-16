#!/usr/bin/env python3
"""Publish the two source-tree files a consumer needs to export DCIM YAML.

Everything else the exporter reads already ships: the compiled SVG embeds the
whole device manifest in its <metadata>, and components.json carries the five
contract fields the exporter takes off a component (attrs, description, kind,
name, parts). These two were the remainder, and both were reachable only by
someone holding a checkout - which made "export a NetBox document" a task that
required the development environment rather than the artifacts.

vendors.yaml is the corporate-lineage and NOS-vendor registry. It is what turns
`arrcus` into "Arrcus" when an overlay re-files a device under the company that
sells the software rather than the one that made the metal.

The overlays ship WHOLE, not just their `identity:`. The exporter happens to
read identity today, but an overlay's `terms`, `interfaces` and `entity-map` are
the NOS mapping - the thing that says the port silkscreened 1 is called swp1 and
answers to sfp1 over OpenConfig. A consumer joining a drawing to a running
device wants exactly that, and publishing half of a document invites a second
pass later to publish the other half.
"""
import argparse
import json
from pathlib import Path

import yaml

from portrayal.manifest import load_yaml

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    # Defaulted rather than required: build.sh drives every index with the same
    # two flags, and a tool that needed a third would drop out of that loop.
    ap.add_argument("--schemas", default=str(SCHEMAS))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    reg = yaml.safe_load((Path(args.schemas) / "vendors.yaml").read_text()) or {}
    (out / "vendors.json").write_text(json.dumps({
        "format": 1,
        "vendors": reg.get("vendors") or {},
        "namespaces": reg.get("namespaces") or {},
    }, indent=1))

    # Keyed by <ns>/<model> - the directory path, which is how an overlay names
    # its own device and how a component ref names a namespace. devices.json is
    # keyed by bare `name`, but a bare name cannot say which vendor's tree it
    # came from, and this file has to survive two vendors shipping one model.
    overlays, n = {}, 0
    for root in args.library:
        for f in sorted(Path(root).glob("devices/*/*/overlays/*.yaml")):
            doc = load_yaml(f) or {}
            key = f"{f.parents[2].name}/{f.parents[1].name}"
            overlays.setdefault(key, {})[f.stem] = doc
            n += 1
    (out / "overlays.json").write_text(json.dumps({
        "format": 1, "overlays": overlays}, indent=1))

    print(f"compiled {len(reg.get('vendors') or {})} vendor(s) -> {out}/vendors.json"
          f" and {n} overlay(s) on {len(overlays)} device(s) -> {out}/overlays.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
