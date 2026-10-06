#!/usr/bin/env python3
"""Write library/components/CATALOGUE.md: every component, one row, grouped by
namespace, with what a contributor needs to decide whether to reuse it.

Reads the contracts and the device manifests directly rather than dist/, so the
page can be written without a build.

GENERATED, AND NOT COMMITTED. `./build.sh` writes the page on every build. It
used to be committed, with a test holding the copy to this script's output, and
its component total and per-part device counts moved with nearly every pull
request - so any two open pull requests conflicted on it, and the second to
merge had to merge main in and regenerate it. The path is gitignored instead.

    python3 spec/tools/portrayal/components_catalogue.py --library library --out library/components/CATALOGUE.md
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from portrayal import libwalk
# libyaml, through the shared loader, now that every build runs this: the
# pure-Python parser made it the slowest walk in the build's index pass
# (about 16 s against about 3 s, every contract and manifest read once).
from portrayal.manifest import load_yaml

REF = re.compile(r"\b([a-z0-9-]+)/([a-z0-9-]+)@(\d+)\b")

# A BLOCK THAT EXPLAINS WHY NOTHING USES A PART MUST NOT READ AS A USE. Both
# counters below match refs in the raw text, which is deliberate - a part cited
# in provenance as the origin of a borrowed figure is worth showing - but
# `unplaced:` and `superseded-by:` are the two fields whose whole subject is a
# ref that is NOT a user. `unplaced:` names the part that superseded it or the
# issue that will seat it; `superseded-by:` names the successor a retired part
# points at, without composing it - the same shape, the opposite direction.
# Counted, `common/psu-550w@1` would report itself as composing the `@2` that
# replaced it, and `common/sfp-lc-duplex@1` would report itself as composing
# `generic/sfp-lc@1` rather than the other way round. Each block runs from its
# key to the next one at column zero, or to the end of the file.
NON_USE_BLOCK = re.compile(r"^(?:unplaced|superseded-by):.*?(?=^\S|\Z)", re.M | re.S)


def without_non_use_refs(text):
    return NON_USE_BLOCK.sub("", text)


def first_sentence(text, limit=110):
    s = " ".join(str(text or "").split())
    s = s.split(". ")[0].rstrip(".")
    return (s[: limit - 1] + "…") if len(s) > limit else s


def size_text(size):
    if not isinstance(size, dict):
        return ""
    w, h, d = size.get("w"), size.get("h"), size.get("d")
    out = f"{w:g} × {h:g}" if w is not None and h is not None else ""
    if d is not None:
        out += f" × {d:g}"
    return out


def composed_by(library):
    """ref -> contracts that compose it through `parts:` (or otherwise name it)."""
    users = defaultdict(set)
    for contract in sorted(library.glob("components/*/*/v*/contract.yaml")):
        own = f"{contract.parts[-4]}/{contract.parts[-3]}@{contract.parts[-2][1:]}"
        for ns, name, major in set(REF.findall(without_non_use_refs(contract.read_text()))):
            ref = f"{ns}/{name}@{major}"
            if ref != own:
                users[ref].add(own)
    return users


def seated_by(library):
    """ref -> device slugs that SEAT it: a placement or bay whose `ref`,
    `default` or `accepts` names the major, or a configuration whose `bays` or
    `occupants` does (#348).

    NOT A TEXT MATCH, which this was. A ref named in a provenance sentence or
    a comment counted the same as one a bay places, and three of the nine
    devices #264 counted for common/usb-a@3 named it to say they do not use
    it. The parsed manifest is read instead - a device's layout.yaml, where it
    has one, is expanded INTO that manifest, so it adds nothing to read.
    """
    users = defaultdict(set)

    def named(v):
        if isinstance(v, str):
            yield v.split(":")[0]
        elif isinstance(v, dict) and isinstance(v.get("ref"), str):
            yield v["ref"].split(":")[0]

    for dev in libwalk.iter_devices([library]):
        slug = f"{dev.parent.parent.name}/{dev.parent.name}"
        doc = load_yaml(dev) or {}
        refs = set()
        for view in (doc.get("views") or {}).values():
            comps = (view or {}).get("components") or {}
            for item in (comps.get("placements") or []) + (comps.get("bays") or []):
                for key in ("ref", "default"):
                    refs.update(named(item.get(key)))
                for a in item.get("accepts") or []:
                    refs.update(named(a))
        for cfg in (doc.get("configurations") or {}).values():
            for key in ("bays", "occupants"):
                for v in ((cfg or {}).get(key) or {}).values():
                    refs.update(named(v))
        for ref in refs:
            if REF.fullmatch(ref):
                users[ref].add(slug)
    return users


def build(library):
    library = Path(library)
    users = seated_by(library)
    parts = composed_by(library)
    groups = defaultdict(list)
    for contract in sorted(library.glob("components/*/*/v*/contract.yaml")):
        ns, name, vdir = contract.parts[-4], contract.parts[-3], contract.parts[-2]
        doc = load_yaml(contract) or {}
        ref = f"{ns}/{name}@{vdir[1:]}"
        groups[ns].append({
            "ref": ref,
            "kind": doc.get("kind", ""),
            "class": doc.get("class", ""),
            "size": size_text(doc.get("size")),
            "fits": doc.get("conforms") or doc.get("interface") or doc.get("mates") or "",
            "used": len(users.get(ref, ())),
            "parts": len(parts.get(ref, ())),
            "what": first_sentence(doc.get("description")),
        })
    order = ["std", "common", "generic"] + sorted(
            k for k in groups if k not in ("std", "common", "generic"))
    lines = [
        "# Component catalogue",
        "",
        "Generated by `./build.sh`, and not committed: rebuild after pulling, or the page",
        "describes the library you had. Without a build,",
        "`python3 spec/tools/portrayal/components_catalogue.py --library library --out",
        "library/components/CATALOGUE.md` writes it.",
        "",
        "One row per component major: what it is, how big it is in millimetres",
        "(w × h × d), the standard it conforms to or the interface it presents or mates,",
        "how many devices seat it and how many other components compose it. A device",
        "seats a part when a placement or bay places it, a bay accepts it or a",
        "configuration puts it in one; naming it in prose does not count. Search this",
        "page before drawing a part; the [components README](README.md) says which",
        "namespace a new one belongs in.",
        "",
        "A `std/x` and a `common/x` with the same name are two layers rather than two",
        "copies: `std/` is the aperture, `common/` is the bezel, shell or nut around it and",
        "composes it. Place the wrapper when the panel carries that furniture and the",
        "aperture when it is a bare opening - never both at one position. The README's",
        "[Namespaces](README.md#namespaces) section has the pairs and the rule.",
        "",
    ]
    total = 0
    for ns in order:
        rows = groups[ns]
        total += len(rows)
        lines += [f"## {ns}/ ({len(rows)})", "",
                  "| ref | kind | class | size (mm) | conforms / interface | devices | in parts | what it is |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| `{r['ref']}` | {r['kind']} | {r['class']} | {r['size']} | {r['fits']} | {r['used']} | {r['parts']} | {r['what']} |")
        lines.append("")
    # after the opening paragraph, which ends at the first blank line
    lines[lines.index("", 2) + 1:lines.index("", 2) + 1] = [
        f"{total} component majors in {len(order)} namespaces.", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default="library")
    ap.add_argument("--out", help="write the page here (default: standard output)")
    args = ap.parse_args(argv)
    page = build(args.library)
    if args.out:
        Path(args.out).write_text(page, encoding="utf-8")
    else:
        sys.stdout.write(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
