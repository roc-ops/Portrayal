#!/usr/bin/env python3
"""Pack a built dist into a few files per device, on request.

    dist_packs.py --dist library/dist --out <new folder> [--chunk-bytes N]

THE PUBLISHED DIST IS NOT CHANGED, and neither are the npm packages: this reads
a built dist and writes a folder of its own, which a caller replaces whole. It
refuses an `--out` that is inside the dist, holds it, or already holds files,
so a pack can never land in a published build and a stale one never survives.

One drawing is one file in a dist, which is right for a build and wrong for a
file server that limits the number of files. A pack holds many drawings as text:

- `devices/<device>.json` - `{"more": bool, "files": {<face file>: <svg text>}}`:
  every face the default configuration names in `<device>.configs.json`
  `configs[].files`. `more` says whether a second pack exists.
- `devices/<device>.more.json` - `{"files": {...}}`: every other face a
  configuration names. Written only for a device that has any.
- `components/<namespace>.<k>.json` - `{"files": {"components/<skin>": <svg text>}}`:
  one namespace's skins, cut greedily into chunks whose file is at most
  `--chunk-bytes` (1,000,000 by default), in byte order of the file name. `k`
  starts at 1. A skin larger than a chunk is a chunk by itself.
- `components/index.json` - `{<namespace>: [<first skin name of chunk 2>, ...]}`.
  A skin is in the chunk after the last name that is not greater than it, so a
  reader finds it by binary search. A namespace of one chunk holds `[]`.

Text only: `configs.json`, `source.json`, `.elements.json` and the library-wide
JSON are not packed, and a face no configuration names is in no pack. The same
dist always gives the same bytes. kit/dist.js `packedDist` and `fetchDist` read
the result.
"""
import argparse
import json
import sys
from pathlib import Path

CHUNK_BYTES = 1_000_000


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json(obj))


def _text(dist, name, owner):
    f = dist / name
    if not f.is_file():
        raise SystemExit(f"{owner}: configs.json names {name}, which the dist does not have")
    # bytes, not text mode: a carriage return must come back as it went in
    return f.read_bytes().decode("utf-8")


def device_packs(dist, name):
    """(default pack, more pack or None) for one device."""
    idx = json.loads((dist / f"{name}.configs.json").read_bytes())
    owner = f"{name}.configs.json"
    named = {c["name"]: set((c.get("files") or {}).values()) for c in idx["configs"]}
    default = named[idx["default"]]
    other = set().union(*named.values()) - default
    first = {f: _text(dist, f, owner) for f in sorted(default)}
    second = {f: _text(dist, f, owner) for f in sorted(other)}
    return ({"more": bool(second), "files": first}, {"files": second} if second else None)


def _entry_size(name, text):
    """Bytes one `"key":"text"` takes in a pack file."""
    return len(_json(name)) + 1 + len(_json(text))


def skin_chunks(skins, limit):
    """The names of `skins` (a {name: text} dict, sorted) cut greedily into runs
    whose pack file is at most `limit` bytes. A run takes the 12 bytes of
    `{"files":{}}`, each entry, and a comma between entries."""
    chunks, size = [], 0
    for name, text in skins.items():
        s = _entry_size(f"components/{name}", text)
        if chunks and size + 1 + s <= limit:
            chunks[-1].append(name)
            size += 1 + s
        else:
            chunks.append([name])
            size = len('{"files":{}}') + s
    return chunks


def build_packs(dist, out, chunk_bytes=CHUNK_BYTES):
    dist, out = Path(dist).resolve(), Path(out).resolve()
    if out == dist or dist in out.parents or out in dist.parents:
        raise SystemExit(f"--out {out} is inside the dist {dist} or holds it; "
                         "packs are not part of a published build")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise SystemExit(f"--out {out} already holds files; give a folder that does not exist")
    devices = sorted(p.name[:-len(".configs.json")] for p in dist.glob("*.configs.json"))
    if not devices:
        raise SystemExit(f"{dist} holds no <device>.configs.json: not a built dist")
    # read everything before writing anything, so a stop leaves no half a folder
    written = {}
    for name in devices:
        first, second = device_packs(dist, name)
        written[f"devices/{name}.json"] = first
        if second:
            written[f"devices/{name}.more.json"] = second
    by_ns = {}
    for p in sorted((dist / "components").glob("*.svg"), key=lambda p: p.name.encode()):
        ns, sep, _ = p.name.partition("--")
        if not sep or not ns:
            raise SystemExit(f"components/{p.name}: no namespace in the file name")
        by_ns.setdefault(ns, {})[p.name] = p.read_bytes().decode("utf-8")
    index = {}
    for ns, skins in sorted(by_ns.items()):
        chunks = skin_chunks(skins, chunk_bytes)
        index[ns] = [c[0] for c in chunks[1:]]
        for k, names in enumerate(chunks, 1):
            written[f"components/{ns}.{k}.json"] = {"files": {f"components/{n}": skins[n] for n in names}}
    written["components/index.json"] = index
    for rel, obj in written.items():
        _dump(out / rel, obj)
    return sorted(written)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", required=True, help="a built dist (library/dist)")
    ap.add_argument("--out", required=True, help="a folder that does not exist yet, outside the dist")
    ap.add_argument("--chunk-bytes", type=int, default=CHUNK_BYTES,
                    help="most bytes in one skin chunk's file (default %(default)s)")
    args = ap.parse_args(argv)
    names = build_packs(args.dist, args.out, args.chunk_bytes)
    print(f"wrote {len(names)} packs to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
