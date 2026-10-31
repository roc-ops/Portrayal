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
FAMILIES = ("fiber", "copper", "dac", "aoc", "power", "ground", "stack", "usb", "console")
BASES = ("standard", "convention")
# A jacket colour can also be counted on the maker's photograph (#1028).
JACKET_BASES = BASES + ("photo",)
COLOR = re.compile(r"^#[0-9a-f]{6}$")
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


def jacket_problems(where, j, sources):
    """What is wrong with one jacket: a colour, a basis, sources."""
    if not isinstance(j, dict):
        return [f"{where}: not a mapping"]
    out = []
    if not isinstance(j.get("color"), str) or not COLOR.match(j["color"]):
        out.append(f"{where}: color is # and six lower case hex digits")
    if j.get("basis") not in JACKET_BASES:
        out.append(f"{where}: basis must be one of {', '.join(JACKET_BASES)}")
    src = j.get("sources")
    if not isinstance(src, list) or not src:
        out.append(f"{where}: no sources")
    else:
        out += [f"{where}: unknown source {s!r}" for s in src if not _known(s, sources)]
    if j.get("basis") == "photo" and not (isinstance(j.get("note"), str) and j["note"].strip()):
        out.append(f"{where}: a colour read off a photograph says what was counted, in its note")
    out += [f"{where}: unknown key {k!r}" for k in sorted(set(j) - {"color", "basis", "sources", "note"})]
    return out


def dc_roles():
    """The roles a DC conductor may have: the keys of spec/schemas/dc.yaml's `roles`."""
    return tuple(load_yaml(SCHEMAS / "dc.yaml")["roles"])


def dc_problems(where, t, sources, roles):
    """What is wrong with the DC keys of one type: `dc`, `conductors`, `ampacity-a`."""
    out = []
    dc = t.get("dc")
    if "dc" in t and not isinstance(dc, bool):
        out.append(f"{where}: dc must be true or false")
    if "conductors" in t:
        cond = t["conductors"]
        if not isinstance(cond, list) or not cond:
            out.append(f"{where}: conductors is a list of one or more {{role, awg}} mappings")
        else:
            for i, c in enumerate(cond, 1):
                w = f"{where} conductor {i}"
                if not isinstance(c, dict):
                    out.append(f"{w}: not a mapping")
                    continue
                if c.get("role") == "gnd":
                    out.append(f"{w}: role 'gnd' is a ground wire, a type of its own, and not a conductor of a feed")
                elif c.get("role") not in roles:
                    out.append(f"{w}: role {c.get('role')!r} is not one of dc.yaml's roles ({', '.join(roles)})")
                if not _positive(c.get("awg")):
                    out.append(f"{w}: awg must be a positive number")
                out += [f"{w}: unknown key {k!r}" for k in sorted(set(c) - {"role", "awg"})]
    if "ampacity-a" in t:
        if not _positive(t["ampacity-a"]):
            out.append(f"{where}: ampacity-a must be a positive number of amperes")
        src = t.get("ampacity-sources")
        if not isinstance(src, list) or not src:
            out.append(f"{where}: ampacity-a has no ampacity-sources")
        else:
            out += [f"{where} ampacity-sources: unknown source {s!r}" for s in src if not _known(s, sources)]
    if dc is True:
        if t.get("family") != "power":
            out.append(f"{where}: a DC feed is of the family power")
        if "conductors" not in t:
            out.append(f"{where}: a DC feed names its conductors")
        if "ampacity-a" not in t:
            out.append(f"{where}: a DC feed states its ampacity-a")
    elif "conductors" in t:
        out.append(f"{where}: conductors belong to a DC feed, which states dc: true")
    return out


def problems(doc, roles=None):
    """Every reason the table cannot be published; [] when it can."""
    if not isinstance(doc, dict):
        return ["the table is not a mapping"]
    roles = dc_roles() if roles is None else roles
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
        out += dc_problems(w, t, sources, roles)
        # a DC feed names its `conductors` instead
        if t.get("family") == "power" and t.get("dc") is not True and not (isinstance(t.get("conductor"), str) and t["conductor"]):
            out.append(f"{w}: a power type names its cord's `conductor`")
        if "sources" in t:
            if not isinstance(t["sources"], list) or not t["sources"]:
                out.append(f"{w}: sources is a list of the documents that name the cable")
            else:
                out += [f"{w}: unknown source {s!r}" for s in t["sources"] if not _known(s, sources)]
        if (fib is not None) != (t.get("family") == "fiber"):
            out.append(f"{w}: a fiber type, and only a fiber type, states `fiber`")
        if "jacket" in t:
            out += jacket_problems(f"{w} jacket", t["jacket"], sources)
            # One table holds the colour a media is drawn in: the kit's.
            if t.get("media") == tid:
                out.append(f"{w}: a bare media type states no jacket; a media's colour is the kit's COLORS")
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
