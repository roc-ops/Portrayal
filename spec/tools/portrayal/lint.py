#!/usr/bin/env python3
"""Portrayal linter v0: schema validation + contract<->skin consistency + ID grammar.

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

from manifest import (view_parts, targets, VIEW_KEY_ORDER,
                      PANEL_KEY_ORDER, COMPONENT_KEY_ORDER)
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


def _instance_size(ref, lib_roots):
    """(w, h) of a component, or None when it cannot be resolved."""
    if not ref:
        return None
    c = resolve_component(ref, lib_roots)          # returns a PATH, not the document
    if c is None:
        return None
    try:
        d = yaml.safe_load(c.read_text()) or {}
    except yaml.YAMLError:
        return None
    sz = d.get("size")
    return (sz["w"], sz["h"]) if sz else None


def lint_device_mating(path, view_name, view, lib_roots):
    """L12: mate-to must resolve, and the two sides must agree on the interface."""
    placements = view_parts(view)["placements"]
    by_id = {p["id"]: p for p in placements}
    for p in placements:
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
    parts_ = view_parts(view)["placements"]
    # An indicator that DECLARES it belongs to a part may sit on it: an LED in a
    # jack's bezel overlaps the jack by construction. `for:` is the declaration,
    # so honour it here the same way mate-to is honoured.
    owned = {p["id"]: set(targets(p.get("for"))) for p in parts_}
    for p in parts_:
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
                if b[0] in owned.get(a[0], ()) or a[0] in owned.get(b[0], ()):
                    continue
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

    declared_groups = set((data.get("groups") or {}).keys())
    for vname, view in (data.get("views") or {}).items():
        view = view or {}
        # L16 - a view is written in the order the part is made. Not a style
        # preference: an agent building a device follows this order stage by stage,
        # and a file that reads in a different order teaches the wrong procedure.
        for keys, order, where in ((list(view.keys()), VIEW_KEY_ORDER, vname),
                                   (list((view.get("panel") or {}).keys()), PANEL_KEY_ORDER, f"{vname}/panel"),
                                   (list((view.get("components") or {}).keys()), COMPONENT_KEY_ORDER, f"{vname}/components")):
            present = [k for k in order if k in keys]
            if [k for k in keys if k in order] != present:
                err(path, "L16", f"{where}: keys must read {' > '.join(present)} "
                                 f"(manufacturing order), not {' > '.join(k for k in keys if k in order)}")
        lint_device_mating(path, vname, view, lib_roots)
        lint_device_overlap(path, vname, view, lib_roots)
        vp = view_parts(view)
        seen = set()
        # L17 - every group used is declared. The declaration carries the vendor's
        # word and the numbering origin; a group that is only a string has neither.
        for item in vp["placements"] + vp["bays"]:
            g = item.get("group")
            if g and g not in declared_groups:
                err(path, "L17", f"{vname}/{item['id']}: group {g!r} is not declared "
                                 "under top-level groups:")
        for p in vp["placements"]:
            check_segment(path, "L2", p["id"])
            if p["id"] in seen:
                err(path, "L5", f"duplicate instance id {p['id']} in view {vname}")
            seen.add(p["id"])
            if not resolve(p["ref"]):
                err(path, "L5", f"unresolvable ref {p['ref']} ({p['id']})")
        for b in vp["bays"]:
            check_segment(path, "L2", b["id"])
            if b["id"] in seen:
                err(path, "L5", f"duplicate instance id {b['id']} in view {vname}")
            seen.add(b["id"])
            for acc in b["accepts"]:
                if not resolve(acc):
                    err(path, "L5", f"unresolvable accepts ref {acc} ({b['id']})")
            if b.get("default") and b["default"] not in b["accepts"]:
                err(path, "L6", f"bay {b['id']} default {b['default']} not in accepts")
        for r in vp["regions"]:
            check_segment(path, "L2", r["id"])
            for m in r.get("members", []) or []:
                if m not in seen:
                    err(path, "L7", f"region {r['id']} member {m} is not an instance in view {vname}")
        # L14 - `for:` must name a placement or bay that exists in this view, and
        # the thing carrying it must sit near it. Same field, same rule, whether the
        # carrier is a silkscreen legend, an LED or a bay: "belongs to / annotates".
        # A legend or indicator on the far side of the chassis from its target is
        # the failure this catches; it is invisible in YAML and obvious drawn.
        boxes = {}
        for p in vp["placements"]:
            c = _instance_size(p.get("ref"), lib_roots)
            if c and p.get("at"):
                boxes[p["id"]] = (p["at"], c, p.get("rotate"))
        for b in vp["bays"]:
            boxes[b["id"]] = (b["at"], (b["size"]["w"], b["size"]["h"]), b.get("rotate"))

        def footprint(owner):
            (ax, ay), (bw, bh), rot = boxes[owner]
            if rot in (90, 270, -90):
                d = (bw - bh) / 2.0
                ax, ay, bw, bh = ax + d, ay - d, bh, bw
            return ax, ay, bw, bh

        def check_for(kind, ident, at, value):
            names = targets(value)
            known = []
            for owner in names:
                if owner not in seen:
                    err(path, "L14", f"{vname}: {kind} {ident!r} is for {owner!r}, "
                                     "which is not a placement or bay in this view")
                elif owner in boxes:
                    known.append(owner)
            if not known or not at:
                return
            # A mark naming SEVERAL things is tested against the region they span,
            # not against each one alone. A "0/1" legend under a stacked pair, or a
            # leader line from a breaker to its terminal, is necessarily far from at
            # least one end - that is what joining two things means.
            fps = [footprint(o) for o in known]
            ax = min(f[0] for f in fps); ay = min(f[1] for f in fps)
            bw = max(f[0] + f[2] for f in fps) - ax
            bh = max(f[1] + f[3] for f in fps) - ay
            mx, my = at
            # Inside that region, or within one region-dimension of it. The floor of
            # 20mm is what makes this usable on real hardware: indicators and legends
            # are grouped, so a column's LEDs often sit above the TOP port and serve
            # the bottom one 18mm away, and a legend beside a 2mm lamp is necessarily
            # further off than 2mm. 20mm is generous for light-pipe and silkscreen
            # practice while still an order of magnitude below "somewhere else on the
            # panel", which is the mistake this rule exists to catch.
            tx, ty = max(bw, 20.0), max(bh, 20.0)
            if mx < ax - tx or mx > ax + bw + tx or my < ay - ty or my > ay + bh + ty:
                err(path, "L14", f"{vname}: {kind} {ident!r} at ({mx:g}, {my:g}) is "
                                 f"for {', '.join(known)} but sits well outside "
                                 f"({ax:g}, {ay:g} {bw:g}x{bh:g})")

        for m in vp["silkscreen"]:
            if m.get("id"):
                check_segment(path, "L2", m["id"])
            check_for("silkscreen", m.get("text") or m.get("id") or "path", m["at"], m.get("for"))
        for p in vp["placements"]:
            check_for("placement", p["id"], p.get("at"), p.get("for"))
        for b in vp["bays"]:
            check_for("bay", b["id"], b.get("at"), b.get("for"))
    # L15 - the conformance gate. A device declares how far it has been taken and
    # lint holds it to that standard, so work in progress can be committed without
    # fighting the linter while a device that CLAIMS to be verified has to earn it.
    maturity = data.get("maturity", "draft")
    if maturity in ("modelled", "verified"):
        prov = data.get("provenance") or {}
        if not prov:
            err(path, "L15", f"maturity {maturity}: no provenance block. A device at this "
                             "level must cite where its numbers came from")
        else:
            joined = " ".join(str(v) for v in prov.values()).lower()
            if not any(k in joined for k in ("datasheet", "installation guide",
                                             "hardware guide", "install guide", "manual")):
                err(path, "L15", f"maturity {maturity}: provenance cites no datasheet or "
                                 "hardware guide. If there genuinely is no document, say so "
                                 "explicitly in provenance and drop to draft")
        for key in ("width", "height", "depth"):
            if key in (data.get("chassis") or {}) and not prov:
                break
    if maturity == "verified":
        # verified has to hold for the whole assembly, not just the chassis manifest.
        # A device that places a component whose dimensions are guessed is not verified,
        # however carefully the chassis itself was measured.
        def estimated_keys(doc):
            return sorted(k for k, v in (doc.get("provenance") or {}).items()
                          if str(v).lstrip().lower().startswith("estimated"))
        est = estimated_keys(data)
        if est:
            err(path, "L15", f"maturity verified: {len(est)} estimated value(s) on the device "
                             f"({', '.join(est[:4])}) - verified means measured, not guessed")
        refs = set()
        for view in (data.get("views") or {}).values():
            vp_ = view_parts(view)
            for q in vp_["placements"]:
                refs.add(q["ref"])
            for b in vp_["bays"]:
                refs.update(b.get("accepts") or [])
        for ref in sorted(refs):
            c = resolve_component(ref, lib_roots)
            if c is None:
                continue
            try:
                cd = yaml.safe_load(c.read_text()) or {}
            except yaml.YAMLError:
                continue
            ce = estimated_keys(cd)
            if ce:
                err(path, "L15", f"maturity verified: component {ref} has estimated "
                                 f"{', '.join(ce)} - a verified device cannot be built "
                                 "from guessed parts")

    bay_accepts = {}
    for view in (data.get("views") or {}).values():
        for b in view_parts(view)["bays"]:
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
