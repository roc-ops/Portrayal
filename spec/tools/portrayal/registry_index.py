#!/usr/bin/env python3
"""Publish the two source-tree files a consumer needs to export DCIM YAML.

Everything else the exporter reads already ships: <device>.source.json is the
whole device manifest, and components.json carries the five
contract fields the exporter takes off a component (attrs, description, kind,
name, parts). These two were the remainder, and both were reachable only by
someone holding a checkout - which made "export a NetBox document" a task that
required the development environment rather than the artifacts.

vendors.yaml is the corporate-lineage and NOS-vendor registry. It is what turns
`arrcus` into "Arrcus" when a listing files a device type under the company
that sells the software rather than the one that made the metal.

The listings ship WHOLE. The exporter reads their names and part numbers, but a
listing's `terms`, `interfaces` and `entity-map` are the NOS mapping - the thing
that says the port silkscreened 1 is called swp1 and answers to sfp1 over
OpenConfig. A consumer joining a drawing to a running device wants exactly that,
and publishing half of a document invites a second pass later to publish the
other half.
"""
import argparse
import json
from pathlib import Path

import yaml

from portrayal import libwalk
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
    vendors = reg.get("vendors") or {}
    (out / "vendors.json").write_text(json.dumps({
        "format": 1,
        "vendors": vendors,
        "namespaces": reg.get("namespaces") or {},
    }, indent=1))

    # Keyed by <ns>/<id> - the listing's own directory, whose namespace is the
    # NOS vendor. `hardware` inside each says which device it lists, and a
    # consumer wanting "who lists this box" inverts on that. `manufacturer` is
    # resolved here, once, so no consumer has to join vendors.json to name one.
    listings = {}
    for root in args.library:
        for f in libwalk.iter_listings([root]):
            doc = load_yaml(f) or {}
            key = libwalk.listing_key(f)
            ns = key.split("/")[0]
            listings[key] = {**doc, "ns": ns,
                             "manufacturer": (vendors.get(ns) or {}).get("display") or ns}
    (out / "listings.json").write_text(json.dumps({
        "format": 1, "listings": listings}, indent=1, sort_keys=True))

    print(f"compiled {len(vendors)} vendor(s) -> {out}/vendors.json"
          f" and {len(listings)} listing(s) -> {out}/listings.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
