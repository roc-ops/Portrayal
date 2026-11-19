#!/usr/bin/env python3
"""Compile library/dist/din-rails.json - the DIN rail profiles (#736).

The source is spec/schemas/din-rails.yaml, which says what each key means.
This checks its shape and writes it out as JSON, with each profile's `id` added
beside its key. A table that fails a check is not written and the build stops:
a figure with no document and page behind it is one nobody can trust, and a
rail drawn from it would be believed.

`slot_centres` is the slot rule of the table's header, so a consumer does not
derive it again.
"""
import argparse
import json
import re
from pathlib import Path

from portrayal.manifest import load_yaml

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
FORMAT = 1
ID = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
SECTION = ("width", "height", "thickness", "crown-outer", "crown-inner", "flange")
SLOT = ("width", "length", "pitch", "end-to-arc-centre", "first-centre")


def _positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def source_problems(where, refs, sources):
    """What is wrong with one `sources` list: entries `{id, page}` of the table."""
    if not isinstance(refs, list) or not refs:
        return [f"{where}: no sources"]
    out = []
    for r in refs:
        if not isinstance(r, dict) or set(r) != {"id", "page"}:
            out.append(f"{where}: a source is {{id, page}}")
            continue
        if r["id"] not in sources:
            out.append(f"{where}: unknown source {r['id']!r}")
        elif not (isinstance(r["page"], int) and not isinstance(r["page"], bool)
                  and 1 <= r["page"] <= sources[r["id"]]["pages"]):
            out.append(f"{where}: page {r['page']!r} is not a page of {r['id']}")
    return out


def length_problems(where, fig, sources):
    """A `{mm, sources}` figure: a positive length and its sources."""
    if not isinstance(fig, dict):
        return [f"{where}: missing"]
    out = [] if _positive(fig.get("mm")) else [f"{where}: mm must be a positive number"]
    out += source_problems(where, fig.get("sources"), sources)
    extra = set(fig) - {"mm", "sources", "basis", "note"}
    return out + [f"{where}: unknown key {k!r}" for k in sorted(extra)]


def profile_problems(pid, p, sources):
    w = f"profile {pid}"
    if not ID.match(str(pid)):
        return [f"{w}: an id is lower case letters, digits, dots and hyphens"]
    if not isinstance(p, dict):
        return [f"{w}: not a mapping"]
    out = []
    if not isinstance(p.get("label"), str) or not p["label"]:
        out.append(f"{w}: no label")
    sec = p.get("section")
    if not isinstance(sec, dict):
        out.append(f"{w}: no section")
    else:
        for k in SECTION:
            out += length_problems(f"{w} section.{k}", sec.get(k), sources)
    slot = p.get("slot")
    if not isinstance(slot, dict):
        out.append(f"{w}: no slot")
    else:
        for k in SLOT:
            out += length_problems(f"{w} slot.{k}", slot.get(k), sources)
        # a slot that does not fit between two neighbours is a misread figure
        if all(_positive((slot.get(k) or {}).get("mm")) for k in ("length", "pitch")) \
                and slot["length"]["mm"] >= slot["pitch"]["mm"]:
            out.append(f"{w}: the slot is as long as its pitch or longer")
    mass = p.get("mass-kg-per-m")
    if not isinstance(mass, dict):
        out.append(f"{w}: no mass-kg-per-m")
    else:
        out += [f"{w} mass-kg-per-m.{k}: must be a positive number"
                for k in ("plain", "slotted") if not _positive(mass.get(k))]
        out += source_problems(f"{w} mass-kg-per-m", mass.get("sources"), sources)
    for group in ("standards", "stock", "finishes"):
        node = p.get(group)
        items = node.items() if isinstance(node, dict) else enumerate(node or [])
        if not node:
            out.append(f"{w}: no {group}")
        for key, item in items:
            out += source_problems(f"{w} {group}[{key}]", (item or {}).get("sources"), sources)
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
    if not isinstance(sources, dict) or not sources:
        out.append("no sources")
        sources = {}
    for sid, s in sources.items():
        if not isinstance(s, dict) or not s.get("title") or not str(s.get("url", "")).startswith("https://") \
                or not (isinstance(s.get("pages"), int) and s["pages"] > 0):
            out.append(f"source {sid}: needs a title, an https url and a page count")
            sources = {k: v for k, v in sources.items() if k != sid}
    profiles = doc.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        out.append("no profiles")
        profiles = {}
    for pid, p in profiles.items():
        out += profile_problems(pid, p, sources)
    return out


def slot_centres(profile, length):
    """Slot centres, in millimetres from the left end, of `profile` cut to `length`.

    From `first-centre`, one `pitch` each; a slot is present only if the whole
    of it lies inside the length. Sourced for a length that is a multiple of
    the pitch (the table's header); for any other it is the proposed rule.
    """
    if not _positive(length):
        raise ValueError("a rail's length is a positive number of millimetres")
    slot = profile["slot"]
    pitch, half = slot["pitch"]["mm"], slot["length"]["mm"] / 2
    out, c = [], slot["first-centre"]["mm"]
    while c + half <= length:
        out.append(round(c, 3))
        c += pitch
    return out


def load_table(schemas=SCHEMAS):
    return load_yaml(Path(schemas) / "din-rails.yaml")


def build(schemas=SCHEMAS):
    src = Path(schemas) / "din-rails.yaml"
    doc = load_table(schemas)
    bad = problems(doc)
    if bad:
        raise SystemExit(f"{src}: " + "; ".join(bad))
    return {"format": doc["format"], "version": str(doc["version"]),
            "generated-from": "spec/schemas/din-rails.yaml",
            "sources": doc["sources"],
            "profiles": {pid: {"id": pid, **p} for pid, p in doc["profiles"].items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemas", default=str(SCHEMAS))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    j = build(args.schemas)
    (out / "din-rails.json").write_text(json.dumps(j, indent=1, sort_keys=True) + "\n")
    print(f"compiled {len(j['profiles'])} DIN rail profiles -> {out}/din-rails.json")


if __name__ == "__main__":
    main()
