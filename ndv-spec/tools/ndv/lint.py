#!/usr/bin/env python3
"""NDV linter v0: schema validation + contract<->skin consistency + ID grammar.

Checks (per FritzingCheckPart lesson — ID sync fails without a linter):
  L1 schema: every YAML validates against its schema
  L2 grammar: every id/segment matches ^[a-z0-9]+(-[a-z0-9]+)*$ and contains no '--'
  L3 skin: every contracted element id exists in every declared skin SVG
  L4 skin: skin viewBox matches contract size
  L5 device: placement refs resolve in the library path; instance ids unique per view
  L6 device: bay defaults appear in the bay's accepts list
  L7 device: region members reference existing instance ids
  L9 component: conforms-declared size matches schemas/standards.yaml
  L10 component: parts resolve, ids unique, no composition cycles (depth <= 4)
  L11 mating: interface/mates need a `mate` point; a wrapper cannot lose or
      change the interface of the receptacle it composes
  L12 device: mate-to resolves, host is a receptacle, and the interfaces match
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SEGMENT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ERRORS = []


def err(path, code, msg):
    ERRORS.append(f"{path}: [{code}] {msg}")


def check_segment(path, code, value):
    if not SEGMENT.match(value) or "--" in value:
        err(path, code, f"bad id segment {value!r}")


def load_schema(schemas_dir, name):
    with open(schemas_dir / name) as f:
        return Draft202012Validator(json.load(f))


def skin_ids(svg_path):
    root = ET.parse(svg_path).getroot()
    return {n.get("id") for n in root.iter() if n.get("id")}, root


STANDARDS = {}


def lint_component(path, validator):
    # same guard as lint_device - a component can break on a colon in a plain
    # scalar just as easily, and an unhandled ScannerError is a traceback rather
    # than a message that tells you which line to look at
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        err(path, "L0", f"will not parse: {str(exc).splitlines()[0]}")
        scalar_colon_hint(path, exc)
        return None
    for e in validator.iter_errors(data):
        err(path, "L1", f"{'/'.join(str(p) for p in e.path)}: {e.message}")
        return data
    check_segment(path, "L2", data["name"])
    for el in (data.get("elements") or {}):
        check_segment(path, "L2", el)
    conf = data.get("conforms")
    if conf:
        std = STANDARDS.get(conf)
        if std is None:
            err(path, "L9", f"conforms: unknown standards key {conf!r}")
        else:
            sz = data["size"]
            if abs(sz["w"] - std["w"]) > 0.05 or abs(sz["h"] - std["h"]) > 0.05:
                err(path, "L9", f"conforms {conf}: size {sz['w']}x{sz['h']} != registry {std['w']}x{std['h']} ({std['registry']})")
            if sz.get("d") is not None and std.get("depth") is not None \
                    and abs(sz["d"] - std["depth"]) > 0.05:
                err(path, "L9", f"conforms {conf}: depth {sz['d']} != registry {std['depth']} ({std['registry']})")
            # aperture vs cavity: registry cavity means the opening steps in, so the
            # component must declare the recess cross-section and a node drawing it
            cav = std.get("cavity")
            if cav:
                rel = data.get("relief") or {}
                rsz = rel.get("size")
                if rsz is None:
                    err(path, "L9", f"conforms {conf}: registry defines a cavity "
                        f"{cav['w']}x{cav['h']} - component must declare relief.size")
                elif abs(rsz["w"] - cav["w"]) > 0.05 or abs(rsz["h"] - cav["h"]) > 0.05:
                    err(path, "L9", f"conforms {conf}: relief.size {rsz['w']}x{rsz['h']} "
                        f"!= registry cavity {cav['w']}x{cav['h']} ({std['registry']})")
                if rsz is not None and not rel.get("cavity"):
                    err(path, "L9", f"conforms {conf}: relief.size set without relief.cavity "
                        "- name the skin node whose art is the recess silhouette")
                if rsz is not None and (rsz["w"] > sz["w"] + 0.05 or rsz["h"] > sz["h"] + 0.05):
                    err(path, "L9", f"conforms {conf}: cavity {rsz['w']}x{rsz['h']} "
                        f"exceeds aperture {sz['w']}x{sz['h']}")
    return data


def resolve_component(ref, lib_roots):
    """Locate a component contract from a `ns/name@major` ref."""
    nsname, major = ref.rsplit("@", 1)
    for r in lib_roots:
        c = Path(r) / "components" / nsname / f"v{major}" / "contract.yaml"
        if c.exists():
            return c
    return None


def lint_component_mating(path, data, lib_roots):
    """L11: mating declarations must be usable and must survive composition."""
    cps = data.get("connection-points") or {}
    for key in ("interface", "mates"):
        if data.get(key) and "mate" not in cps:
            err(path, "L11", f"{key}: {data[key]!r} declared but no 'mate' "
                             "connection-point - nothing to align to")
    # a wrapper may re-present the interface of a receptacle it composes, but it
    # must not present a DIFFERENT one - a plug would mate with the wrapper and
    # land on the wrong geometry
    for part in data.get("parts") or []:
        found = resolve_component(part["ref"], lib_roots)
        if not found:
            continue
        sub = yaml.safe_load(found.read_text())
        sub_if = sub.get("interface")
        if not sub_if:
            continue
        # declaring none is fine - a PSU composes an inlet without presenting one
        # at its own origin. Contradicting it is not.
        if data.get("interface") and data["interface"] != sub_if:
            err(path, "L11", f"declares interface {data['interface']!r} but composes "
                             f"{part['ref']} presenting {sub_if!r}")


def lint_component_parts(path, data, lib_roots, depth=0, seen=None):
    seen = seen or set()
    key = f"{data.get('name')}@{data.get('version','')}"
    if depth > 4:
        err(path, "L10", "composition depth exceeds 4 (cycle?)")
        return
    ids = set()
    for part in data.get("parts") or []:
        if part["id"] in ids:
            err(path, "L10", f"duplicate part id {part['id']}")
        ids.add(part["id"])
        nsname, major = part["ref"].rsplit("@", 1)
        found = None
        for r in lib_roots:
            c = Path(r) / "components" / nsname / f"v{major}" / "contract.yaml"
            if c.exists():
                found = c
                break
        if not found:
            err(path, "L10", f"unresolvable part ref {part['ref']}")
            continue
        sub = yaml.safe_load(found.read_text())
        if part["ref"] in seen:
            err(path, "L10", f"composition cycle via {part['ref']}")
            continue
        lint_component_parts(found, sub, lib_roots, depth + 1, seen | {part["ref"]})


def _skin_checks(path, data):
    skins_dir = path.parent / "skins"
    contracted = set((data.get("elements") or {}).keys())
    for skin in data.get("skins", ["default"]):
        sp = skins_dir / f"{skin}.svg"
        if not sp.exists():
            err(path, "L3", f"declared skin missing: {sp.name}")
            continue
        ids, root = skin_ids(sp)
        missing = contracted - ids
        if missing:
            err(sp, "L3", f"skin lacks contracted element ids: {sorted(missing)}")
        relief = data.get("relief") or {}
        rnodes = [relief["cavity"]] if relief.get("cavity") else []
        rnodes += [ft["node"] for ft in relief.get("features") or []]
        rmissing = set(rnodes) - ids
        if rmissing:
            err(sp, "L11", f"skin lacks relief node ids: {sorted(rmissing)}")
        vb = (root.get("viewBox") or "").split()
        size = data["size"]
        if len(vb) == 4 and (float(vb[2]) != size["w"] or float(vb[3]) != size["h"]):
            err(sp, "L4", f"viewBox {vb} != contract size {size['w']}x{size['h']}")
    return data


def lint_device_mating(path, view_name, view, lib_roots):
    """L12: mate-to must resolve, and the two sides must agree on the interface."""
    by_id = {p["id"]: p for p in (view.get("placements") or [])}
    for p in view.get("placements") or []:
        target = p.get("mate-to")
        if not target:
            continue
        host = by_id.get(target)
        if host is None:
            err(path, "L12", f"{view_name}/{p['id']}: mate-to {target!r} is not a "
                             "placement in this view")
            continue
        if not host.get("at"):
            err(path, "L12", f"{view_name}/{p['id']}: mate-to {target!r} has no "
                             "explicit position (occupants cannot host occupants)")
            continue
        hp, op = resolve_component(host["ref"], lib_roots), resolve_component(p["ref"], lib_roots)
        if not hp or not op:
            continue
        hc, oc = yaml.safe_load(hp.read_text()), yaml.safe_load(op.read_text())
        want, have = hc.get("interface"), oc.get("mates")
        if not have:
            err(path, "L12", f"{view_name}/{p['id']}: {p['ref']} declares no 'mates', "
                             "so it cannot occupy anything")
        if not want:
            err(path, "L12", f"{view_name}/{p['id']}: host {host['ref']} presents no "
                             "'interface', so nothing can mate into it")
        if want and have and want != have:
            err(path, "L12", f"{view_name}/{p['id']}: {p['ref']} mates {have!r} but "
                             f"{host['ref']} presents {want!r}")


def lint_device_overlap(path, view_name, view, lib_roots):
    """L13: two placed components must not occupy the same faceplate area.

    Overlap is almost always a sizing mistake rather than a drawing choice: a
    part measured off one device dropped into a tighter gap on another. It is
    invisible in the flat SVG (the later node just paints over the earlier one)
    but obvious in 3D, where an LED dome hangs over the lip of a port cavity.

    Occupants are exempt - a transceiver placed with mate-to is *supposed* to
    sit inside its host's aperture.
    """
    boxes = []
    for p in view.get("placements") or []:
        if not p.get("at") or p.get("mate-to"):
            continue
        cp = resolve_component(p["ref"], lib_roots)
        if not cp:
            continue
        sz = (yaml.safe_load(cp.read_text()) or {}).get("size") or {}
        if "w" not in sz or "h" not in sz:
            continue
        w, h = sz["w"], sz["h"]
        x, y = p["at"][0], p["at"][1]
        # a quarter-turn swaps the footprint about the component centre - the same
        # transform render.py applies when it computes view extents
        if p.get("rotate") in (90, 270, -90):
            cx, cy = x + w / 2, y + h / 2
            x, y, w, h = cx - h / 2, cy - w / 2, h, w
        boxes.append((p["id"], x, y, w, h))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            ox = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
            oy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
            if ox > 1e-3 and oy > 1e-3:
                err(path, "L13", f"{view_name}: {a[0]} and {b[0]} overlap by "
                                 f"{ox:.2f}x{oy:.2f}mm")


def scalar_colon_hint(path, exc):
    """A colon-space inside an unquoted scalar is the commonest way these break.

    `notes: measured from a photo: about 3mm` parses as a nested mapping and the
    error PyYAML gives says nothing about why. Point at the offending line, since
    this has cost several builds.
    """
    mark = getattr(exc, "problem_mark", None)
    if mark is None:
        return
    try:
        line = path.read_text().splitlines()[mark.line]
    except IndexError:
        return
    stripped = line.strip()
    # a second ": " on the line is the tell - the first is the key, the rest is
    # prose that PyYAML then tries to read as a nested mapping
    if stripped.count(": ") > 1 and not stripped.startswith("#"):
        err(path, "L0", f"line {mark.line + 1}: a colon inside an unquoted scalar - "
                        f"rephrase or quote it: {stripped[:70]!r}")


def lint_device(path, validator, lib_roots):
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        err(path, "L0", f"will not parse: {str(exc).splitlines()[0]}")
        scalar_colon_hint(path, exc)
        return None
    for e in validator.iter_errors(data):
        err(path, "L1", f"{'/'.join(str(p) for p in e.path)}: {e.message}")
        return data

    def resolve(ref):
        nsname, major = ref.rsplit("@", 1)
        return any((Path(r) / "components" / nsname / f"v{major}" / "contract.yaml").exists()
                   for r in lib_roots)

    for vname, view in (data.get("views") or {}).items():
        view = view or {}
        lint_device_mating(path, vname, view, lib_roots)
        lint_device_overlap(path, vname, view, lib_roots)
        seen = set()
        for p in view.get("placements", []) or []:
            check_segment(path, "L2", p["id"])
            if p["id"] in seen:
                err(path, "L5", f"duplicate instance id {p['id']} in view {vname}")
            seen.add(p["id"])
            if not resolve(p["ref"]):
                err(path, "L5", f"unresolvable ref {p['ref']} ({p['id']})")
        for b in view.get("bays", []) or []:
            check_segment(path, "L2", b["id"])
            if b["id"] in seen:
                err(path, "L5", f"duplicate instance id {b['id']} in view {vname}")
            seen.add(b["id"])
            for acc in b["accepts"]:
                if not resolve(acc):
                    err(path, "L5", f"unresolvable accepts ref {acc} ({b['id']})")
            if b.get("default") and b["default"] not in b["accepts"]:
                err(path, "L6", f"bay {b['id']} default {b['default']} not in accepts")
        for r in view.get("regions", []) or []:
            check_segment(path, "L2", r["id"])
            for m in r.get("members", []) or []:
                if m not in seen:
                    err(path, "L7", f"region {r['id']} member {m} is not an instance in view {vname}")
    bay_accepts = {}
    for view in (data.get("views") or {}).values():
        for b in (view or {}).get("bays", []) or []:
            bay_accepts[b["id"]] = b["accepts"]
    for cname, cfg in (data.get("configurations") or {}).items():
        for bid, ref in (cfg.get("bays") or {}).items():
            if bid not in bay_accepts:
                err(path, "L8", f"config {cname}: unknown bay {bid}")
            elif ref not in bay_accepts[bid]:
                err(path, "L8", f"config {cname}: bay {bid} ref {ref} not in accepts")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemas", required=True)
    ap.add_argument("--library", action="append", required=True)
    args = ap.parse_args()
    schemas = Path(args.schemas)
    std_file = schemas / "standards.yaml"
    if std_file.exists():
        STANDARDS.update(yaml.safe_load(std_file.read_text())["standards"])
    comp_v = load_schema(schemas, "component.schema.json")
    dev_v = load_schema(schemas, "device.schema.json")
    ovl_v = load_schema(schemas, "overlay.schema.json")

    n = 0
    for root in args.library:
        root = Path(root)
        for f in sorted(root.glob("components/**/contract.yaml")):
            d = lint_component(f, comp_v)
            # a file that would not parse has already been reported; running the
            # rest against None just buries that message under a traceback
            if d is not None:
                _skin_checks(f, d)
                lint_component_parts(f, d, args.library)
                lint_component_mating(f, d, args.library)
            n += 1
        for f in sorted(root.glob("devices/**/device.yaml")):
            lint_device(f, dev_v, args.library); n += 1
        for f in sorted(root.glob("devices/**/overlays/*.yaml")):
            data = yaml.safe_load(f.read_text())
            for e in ovl_v.iter_errors(data):
                err(f, "L1", f"{'/'.join(str(p) for p in e.path)}: {e.message}")
            n += 1

    if ERRORS:
        print(f"LINT: {len(ERRORS)} error(s) across {n} file(s)")
        for e in ERRORS:
            print(f"  {e}")
        sys.exit(1)
    print(f"LINT: ok ({n} files)")


if __name__ == "__main__":
    main()
