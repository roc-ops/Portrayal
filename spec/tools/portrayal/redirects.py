#!/usr/bin/env python3
"""Redirects for a replaced part (#1049): `supersedes:` and its signature.

A rack file names parts by ref. When a major is removed, its ref stops
resolving, and a rack that names it quietly loses the part. The replacement
therefore says which removed refs it stands in for:

    supersedes:
      - ref: fibrain/xmn1021gb@1
        signature: sha256:<64 hex>
        from: <commit>

and the build publishes that list on the replacement's `components.json` entry
(`supersedes`, an empty list on every other row). The rack kit reads it
(kit/redirects.js) and follows an old ref to the new one.

THE SIGNATURE IS THE PROOF OF A DROP-IN. It is a hash of what a saved rack can
name on the part: its slots (id, interface, kind, media, bores, what each
accepts and holds by default), its bays, the ids of the parts it composes, the
directions of its faces, its fibre paths, its fields and its element names. It
leaves out everything a drop-in may change: where a port stands, a size, a
body, a description, which version of an adapter sits behind a part id and the
major of a face. It is recorded from the REMOVED part's published form, once,
and recomputed from the replacement at every build, so an edit that renames a
port, drops a slot or changes what it accepts fails the build instead of
turning a saved rack's swap into a different part.

`from` says where the recorded value came from: a commit whose tree still held
the removed part. `sign` below prints a signature from a `components.json`
built from that tree:

    git archive <commit> library spec/schemas | tar -x -C /tmp/old
    python -m portrayal.components_index --library /tmp/old/library --out /tmp/old/dist
    python -m portrayal.redirects sign /tmp/old/dist/components.json fibrain/xmn1021gb@1
"""
import argparse
import hashlib
import json
import sys

REF = r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*@[0-9]+$"


def ref_of(entry):
    """`ns/name@major` of a published entry."""
    return f"{entry['ns']}/{entry['name']}@{str(entry['major']).lstrip('v')}"


def _cage(c):
    return {"id": c.get("id"), "interface": c.get("interface"), "kind": c.get("kind"), "media": c.get("media"),
            "bores": list(c.get("bores") or []), "accepts": sorted(c.get("accepts") or []),
            "default": c.get("default")}


def _bay(b):
    # `accepts` is the PUBLISHED list, every ref the bay takes (manifest.offers);
    # a bay that states an `interface` signs it too, and one that states none
    # signs exactly what it always did
    b = b or {}
    return {"accepts": sorted(b.get("accepts") or []), "default": b.get("default"),
            **({"interface": b["interface"]} if b.get("interface") else {})}


def form(entry):
    """What a saved rack can name on a part, and nothing a drop-in may change."""
    cages = entry.get("cages")
    bays = entry.get("bays") or {}
    return {
        "kind": entry.get("kind"),
        "class": entry.get("class"),
        "cages": sorted((_cage(c) for c in cages if isinstance(c, dict)), key=lambda c: str(c["id"]))
        if isinstance(cages, list) else [],
        "bays": {k: _bay(v) for k, v in sorted(bays.items())} if isinstance(bays, dict) else {},
        "parts": sorted(str(p.get("id")) for p in entry.get("parts") or [] if isinstance(p, dict)),
        "faces": sorted((entry.get("faces") or {}).keys()),
        "optical": entry.get("optical") or None,
        "fields": sorted((entry.get("fields") or {}).keys()),
        "elements": sorted(entry.get("elements") or []),
    }


def signature(entry):
    """`sha256:<hex>` of a part's drop-in form."""
    text = json.dumps(form(entry), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def claims(entries):
    """[(old ref, replacement ref, claim)] for every `supersedes` published."""
    return [(c["ref"], ref_of(e), c) for e in entries for c in e.get("supersedes") or [] if isinstance(c, dict)]


def table(entries):
    """{removed ref: replacement ref}, as the kit reads it."""
    return {old: new for old, new, _ in claims(entries)}


def problems(entries):
    """Sentences for every redirect that does not hold, [] when all do.

    Each claim must name a ref nothing publishes any more, be made by one
    replacement only, be signed with what the replacement now publishes, and
    leave no loop.
    """
    live = {ref_of(e): e for e in entries}
    out, seen = [], {}
    for old, new, c in claims(entries):
        if old in live:
            out.append(f"{new} supersedes {old}, which is still in the library: a redirect is for a ref that is gone.")
        if old in seen and seen[old] != new:
            out.append(f"{old} is claimed by two replacements, {seen[old]} and {new}: a ref redirects to one part.")
        seen.setdefault(old, new)
        have = signature(live[new])
        if c.get("signature") != have:
            out.append(f"{new} is no longer a drop-in for {old}: its slots, part ids, faces or fibre paths differ from "
                       f"what {old} published (signature {have}, recorded {c.get('signature')}). Restore them, or "
                       f"remove the redirect and say in the changelog that {old} is gone.")
    step = {old: new for old, new in seen.items()}
    for start in sorted(step):
        at, trail = start, [start]
        while at in step:
            at = step[at]
            if at in trail:
                out.append(f"The redirects of {start} loop: {' -> '.join(trail + [at])}.")
                break
            trail.append(at)
        else:
            continue
        break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sign", help="print the signature of a published part")
    s.add_argument("components", help="a components.json built from the tree that held the part")
    s.add_argument("refs", nargs="+")
    args = ap.parse_args(argv)
    by_ref = {ref_of(e): e for e in json.load(open(args.components))["components"]}
    bad = 0
    for ref in args.refs:
        if ref not in by_ref:
            print(f"{ref}: not in {args.components}", file=sys.stderr)
            bad = 1
            continue
        print(f"{ref} {signature(by_ref[ref])}")
    return bad


if __name__ == "__main__":
    sys.exit(main())
