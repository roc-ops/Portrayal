"""THE SITE FILE CHECKER: what JSON Schema cannot say about a `portrayal-site` file.

The schema (`spec/schemas/site.schema.json`) gives the shape. These rules of
docs/site-file-design.md are not shapes, and are checked here:

  - a placed rack's `file` is normalised, stays inside the site's folder, and
    is compared normalised;
  - a pathway segment has two different nodes at its ends;
  - every `id`, and every `guid`, is unique across the whole file;
  - every id a file names (a wall, a node, a rack placement, a placed device,
    a point outside the site, an item in a placed rack) is there;
  - a cable is stored at the LOWEST LEVEL THAT HOLDS BOTH ITS ENDS: two ends in
    one rack belong in that rack's file, two in one space in the space, two in
    one building in the building, and anything else on the site.

`read` is the version 0 reader rule: a newer version is refused whole, naming
both versions, before any of it is read.

These are plain functions over a parsed document, so the kit can mirror them
one for one. A placed rack file is opened for reading only, and never written.
"""
import argparse
import json
import posixpath
import re
import sys
from pathlib import Path

import jsonschema

FORMAT = "portrayal-site"
VERSION = 0
SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "site.schema.json"


class SiteVersionError(ValueError):
    """A site file newer than this reader."""


def refuse_newer(doc):
    """Refuse a document that is not a site file, or is newer than VERSION."""
    fmt = doc.get("format") if isinstance(doc, dict) else None
    if fmt != FORMAT:
        raise ValueError(f"This is not a site file: its format is {fmt!r}, not {FORMAT!r}.")
    v = doc.get("version")
    if isinstance(v, int) and not isinstance(v, bool) and v > VERSION:
        raise SiteVersionError(
            f"This site file is version {v}; this reader supports up to version {VERSION}.")


def read(path):
    """The document at `path`, refused whole if it is not one this reader reads."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    refuse_newer(doc)
    return doc


def _schema_findings(doc):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc),
                  key=lambda e: list(map(str, e.absolute_path)))
    return [f"/{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in errs]


def _walk_ids(node, where, ids, guids):
    """Every id and guid in the file, with where each was seen. An extension
    block is someone else's data, and its keys are not this file's ids."""
    if isinstance(node, dict):
        if isinstance(node.get("id"), str):
            ids.setdefault(node["id"], []).append(where)
        if isinstance(node.get("guid"), str):
            guids.setdefault(node["guid"], []).append(where)
        for k, v in node.items():
            if k != "ext":
                _walk_ids(v, f"{where}/{k}", ids, guids)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_ids(v, f"{where}/{i}", ids, guids)


def _inside(file):
    """`file` normalised (`.` and `..` folded, `/` as the separator), or None when
    it is absolute or resolves outside the site folder."""
    text = file.replace("\\", "/")
    if text.startswith("/") or re.match(r"[A-Za-z]:", text):
        return None
    norm = posixpath.normpath(text)
    if norm == ".." or norm.startswith("../"):
        return None
    return norm


def _rack_items(path, rack_id, cache):
    """The item ids of rack `rack_id` in the rack file at `path`, or None when the
    file or the rack is not there. Read as bytes, and never written."""
    if path not in cache:
        try:
            with open(path, "rb") as f:
                cache[path] = json.loads(f.read())
        except (OSError, ValueError):
            cache[path] = None
    doc = cache[path]
    for rack in (doc or {}).get("racks") or []:
        if isinstance(rack, dict) and rack.get("id") == rack_id:
            return {i.get("id") for i in rack.get("items") or [] if isinstance(i, dict)}
    return None


def check(doc, base=None):
    """Every finding for `doc`, as sentences; an empty list is a good file.

    `base` is the folder the file is in. Given it, each placed rack file is
    read, and a rack end's item is checked against it."""
    found = _schema_findings(doc)
    if found:
        return found        # the rules below read the shape the schema just refused

    ids, guids = {}, {}
    _walk_ids(doc, "", ids, guids)
    for kind, seen in (("id", ids), ("guid", guids)):
        for value, where in seen.items():
            if len(where) > 1:
                found.append(f"The {kind} {value} is used twice or more: at {', '.join(where)}.")

    site = doc["site"]
    # Where each thing is: its space, building or site.
    space_of, building_of = {}, {}         # placed thing -> space id; space -> building id
    walls, floors_of, nodes_of = {}, {}, {}
    placements, cables = {}, []            # placement id -> (space, file, rack); (cable, level)
    points = {p["id"] for p in site.get("points", [])}
    cables += [(c, ("site", site["id"])) for c in site.get("cables", [])]
    for b in site["buildings"]:
        bid = b["id"]
        cables += [(c, ("building", bid)) for c in b.get("cables", [])]
        for fl in b["floors"]:
            floors_of.setdefault(bid, set()).add(fl["id"])
            for sp in fl["spaces"]:
                sid = sp["id"]
                building_of[sid] = bid
                walls[sid] = {w["id"] for w in sp.get("walls", [])}
                cables += [(c, ("space", sid)) for c in sp.get("cables", [])]
                for r in sp.get("racks", []):
                    placements[r["id"]] = (sid, r["file"], r["rack"])
                    space_of[r["id"]] = sid
                for s in sp.get("surfaces", []):
                    if s["wall"] not in walls[sid]:
                        found.append(f"Surface {s['id']} is on wall {s['wall']}, which space {sid} does not have.")
                    for d in s["devices"]:
                        space_of[d["id"]] = sid
                for d in sp.get("devices", []):
                    space_of[d["id"]] = sid
                    if "wall" in d and d["wall"] not in walls[sid]:
                        found.append(f"Device {d['id']} is on wall {d['wall']}, which space {sid} does not have.")
        paths = b.get("pathways") or {}
        nodes_of[bid] = {n["id"] for n in paths.get("nodes", [])}
        for n in paths.get("nodes", []):
            if n["floor"] not in floors_of.get(bid, set()):
                found.append(f"Pathway node {n['id']} is on floor {n['floor']}, which building {bid} does not have.")
        for s in paths.get("segments", []):
            if s["a"] == s["b"]:
                found.append(f"Pathway segment {s['id']} has node {s['a']} at both ends; a segment runs between two nodes.")
            for e in ("a", "b"):
                if s[e] not in nodes_of[bid]:
                    found.append(f"Pathway segment {s['id']} ends at node {s[e]}, which building {bid} does not have.")

    # Each rack is placed once, and each placed rack is in its file.
    racks_cache, placed, items = {}, {}, {}
    for pid, (sid, written, rack) in placements.items():
        file = _inside(written)
        if file is None:
            found.append(f"Rack {pid} places a rack file at {written}, which is outside the site folder; "
                         "a placed rack file is a relative path that stays inside it.")
            continue
        placements[pid] = (sid, file, rack)
        key = (file, rack)
        if key in placed:
            found.append(f"Racks {placed[key]} and {pid} both place rack {rack} of {file}; a rack stands in one place.")
        placed[key] = pid
        if base is not None:
            got = _rack_items(str(Path(base) / file), rack, racks_cache)
            if got is None:
                found.append(f"Rack {pid} places rack {rack} of {file}, and that file has no such rack or cannot be read.")
            items[pid] = got

    def level(end, cid, side):
        """(rack placement, space, building) of an end, or None when it names
        nothing in this file. A point outside the site has none of them."""
        if "rack" in end:
            pid = end["rack"]
            if pid not in placements:
                found.append(f"Cable {cid} end {side} names rack {pid}, which this file does not place.")
                return None
            got = items.get(pid)
            if got is not None and end["item"] not in got:
                _, file, rack = placements[pid]
                found.append(f"Cable {cid} end {side} names item {end['item']}, which rack {rack} of {file} does not have.")
                return None
            sid = space_of[pid]
            return (pid, sid, building_of[sid])
        if "device" in end:
            did = end["device"]
            if did not in space_of or did in placements:
                found.append(f"Cable {cid} end {side} names device {did}, which this file does not place.")
                return None
            sid = space_of[did]
            return (None, sid, building_of[sid])
        if end["point"] not in points:
            found.append(f"Cable {cid} end {side} names point {end['point']}, which the site does not list.")
            return None
        return (None, None, None)

    for cable, (where, at) in cables:
        cid = cable["id"]
        a, b = level(cable["a"], cid, "a"), level(cable["b"], cid, "b")
        if a is None or b is None:
            continue
        if a[0] is not None and a[0] == b[0]:
            found.append(f"Cable {cid} has both ends in rack {a[0]}; it belongs in that rack's rack file, "
                         f"not in {where} {at}.")
            continue
        if a[1] is not None and a[1] == b[1]:
            lowest = ("space", a[1])
        elif a[2] is not None and a[2] == b[2]:
            lowest = ("building", a[2])
        else:
            lowest = ("site", site["id"])
        if lowest != (where, at):
            found.append(f"Cable {cid} is stored in {where} {at} and belongs in {lowest[0]} {lowest[1]}, "
                         "the lowest level that holds both its ends.")
    return found


def check_file(path):
    """`read`, then `check` with the placed rack files read beside it."""
    return check(read(path), base=Path(path).resolve().parent)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Check a portrayal-site file: its schema, unique ids and "
                                             "GUIDs, references, and where each cable is stored.")
    ap.add_argument("site_file", help="the site file to check; the rack files it places are read beside it")
    args = ap.parse_args()
    try:
        problems = check_file(args.site_file)
    except (OSError, ValueError) as e:
        sys.exit(str(e))
    print("\n".join(problems) or "ok")
    sys.exit(1 if problems else 0)
