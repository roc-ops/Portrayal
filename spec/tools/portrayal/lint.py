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
  L20 states: a state name is a token - prose belongs in `description`
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from manifest import (view_parts, targets, split_target, VIEW_KEY_ORDER,
                      PANEL_KEY_ORDER, COMPONENT_KEY_ORDER)
from jsonschema import Draft202012Validator

SEGMENT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# The same test the Explorer applies before it will build state chips. A state
# name is one half of a CSS class - `state-<name>` is what the compiled drawing
# paints on - so anything that is not a token is a class nothing styles.
STATE_TOKEN = re.compile(r"^[a-z0-9-]+$")
# Solid, on and off, or flashing between two colours. Rate is not here yet -
# see the note on `behavior` in the schema.
STATE_BEHAVIORS = {"solid", "blinking", "alternating"}
ERRORS = []
WARNINGS = []


def err(path, code, msg):
    ERRORS.append(f"{path}: [{code}] {msg}")


def warn(path, code, msg):
    """A rule the portfolio does not satisfy yet.

    A rule that goes red across every device on the day it lands teaches people
    to ignore the linter. A warning states the debt, keeps the count visible,
    and gets promoted to err() once the sweep is done.
    """
    WARNINGS.append(f"{path}: [{code}] {msg}")


# A cage whose media token names a FAMILY rather than a specific media. One
# component serves all of them because the mechanicals are identical, so the
# component's own attrs can never resolve which. Anything not listed here
# answers for itself - an RJ45 is an RJ45.
AMBIGUOUS_MEDIA = {"sfp", "qsfp"}

_CLASS_CACHE = {}
_ATTRS_CACHE = {}
_ELEMENTS_CACHE = {}
_SIZE_CACHE = {}


def contract_class(ref, lib_roots):
    """The `class` a component declares, or None. Cached - L18/L19 ask per
    placement, and a 188-placement device would otherwise re-read one contract
    188 times."""
    if ref in _CLASS_CACHE:
        return _CLASS_CACHE[ref]
    nsname, major = ref.rsplit("@", 1)
    cls = None
    for r in lib_roots:
        f = Path(r) / "components" / nsname / f"v{major}" / "contract.yaml"
        if f.exists():
            cls = (yaml.safe_load(f.read_text()) or {}).get("class")
            break
    _CLASS_CACHE[ref] = cls
    return cls


def contract_size(ref, lib_roots):
    """The `size` a component declares, or None. Cached alongside class and attrs -
    L21 asks per placement and a 248-placement view would re-read otherwise."""
    if ref in _SIZE_CACHE:
        return _SIZE_CACHE[ref]
    try:
        nsname, major = ref.rsplit("@", 1)
    except ValueError:
        _SIZE_CACHE[ref] = None
        return None
    size = None
    for r in lib_roots:
        f = Path(r) / "components" / nsname / f"v{major}" / "contract.yaml"
        if f.exists():
            size = (yaml.safe_load(f.read_text()) or {}).get("size")
            break
    _SIZE_CACHE[ref] = size
    return size


def contract_attrs(ref, lib_roots):
    if ref in _ATTRS_CACHE:
        return _ATTRS_CACHE[ref]
    nsname, major = ref.rsplit("@", 1)
    attrs = {}
    for r in lib_roots:
        f = Path(r) / "components" / nsname / f"v{major}" / "contract.yaml"
        if f.exists():
            attrs = (yaml.safe_load(f.read_text()) or {}).get("attrs") or {}
            break
    _ATTRS_CACHE[ref] = attrs
    return attrs


def contract_elements(ref, lib_roots):
    """The element ids a component contracts, for L20's per-element states form."""
    if ref in _ELEMENTS_CACHE:
        return _ELEMENTS_CACHE[ref]
    nsname, major = ref.rsplit("@", 1)
    els = set()
    for r in lib_roots:
        f = Path(r) / "components" / nsname / f"v{major}" / "contract.yaml"
        if f.exists():
            els = set(((yaml.safe_load(f.read_text()) or {}).get("elements") or {}).keys())
            break
    _ELEMENTS_CACHE[ref] = els
    return els


def check_states(path, where, states, attrs, elements=None):
    """L20 - a state name is a token, and prose is not a state list.

    `states: 'Blue = 100G, Green = 40G'` is a real fact, correctly transcribed
    from the vendor's quick start guide, written in the only field that would
    accept it. attrs: takes anything, so it took that - and then nothing could
    read it. The Explorer splits data-states on whitespace and would have made
    chips called "=" and "100G," setting classes nothing paints, so it refuses
    the whole value and the port's real semantics reach no one.

    Two checks, one rule. A declared state name must be a token, because half of
    it becomes a CSS class. And `states` inside attrs: is that same prose in the
    same wrong place - the structured field is `states:` on the placement or its
    group, with the sentence beside it in `description:`.

    Warning rather than error while the portfolio catches up, per L18/L19. The
    two checks below it are errors instead, and can be: `behavior` and the
    per-element mapping are new spellings, so nothing in the portfolio predates
    them and no sweep is owed.
    """
    if isinstance(states, dict):
        for el, sts in states.items():
            if elements is not None and el not in elements:
                err(path, "L20", f"{where}: states names element {el!r}, which the "
                                 f"component does not contract "
                                 f"(has: {', '.join(sorted(elements)) or 'none'})")
            check_states(path, f"{where}/{el}", sts, None)
        states = []
    for st in states or []:
        name = st if isinstance(st, str) else (st or {}).get("name")
        if not isinstance(name, str) or not STATE_TOKEN.match(name):
            warn(path, "L20", f"{where}: state name {name!r} is not a token "
                              f"(^[a-z0-9-]+$). `state-<name>` is a CSS class; put "
                              f"the sentence in description: instead")
        # A state is colour AND behaviour, and `alternating` is the one behaviour
        # that cannot be drawn from a single colour - it flashes between two.
        beh = st.get("behavior") if isinstance(st, dict) else None
        if beh is None:
            continue
        mode = beh if isinstance(beh, str) else beh.get("mode")
        if mode not in STATE_BEHAVIORS:
            err(path, "L20", f"{where}/{name}: behavior {mode!r} is not one of "
                             f"{', '.join(sorted(STATE_BEHAVIORS))}")
        if mode == "alternating" and not (isinstance(beh, dict) and beh.get("color")):
            err(path, "L20", f"{where}/{name}: behavior alternating flashes between "
                             f"two colours - give the second as behavior.color")
    prose = (attrs or {}).get("states")
    if prose is not None:
        warn(path, "L20", f"{where}: attrs.states = {str(prose)[:60]!r} - state "
                          f"meanings in attrs: reach nothing. Declare states: on "
                          f"the placement or its group, with the prose in "
                          f"description:")


# Approximate glyph metrics, in em. Real faces differ by a few percent, which is
# why L21 carries a tolerance rather than pretending these are exact.
CAP_EM, DESC_EM, ADV_EM = 0.72, 0.10, 0.60
# How far a mark may reach into a part before it is a finding. The metrics above
# are estimates and a mark that grazes a boundary is not what this rule is for;
# 0.3mm is comfortably below the real cases, which buried 0.4 to 1.8mm of glyph.
SILK_TOL = 0.3


def _path_extent(path_d, at):
    """Bounding box of a silkscreen path, whose geometry is relative to its `at`."""
    v = []
    for tok in path_d.replace(",", " ").split():
        try:
            v.append(float(tok))
        except ValueError:
            pass
    if len(v) < 2:
        return None
    xs, ys = v[0::2], v[1::2]
    return (at[0] + min(xs), at[1] + min(ys), at[0] + max(xs), at[1] + max(ys))


def _text_extent(m):
    """Bounding box of a text mark. `at` is the BASELINE, not the top edge - which
    is the whole reason this rule exists: 2.2mm digits anchored 1.2mm below a port
    still reached up into it."""
    x, y = m["at"]
    fs = m.get("font-size", 2.2)
    w = len(str(m["text"])) * fs * ADV_EM
    anchor = m.get("anchor", "start")
    x0 = x - w if anchor == "end" else (x - w / 2 if anchor == "middle" else x)
    return (x0, y - fs * CAP_EM, x0 + w, y + fs * DESC_EM)


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
    check_states(path, data["name"], data.get("states"), data.get("attrs"))
    for el, spec in (data.get("elements") or {}).items():
        check_segment(path, "L2", el)
        check_states(path, f"{data['name']}/{el}", (spec or {}).get("states"), None)
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
    # Bays occupy faceplate area exactly as placements do. Leaving them out let a
    # rivet row sit on top of five fan bays without a word from the linter.
    for b in view_parts(view)["bays"]:
        # NOT transposed for `rotate`. A placement's size comes from the unrotated
        # component, so a quarter turn swaps it; a bay's size is authored as the
        # ON-PANEL footprint already, and `rotate` only spins the occupant inside
        # it. Transposing here reported the C40G's six horizontal card bays as
        # overlapping each other by 300mm.
        boxes.append((b["id"], b["at"][0], b["at"][1], b["size"]["w"], b["size"]["h"]))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            ox = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
            oy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
            # 0.05mm, not 0.001. Abutting parts on a fractional pitch round into
            # a hair of overlap - the C100G's 30.47mm card pitch puts adjacent
            # bays 0.01mm into each other - and reporting that trains people to
            # ignore the rule. Anything a sheet-metal shop could not hold is noise.
            if ox > 0.05 and oy > 0.05:
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
    for gname, gdef in (data.get("groups") or {}).items():
        check_states(path, f"groups/{gname}", (gdef or {}).get("states"),
                     (gdef or {}).get("attrs"))
    # Every id each view offers, indexed by view name. A `for:` may name a target
    # in ANOTHER view of the same device (`rear/psu-0`), so the check below cannot
    # be answered from the view it is standing in.
    view_ids = {}
    for vn_, vv_ in (data.get("views") or {}).items():
        vpp = view_parts(vv_ or {})
        view_ids[vn_] = ({q["id"] for q in vpp["placements"]}
                         | {b["id"] for b in vpp["bays"]})
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
                continue
            cls = contract_class(p["ref"], lib_roots)
            # L18 - a port on an AMBIGUOUS cage has to say which media it is.
            #
            # Most components answer for themselves: std/rj45 is an RJ45 and
            # nothing more specific exists, so inheriting media from the contract
            # is right and this rule must not fire on it. But one cage covers a
            # whole family - std/sfp-ganged is SFP, SFP+, SFP28 or SFP56, because
            # SFF-8433 gives them identical mechanicals - so the component can only
            # ever say "sfp", and a port that inherits it displays as SFP when the
            # datasheet says SFP28. That is the whole defect: the model looked
            # complete because a family token is still a token.
            #
            # Group attrs count. Declaring media once for a homogeneous block is
            # exactly what a group is for.
            if cls == "port":
                gattrs = ((data.get("groups") or {}).get(p.get("group")) or {}).get("attrs") or {}
                declared = (p.get("attrs") or {}).get("media") or gattrs.get("media")
                if not declared:
                    own = (contract_attrs(p["ref"], lib_roots) or {}).get("media")
                    if own in AMBIGUOUS_MEDIA:
                        warn(path, "L18", f"{vname}/{p['id']}: inherits media {own!r} from "
                                          f"{p['ref']}, which is a family, not an answer. "
                                          f"Declare the real media on the placement or on "
                                          f"group {p.get('group')!r}")
            # L19 - an indicator says what it indicates. Naming alone does not do
            # it: led-p0-a next to port-0 is a convention a reader infers and a
            # tool cannot. Warning, not error - `for:` postdates most of the
            # portfolio and 1101 of 1159 placements predate it.
            check_states(path, f"{vname}/{p['id']}", p.get("states"), p.get("attrs"),
                         contract_elements(p["ref"], lib_roots))
            if cls in ("led", "button", "display") and not p.get("for"):
                warn(path, "L19", f"{vname}/{p['id']}: {cls} declares no 'for:', so "
                                  "nothing knows what it indicates")
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
                # `chassis` is the whole unit, and it is not an invention: the
                # renderer already gives the faceplate data-path="chassis", so it
                # is a real node and the first row of every tree. An indicator
                # whose subject is a rail, a timing core or the box itself names
                # it. Nothing to locate, so nothing to measure against.
                if owner == "chassis":
                    if kind == "silkscreen":
                        err(path, "L14", f"{vname}: silkscreen {ident!r} is for "
                                         "'chassis'. Printed ink annotates a part, "
                                         "not the whole unit")
                    continue
                vref, oid = split_target(owner)
                if vref is not None:
                    # A cross-view reference: `rear/psu-0` from the front view. The
                    # view and the id both have to exist, and that is the whole
                    # test.
                    #
                    # There is deliberately NO proximity test here, and adding one
                    # would be wrong rather than merely strict. Each view defines
                    # its own coordinate system over its own face; the distance
                    # between a lamp at (12, 8) on the front and a PSU at (30, 20)
                    # on the rear is a subtraction of two unrelated origins and
                    # means nothing. The 30mm floor below exists to catch a legend
                    # on the far side of one panel from its target - across faces
                    # of a box it would reject every correct binding, since a front
                    # lamp is legitimately half a metre of chassis away from the
                    # part it names. Do not "fix" this.
                    if vref not in view_ids:
                        err(path, "L14", f"{vname}: {kind} {ident!r} is for {owner!r}, "
                                         f"but this device has no view {vref!r}")
                    elif oid not in view_ids[vref]:
                        err(path, "L14", f"{vname}: {kind} {ident!r} is for {owner!r}, "
                                         f"but {oid!r} is not a placement or bay in "
                                         f"view {vref}")
                    continue
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
            # Inside that region, or within one region-dimension of it. The floor
            # exists because indicators are banded: a stacked pair gets ONE row of
            # lamps above it, so the lamp serving the far member is a whole stack
            # pitch away from it and always will be. The floor therefore has to
            # clear the largest real stack pitch, not the typical one.
            #
            # It was 20mm, calibrated on an SFP belly-to-belly pair at 18mm. That
            # silently rejected QSFP: on the AS7326-56X the QSFP28 pair is on an
            # 18mm pitch with a 10.15mm cage, putting the lamp band 27.4mm from the
            # lower port's near edge, so sixteen correct bindings could not be
            # written. 30mm clears that with margin and is still a fifteenth of a
            # 440mm panel - an order of magnitude below "somewhere else entirely",
            # which is the mistake this rule exists to catch.
            #
            # Note what this rule can and cannot do: it catches an indicator bound
            # to something far away. It cannot catch one bound to the WRONG port in
            # the right block - that is a meaning error, and no distance test sees
            # it.
            tx, ty = max(bw, 30.0), max(bh, 30.0)
            if mx < ax - tx or mx > ax + bw + tx or my < ay - ty or my > ay + bh + ty:
                err(path, "L14", f"{vname}: {kind} {ident!r} at ({mx:g}, {my:g}) is "
                                 f"for {', '.join(known)} but sits well outside "
                                 f"({ax:g}, {ay:g} {bw:g}x{bh:g})")

        for m in vp["silkscreen"]:
            if m.get("id"):
                check_segment(path, "L2", m["id"])
            check_for("silkscreen", m.get("text") or m.get("id") or "path", m["at"], m.get("for"))
        # L21 - printed ink that a part covers is ink nobody can read.
        #
        # Silkscreen paints UNDER components by design: that is the layer model,
        # and a legend that disappears when its module is fitted is the intended
        # signal that it is in the wrong place. Nothing was checking it, so the
        # signal only ever arrived by someone looking at a render. On the AGR420
        # the port numbers were anchored 1.2mm below the bottom cage row and still
        # reached into it, because a text `at` is a baseline and the glyphs grow
        # upward from it. Across the portfolio 53 marks are buried, one of them by
        # 1.8mm of a 2.2mm digit.
        boxes = []
        for p in vp["placements"]:
            if not p.get("at"):
                continue                      # a mate-to occupant carries no position
            sz = (contract_size(p["ref"], lib_roots) or {})
            if sz.get("w") and sz.get("h"):
                boxes.append((p["at"][0], p["at"][1], sz["w"], sz["h"], p["id"]))
        for m in vp["silkscreen"]:
            if not m.get("at"):
                continue
            ext = _text_extent(m) if m.get("text") else (
                _path_extent(m["path"], m["at"]) if m.get("path") else None)
            if not ext:
                continue
            mx0, my0, mx1, my1 = ext
            for bx, by, bw, bh, bid in boxes:
                ox = min(mx1, bx + bw) - max(mx0, bx)
                oy = min(my1, by + bh) - max(my0, by)
                if ox > SILK_TOL and oy > SILK_TOL:
                    what = repr(m.get("text")) if m.get("text") else (m.get("id") or "path")
                    warn(path, "L21", f"{vname}: silkscreen {what} at "
                                      f"({m['at'][0]:g}, {m['at'][1]:g}) is {oy:.2f}mm "
                                      f"inside {bid}, which paints over it")
                    break

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

    if WARNINGS:
        by_code = {}
        for w in WARNINGS:
            by_code.setdefault(w.split("[")[1].split("]")[0], []).append(w)
        for code, ws in sorted(by_code.items()):
            print(f"LINT: {len(ws)} warning(s) [{code}]")
            # Five examples, then a per-file tally. The examples alone hid the
            # shape of the debt and actively misled: `lint | grep device` came
            # back empty for a device with dozens of warnings, because it was
            # grepping the five that happened to print. A count per file is what
            # makes this a dashboard instead of a sample.
            for w in ws[:5]:
                print(f"  {w}")
            if len(ws) > 5:
                per_file = {}
                for w in ws:
                    per_file[w.split(":")[0]] = per_file.get(w.split(":")[0], 0) + 1
                print(f"  ... and {len(ws) - 5} more, by file:")
                for f_, n_ in sorted(per_file.items(), key=lambda kv: -kv[1]):
                    print(f"      {n_:4d}  {f_}")
    if ERRORS:
        print(f"LINT: {len(ERRORS)} error(s) across {n} file(s)")
        for e in ERRORS:
            print(f"  {e}")
        sys.exit(1)
    print(f"LINT: ok ({n} files)")


if __name__ == "__main__":
    main()
