#!/usr/bin/env python3
"""Compile library/dist/cable-types.json - the named cable types (#919).

The source is spec/schemas/cable-types.yaml, which says what each key means.
This checks its shape and writes it out as JSON, with each type's `id` added
beside its key, so a consumer that iterates the types does not have to carry
the key along. A table that fails a check is not written and the build stops:
a radius without a source, or a multiple of a diameter the type does not
state, is a figure nobody can trust, and the bend checks would believe it.
"""
import argparse
import json
import re
from pathlib import Path

from portrayal.manifest import load_yaml

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
FORMAT = 1
FAMILIES = ("fiber", "copper", "dac", "aoc", "power")
BASES = ("standard", "convention")
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def _positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def _known(sid, sources):
    return isinstance(sid, str) and sid in sources


def radius_problems(where, r, sources, nullable):
    """What is wrong with one radius: `{mm}` or `{xOD}`, a basis, sources."""
    if r is None:
        return [] if nullable else [f"{where}: missing"]
    if not isinstance(r, dict):
        return [f"{where}: not a mapping"]
    out = []
    rule = [k for k in ("mm", "xOD") if k in r]
    if len(rule) != 1:
        out.append(f"{where}: give exactly one of mm or xOD")
    elif not _positive(r[rule[0]]):
        out.append(f"{where}: {rule[0]} must be a positive number")
    if r.get("basis") not in BASES:
        out.append(f"{where}: basis must be one of {', '.join(BASES)}")
    src = r.get("sources")
    if not isinstance(src, list) or not src:
        out.append(f"{where}: no sources")
    else:
        out += [f"{where}: unknown source {s!r}" for s in src if not _known(s, sources)]
    if "unverified" in r and not isinstance(r["unverified"], bool):
        out.append(f"{where}: unverified must be true or false")
    extra = set(r) - {"mm", "xOD", "basis", "sources", "note", "unverified"}
    out += [f"{where}: unknown key {k!r}" for k in sorted(extra)]
    return out


def problems(doc):
    """Every reason the table cannot be published; [] when it can."""
    if not isinstance(doc, dict):
        return ["the table is not a mapping"]
    out = []
    if doc.get("format") != FORMAT:
        out.append(f"format must be {FORMAT}")
    if not VERSION.match(str(doc.get("version", ""))):
        out.append("version must be MAJOR.MINOR.PATCH")
    sources = doc.get("sources") or {}
    if not isinstance(sources, dict):
        out.append("sources is not a mapping")
        sources = {}
    for sid, s in sources.items():
        if not isinstance(s, dict) or not s.get("title") or not str(s.get("url", "")).startswith("https://"):
            out.append(f"source {sid}: needs a title and an https url")
    types = doc.get("types") or {}
    if not isinstance(types, dict):
        out.append("types is not a mapping")
        types = {}
    if not types:
        out.append("no types")
    for tid, t in types.items():
        w = f"type {tid}"
        if not ID.match(str(tid)):
            out.append(f"{w}: an id is lower case letters, digits and hyphens")
        if not isinstance(t, dict):
            out.append(f"{w}: not a mapping")
            continue
        for key in ("label", "media"):
            if not isinstance(t.get(key), str) or not t[key]:
                out.append(f"{w}: no {key}")
        if t.get("family") not in FAMILIES:
            out.append(f"{w}: family must be one of {', '.join(FAMILIES)}")
        if not _positive(t.get("od_mm")):
            out.append(f"{w}: od_mm must be a positive number")
        od_src = t.get("od_sources")
        if not isinstance(od_src, list) or not od_src:
            out.append(f"{w}: no od_sources")
        else:
            out += [f"{w}: unknown source {s!r}" for s in od_src if not _known(s, sources)]
        mbr = t.get("min_bend_radius")
        if not isinstance(mbr, dict):
            out.append(f"{w}: no min_bend_radius")
        else:
            out += radius_problems(f"{w} installed", mbr.get("installed"), sources, False)
            out += radius_problems(f"{w} loaded", mbr.get("loaded"), sources, True)
            out += [f"{w}: unknown min_bend_radius key {k!r}"
                    for k in sorted(set(mbr) - {"installed", "loaded"})]
        fib = t.get("fiber")
        if fib is not None and not isinstance(fib, dict):
            out.append(f"{w}: fiber is not a mapping")
        elif fib is not None and "min_bend" in fib:
            out += radius_problems(f"{w} fiber.min_bend", fib["min_bend"], sources, False)
        if t.get("family") == "power" and not (isinstance(t.get("conductor"), str) and t["conductor"]):
            out.append(f"{w}: a power type names its cord's `conductor`")
        if (fib is not None) != (t.get("family") == "fiber"):
            out.append(f"{w}: a fiber type, and only a fiber type, states `fiber`")
    # Every bare Rack Builder media has to be a type of its own, so a cable's
    # media resolves with no mapping (kit/rack/cable-types.js).
    named = {t.get("media") for t in types.values() if isinstance(t, dict) and isinstance(t.get("media"), str)}
    for media in sorted(named - {"power", ""}):
        if media not in types:
            out.append(f"media {media}: no type has the id {media}")
    return out


def build(schemas=SCHEMAS):
    src = Path(schemas) / "cable-types.yaml"
    doc = load_yaml(src)
    bad = problems(doc)
    if bad:
        raise SystemExit(f"{src}: " + "; ".join(bad))
    return {"format": doc["format"], "version": str(doc["version"]),
            "generated-from": "spec/schemas/cable-types.yaml",
            "sources": doc["sources"],
            "types": {tid: {"id": tid, **t} for tid, t in doc["types"].items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemas", default=str(SCHEMAS))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    j = build(args.schemas)
    (out / "cable-types.json").write_text(json.dumps(j, indent=1, sort_keys=True) + "\n")
    print(f"compiled {len(j['types'])} cable types -> {out}/cable-types.json")


if __name__ == "__main__":
    main()
