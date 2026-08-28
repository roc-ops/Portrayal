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
  L22 device: a group's declared media/speed matches the ports it holds
  L23 device: a port group is one family, or says in `mixed:` why it is not
  L24 device: `attrs.other` is counted, so the long tail cannot go quiet
  L25 device: one attr key is claimed by one section - it flattens to data-<key>
  L26 component: every `class: cutout` element is backed - the contract conforms,
      or a part at that id resolves to something that does. Counted per CUTOUT
  L27 component: a power-bearing module states its figure, or leaves the record
      that no document holds it
  L28 component: a power figure says which way it points, and its min/typical/max
      are in order
  L29 device: a chassis says how many of the modules it accepts have no figure,
      so a module total is never quoted as one while it is a floor
  L30 device: a card whose figure already covers its paired I/O module, beside a
      paired module that states its own - a sum would count the pairing twice
  L34 device: front and rear occupants of one slot fit around the midplane -
      they may overlap by a tongue, not by a card length
  L33 device: a bay reserves room for every module it accepts, compared
      against the module's `insert` where it has one and `size` otherwise
  L32 any yaml: no mapping declares the same key twice - a duplicate is resolved
      by the parser before anything else sees the file, so the loss is silent
  L35 component: a relief magnitude says where it came from, or is counted as
      unstated - an estimate and a measurement are indistinguishable otherwise
  L36 component: a `borrowed` magnitude names an origin that actually measured it
  L37 device: a group says what it is FOR, and a declared group has members
  L38 component: printed text in a skin sits in a silkscreen group, unless the
      part is applied over the panel rather than printed into it
  L40 device: a pluggable cage says which optics run in it, and optics prose
      names a port group that exists
  L39 device: the panel's holes agree with what goes in them - no two overlap,
      each matches its occupant's standard, no legend is printed on one, and a
      port on a view that declares cutouts has one
  L41 device: a bay or placement scoped to configurations names configurations
      that exist, and does not scope itself to all of them or to none
  L42 device: a silkscreen mark says what it annotates - a part, or `chassis`
      for printing about the whole unit
  L43 device: a front or rear view as wide as the 19-inch rack face still has
      its mounting ears in it; the modelled body is the metal between the folds
  L44 device: panel decor agrees with what is on the face - a patterned field is
      not buried under the parts, and printing does not run off the edge
  L45 device: a view at `modelled` draws something, or it is a size with no face
  L46 component: composed parts do not collide with each other inside the part
  L52 component: a stated power figure says where it was read from
  L53 device: content changed without the version bump the change requires
  L54 device: a declared gap scopes something the device does not have
  L55 library: every vendor namespace is in the vendor registry
  L56 overlay: a NOS identity names a software vendor the registry knows
  L57 device: configurations say what kind of thing they are, and the base is the default
  L58 component: a wrapper's own connection point sits where its aperture mates
  L59 device: top-level part-numbers are not read by anything
      that composes them
  L60 device: a view that says it is empty has to be empty
  L47 component: a declared lamp state is a promise the drawing can keep - some
      element lights when it is set
"""
import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

import attrsections as attrs_mod
import devicelock
from manifest import (view_parts, targets, split_target, presented_interface,
                      VIEW_KEY_ORDER,
                      component_refs, load_yaml,
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

# Which media share a cage. SFP+ modules go in SFP cages, QSFP28 modules go in
# QSFP-DD cages, and the mechanicals do not distinguish them - which is why one
# component serves the whole column and why a group is allowed to say "these are
# SFP28" over a component whose contract can only say "sfp". Anything absent
# answers for itself: rj45 is its own family and nothing else is in it.
MEDIA_FAMILY = {
    "sfp": "sfp", "sfp-plus": "sfp", "sfp28": "sfp", "sfp56": "sfp",
    "qsfp": "qsfp", "qsfp-plus": "qsfp", "qsfp28": "qsfp", "qsfp56": "qsfp",
    "qsfp-dd": "qsfp",
}


def media_family(m):
    return MEDIA_FAMILY.get(m, m)

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
            cls = (load_yaml(f) or {}).get("class")
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
            size = (load_yaml(f) or {}).get("size")
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
            attrs = (load_yaml(f) or {}).get("attrs") or {}
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
            els = set(((load_yaml(f) or {}).get("elements") or {}).keys())
            break
    _ELEMENTS_CACHE[ref] = els
    return els


_PAINT_CACHE = {}
_SVG_NS = "{http://www.w3.org/2000/svg}"


def _paint_box(el):
    """The box a single SVG node covers, or None if it paints nothing or if this
    reader cannot be sure. `fill` absent means black in SVG, so absent is FILLED;
    only an explicit `none` is not. A stroked outline with no fill is a groove or
    a moulding - you read printing through it, so it does not bury anything."""
    tag = el.tag.replace(_SVG_NS, "")
    if el.get("transform"):
        return "unsure"                    # composing transforms is out of scope here
    if (el.get("fill") or "").strip() == "none":
        return None
    try:
        if tag == "rect":
            x, y = float(el.get("x", 0)), float(el.get("y", 0))
            return (x, y, x + float(el.get("width", 0)), y + float(el.get("height", 0)))
        if tag == "circle":
            cx, cy, r = (float(el.get(k, 0)) for k in ("cx", "cy", "r"))
            return (cx - r, cy - r, cx + r, cy + r)
        if tag == "ellipse":
            cx, cy = float(el.get("cx", 0)), float(el.get("cy", 0))
            rx, ry = float(el.get("rx", 0)), float(el.get("ry", 0))
            return (cx - rx, cy - ry, cx + rx, cy + ry)
        if tag in ("path", "polygon", "polyline"):
            d = el.get("d") or el.get("points") or ""
            # The token bbox below only tells the truth when every number is half of
            # an x,y pair. Relative commands, and the shorthands H V A C S Q T that
            # carry an odd count, both break that, so anything but M/L/Z is unsure.
            if tag == "path" and re.search(r"[^MLZ0-9eE.,+\-\s]", d):
                return "unsure"
            return _path_extent(d, (0, 0)) or "unsure"
    except (TypeError, ValueError):
        return "unsure"
    return "unsure"


def paint_boxes(ref, skin, lib_roots):
    """Every box a component's skin actually PAINTS, in component-local mm, or None
    when the skin cannot be read confidently.

    L21 asks whether a legend is buried, and burial is about paint, not about a
    bounding rectangle. Two components in this library make the difference matter:
    casa/brand-swoop is one unfilled stroked curve 258mm wide that paints nothing
    over the mark it was accused of hiding, and common/qsfp28-cage carries four
    panel LEDs above its aperture, with the port number printed in the metal
    BETWEEN the two LED pairs - exactly where the vendor prints it."""
    key = (ref, skin)
    if key in _PAINT_CACHE:
        return _PAINT_CACHE[key]
    boxes = None
    try:
        nsname, major = ref.rsplit("@", 1)
    except ValueError:
        _PAINT_CACHE[key] = None
        return None
    for r in lib_roots:
        base = Path(r) / "components" / nsname / f"v{major}"
        if not (base / "contract.yaml").exists():
            continue
        sp = base / "skins" / f"{skin}.svg"
        if not sp.exists():
            break
        try:
            root = ET.parse(sp).getroot()
        except ET.ParseError:
            break
        boxes = []
        for el in root.iter():
            if el is root:
                continue
            tag = el.tag.replace(_SVG_NS, "")
            if tag in ("defs", "title", "desc", "style", "metadata"):
                boxes = None
                break
            if tag in ("g", "svg"):
                if el.get("transform"):
                    boxes = None
                    break
                continue
            b = _paint_box(el)
            if b == "unsure":
                boxes = None
                break
            if b:
                boxes.append(b)
        # A component composes standard hardware through `parts:`; that art paints
        # too, and the skin does not contain it.
        if boxes is not None:
            contract = load_yaml(base / "contract.yaml") or {}
            for p in contract.get("parts") or []:
                psz = contract_size(p.get("ref", ""), lib_roots) or {}
                if not (psz.get("w") and psz.get("h")):
                    boxes = None
                    break
                px, py = (p.get("at") or [0, 0])[:2]
                boxes.append((px, py, px + psz["w"], py + psz["h"]))
        break
    _PAINT_CACHE[key] = boxes
    return boxes


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
    still reached up into it.

    A ROTATED MARK RUNS ALONG A DIFFERENT AXIS, and measuring it as if it did not
    is how a label printed neatly down a chassis's right edge gets reported as
    running off the face: its length was being added to x, where the metal ends,
    instead of to y, where there is room. The same arithmetic accused rotated
    module legends of painting over the modules beside them. Only the right
    angles are handled - anything else is rare enough that the unrotated box is
    the safer approximation, and being slightly too generous costs a missed
    warning rather than a fabricated one."""
    x, y = m["at"]
    fs = m.get("font-size", 2.2)
    w = len(str(m["text"])) * fs * ADV_EM
    up, down = fs * CAP_EM, fs * DESC_EM
    anchor = m.get("anchor", "start")
    lead = w if anchor == "end" else (w / 2 if anchor == "middle" else 0.0)
    rot = int(m.get("rotate", 0)) % 360
    if rot == 90:            # runs downward, cap side to the LEFT of the baseline
        return (x - up, y - lead, x + down, y - lead + w)
    if rot == 270:           # runs upward, cap side to the right
        return (x - down, y + lead - w, x + up, y + lead)
    if rot == 180:           # runs leftward, cap side below
        return (x - w + lead, y - down, x + lead, y + up)
    return (x - lead, y - up, x - lead + w, y + down)


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
        data = load_yaml(path)
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


def device_dependencies(dev_path, lib_roots):
    """Every file a device's drawing depends on: its manifest, the contracts of
    every component it names, those components' own `parts`, and every skin any
    of them draws with.

    TRANSITIVE, because a component may compose others - the C40G's AC inlet
    panel carries four std/c14-inlet - and a build that re-rendered only on a
    direct ref would go stale the moment somebody edited an inlet.

    SKINS COUNT. They are the actual artwork; a contract can be untouched while
    the drawing it produces changes completely.
    """
    dev = load_yaml(dev_path)
    if not dev:
        return {Path(dev_path)}
    files = {Path(dev_path)}
    seen, queue = set(), list(component_refs(dev))
    while queue:
        ref = queue.pop()
        if ref in seen:
            continue
        seen.add(ref)
        cp = resolve_component(ref, lib_roots)
        if not cp:
            continue
        files.add(cp)
        spec = load_yaml(cp) or {}
        for sk in (spec.get("skins") or []):
            sp = cp.parent / "skins" / f"{sk}.svg"
            if sp.exists():
                files.add(sp)
        for part in (spec.get("parts") or []):
            if part.get("ref"):
                queue.append(part["ref"].split(":")[0])
    return files


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
        sub = load_yaml(found)
        sub_if = sub.get("interface")
        if not sub_if:
            continue
        # declaring none is fine - a PSU composes an inlet without presenting one
        # at its own origin. Contradicting it is not.
        if data.get("interface") and data["interface"] != sub_if:
            err(path, "L11", f"declares interface {data['interface']!r} but composes "
                             f"{part['ref']} presenting {sub_if!r}")


def _composes_a_standard(data, lib_roots, depth=0, seen=None):
    """Does anything under `parts:` say what standard it is, transitively?

    A leaf satisfies this by declaring `conforms:` OR `interface:`. `conforms:`
    is the strong form - L9 checks it against the registry to the millimetre -
    but `std/lc-bore@1` carries `interface: lc` and no `conforms:`, and 82
    `lc-duplex-adapter` placements resolve through it. An aperture that names
    the plug it accepts has said what it is, even where the registry has not
    caught up with it yet.
    """
    seen = seen or set()
    if depth > 4:
        return False
    for part in data.get("parts") or []:
        ref = part.get("ref")
        if not ref or ref in seen:
            continue
        found = resolve_component(ref, lib_roots)
        if not found:
            continue                       # L10 reports the broken ref
        sub = load_yaml(found) or {}
        if sub.get("conforms") or sub.get("interface"):
            return True
        if _composes_a_standard(sub, lib_roots, depth + 1, seen | {ref}):
            return True
    return False


def _part_backs(part, lib_roots):
    """Does this `parts:` entry resolve to something that says what it is?"""
    found = resolve_component(part.get("ref") or "", lib_roots)
    if not found:
        return None                        # L10 reports the broken ref
    sub = load_yaml(found) or {}
    if sub.get("conforms") or sub.get("interface") or \
            _composes_a_standard(sub, lib_roots):
        return sub.get("size") or {}
    return None


def _cutout_is_backed(eid, spec, data, lib_roots):
    """Is THIS opening composed from something that says what it is?

    Matched by ID FIRST and by GEOMETRY otherwise, because the library uses both
    and neither alone is enough. A `parts:` entry whose id is the cutout's is an
    explicit statement that the two are the same opening. Where the ids differ -
    `common/qsfp28-cage` wraps `std/qsfp-ganged`, and a panel assembly wraps the
    cage under an id of its own - the composed part still SITS ON the opening,
    and overlapping it is what makes them the same aperture rather than two.

    Geometry rather than id alone matters because a rule that demanded matching
    ids would punish the library for having a middle layer, which is the
    defect `test_a_wrapper_of_a_wrapper_still_resolves` exists to prevent.
    Id alone is kept as the first test because it is an explicit claim and does
    not depend on a placement being drawn accurately.
    """
    at, size = spec.get("at") or [0, 0], spec.get("size") or [0, 0]
    cx0, cy0, cx1, cy1 = at[0], at[1], at[0] + size[0], at[1] + size[1]
    for part in data.get("parts") or []:
        psize = _part_backs(part, lib_roots)
        if psize is None:
            continue
        if part.get("id") == eid:
            return True
        pat = part.get("at") or [0, 0]
        pw, ph = psize.get("w", 0), psize.get("h", 0)
        if part.get("rotate") in (90, 270):
            pw, ph = ph, pw
        if pat[0] < cx1 and pat[0] + pw > cx0 and pat[1] < cy1 and pat[1] + ph > cy0:
            return True
    return False


def lint_component_aperture(path, data, lib_roots):
    """L26: every aperture is backed by something that says what it is.

    Keyed on `class: cutout` rather than on `class: port`, because the geometry
    is the population and the class is not. `casa/io-6p12` and `io-6p12-sw` are
    `class: line-card` and draw eighteen MCX openings each as inline rectangles
    at an ESTIMATED bore - 252 rendered apertures across the C100G and C40G bays,
    which a rule keyed on `class: port` would never look at.

    THE UNIT IS THE CUTOUT, NOT THE COMPONENT, and it used to be the component.
    The old gate exited early if the contract composed ANY standard part
    anywhere, which asks "does this author follow the compose pattern?" when the
    question the rule exists to answer is "which openings have nothing behind
    them". A component composing seventeen std/ parts and drawing one unbacked
    cutout has one unbacked cutout; the seventeen do not make it zero. The rule's
    own message already counted ELEMENTS while its gate operated on components,
    so the two disagreed about the unit.

    THE CASE THAT SETTLED IT: cisco/a9k-400g-dwdm-tr composes twenty SFP+ ports
    from std/sfp and draws two CFP2 openings that no MSA publishes a figure for.
    Under the old gate it produced no warning at all - the more of a card you
    model correctly, the better it hid the part you could not, so the rule went
    quieter as a card got larger.

    THE COUNT'S MEANING CHANGED WITH THE UNIT. Before this, "4" meant four
    COMPONENTS with no std/ backing anywhere. Now a number means unbacked
    CUTOUTS' components wherever they sit, so a before-and-after comparison is
    not like for like - 10 to 26 is the same library described more precisely,
    not a regression. The four originals - rj11-jack, rj45-jack and
    rj45-shielded twice - compose nothing and report identically either way.

    A warning, not an error, and the message names the registry on purpose. Half
    of what this finds is true and unfixable the same day: there is no `db9` key
    in `standards.yaml`, so the warning is a to-do list for `std/` rather than an
    accusation. L14 and L21 both had to be recalibrated for firing as accusations
    too early.

    THE COUNT STAYS HOMOGENEOUS - every entry still means "no std/ part exists to
    compose" - but the entries are not equally closeable, and `wanted:` on each
    contract is where that distinction lives. Fifteen of the twenty-six are one
    connector, the DE-9 alarm output, whose panel cutout IS published in
    MIL-DTL-24308: a runnable errand, the same shape as the MCX and XFP keys that
    turned out findable once somebody looked outside the vendor's own guide. The
    CPAK, CFP and CFP2 openings are not: those specifications withhold the figure
    by design and need MSA membership or a vendor drawing. Same count, different
    species, and a reader who cannot tell them apart will spend their time on the
    wrong one.

    `std/` is exempt. Those components compose nothing because they ARE the
    bottom of the stack; running the rule on them would flag the foundations for
    not standing on anything. A contract that declares `conforms:` is exempt for
    the same reason - it IS the aperture it draws.
    """
    cutouts = sorted(el for el, spec in (data.get("elements") or {}).items()
                     if (spec or {}).get("class") == "cutout")
    if not cutouts:
        return
    try:
        ns = path.parents[2].name
    except IndexError:
        ns = ""
    if ns == "std" or data.get("conforms"):
        return
    els = data.get("elements") or {}
    unbacked = [el for el in cutouts
                if not _cutout_is_backed(el, els[el] or {}, data, lib_roots)]
    if not unbacked:
        return
    shown = ", ".join(unbacked[:4]) + (" ..." if len(unbacked) > 4 else "")
    warn(path, "L26", f"{len(unbacked)} of {len(cutouts)} element(s) declaring "
         f"class: cutout ({shown}) are backed by nothing - {data.get('name')} "
         "declares no 'conforms:' and composes no part at those ids that does, so "
         "the opening is drawn here instead of composed. If no std/ component "
         "exists for this connector, add the key to spec/schemas/standards.yaml "
         "and a std/ part carrying it; if the dimension cannot be sourced yet, "
         "this warning is the record of that - and the contract's `wanted:` should "
         "say which of those two it is")


# Which way the power goes, by class. A module that consumes owes a
# `power-draw-*-w`; a module that provides owes `power-output-w`. They are
# opposite signs of one unit, and the reason they can never share a key is that
# a sum over both looks entirely plausible and is a category error: two 650 W
# PSUs and eight 850 W line cards added together is not a draw, not a supply,
# and not a crash.
# `fabric` is here for the same reason the others are, not as a courtesy. An
# ASR 9922 holds seven switch fabric cards and Cisco's own per-card table gives
# them 340 W each at 55 C - 2.4 kW that a chassis budget cannot leave out. A
# fabric card is a card in a slot that consumes; the only thing separating it
# from `line-card` is that it forwards between cards rather than off the box,
# which is not a fact about power.
# LOADED FROM spec/schemas/power-roles.yaml, not written here, so the sets and
# the rule that enforces them cannot drift - and so a consumer that has to total
# a chassis can read the same file rather than reimplementing this list. The
# prose that used to live here moved into it; the registry is the argument.
#
# AT IMPORT, not in main(). Loading it only when the CLI parsed --schemas left
# every other caller - a test, a totalling tool, anything importing this module
# as a library - holding three empty tuples, which reads as "no class has a
# power role" and is the exact silence this file exists to end. The CLI still
# overrides from its own --schemas so an alternate tree can be linted.
def _load_power_roles(schemas):
    """The three sets, from the registry. Empty on absence rather than raising -
    a missing registry is a broken checkout, and L51 will say so on every class."""
    f = Path(schemas) / "power-roles.yaml"
    if not f.exists():
        return (), (), ()
    r = (load_yaml(f) or {}).get("roles") or {}
    return (tuple(r.get("draw") or ()), tuple(r.get("supply") or ()),
            tuple(r.get("passive") or ()))


DRAW_CLASSES, SUPPLY_CLASSES, PASSIVE_CLASSES = _load_power_roles(
    Path(__file__).resolve().parents[2] / "schemas")


def _load_vendors(schemas):
    """The vendor registry, or an empty one if the checkout is broken.

    Loaded at import beside the power roles, and for the same reason: a rule
    that silently passes when its registry is missing is worse than one that
    fails loudly, so L55 reports on every namespace when this comes back empty.
    """
    path = Path(schemas) / "vendors.yaml"
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}, {}
    return (doc.get("vendors") or {}), (doc.get("namespaces") or {})


VENDORS, NAMESPACES = _load_vendors(
    Path(__file__).resolve().parents[2] / "schemas")
DRAW_KEYS = ("power-draw-typical-w", "power-draw-max-w", "power-draw-min-w")
SUPPLY_KEYS = ("power-output-w",)

# The device-level vocabulary, reserved for the whole box and refused here, plus
# the spelling this design replaced. `watts: '650'` is banned for saying nothing
# about direction; `power-max-w` is banned for being the DEVICE's word, so that
# the obvious downstream query - sum `power-max-w` over a chassis's occupants -
# returns nothing at all rather than a credible wrong number.
AMBIGUOUS_POWER_KEYS = {
    "watts": "it does not say whether the module draws this or provides it",
    "power-max-w": "that spelling belongs to the whole device",
    "power-typical-w": "that spelling belongs to the whole device",
    "power-min-w": "that spelling belongs to the whole device",
    "power-max-ac-w": "that spelling belongs to the whole device",
    "power-max-dc-w": "that spelling belongs to the whole device",
}


def _power_advice(cls):
    """The key this class owes, named so the author cannot pick the wrong side."""
    if cls in SUPPLY_CLASSES:
        return ("power-output-w",
                "the continuous output it is rated to PROVIDE")
    return ("power-draw-max-w",
            "the load it IMPOSES at its worst rated case (and "
            "`power-draw-typical-w` beside it where the vendor states one)")


def lint_component_role(path, data, _lib_roots=None):
    """L51: a class nobody has decided the power question for.

    A power-totalling tool walked an MX chassis and stopped at the craft
    interface - "I don't know how much the craft interface uses". The contract
    was silent, and it was silent because `panel` and `display` were in neither
    the draw set nor the supply set, so L27 never asked. Nothing was wrong with
    the contract; the question had never been put to it.

    THAT IS THE FAILURE THIS CATCHES, and it is a failure of a CLASS rather than
    of a part. A silence that nothing demanded be filled reads exactly like a
    silence that means zero, and a consumer cannot tell a filter that
    contributes nothing from a card whose figure nobody has looked up. One makes
    a total correct and the other makes it a floor.

    So every class in use answers to spec/schemas/power-roles.yaml, and a class
    in none of the three roles is reported HERE rather than discovered later by
    something trying to add up a chassis. It fires at the moment a class is
    invented, which is the moment someone knows the answer.

    A warning and not an error: the honest response is sometimes "this needs
    thinking about", and a red gate would be cleared by guessing.
    """
    cls = data.get("class")
    if not cls or cls in DRAW_CLASSES or cls in SUPPLY_CLASSES or cls in PASSIVE_CLASSES:
        return
    warn(path, "L51", f"class {cls!r} is in no power role. spec/schemas/power-roles.yaml "
                      "sorts every class into draw (states power-draw-max-w), supply "
                      "(states power-output-w) or passive (contributes zero and is not "
                      "asked). A class in none of them is never asked for a figure, so "
                      "its silence is indistinguishable from a part that draws nothing - "
                      "which is how a chassis total quietly became a floor. Add it to "
                      "the role it belongs in")


def lint_component_power(path, data, _lib_roots=None):
    """L27 and L28 - a module's watts, and which way they point.

    L27, warning. A component of a power-bearing class states no figure. The
    message names the key for THAT class, because the whole design turns on the
    author not picking the wrong side of it while clearing the warning.

    A warning for the L26 reason: most of what it finds is true and unfixable
    the same day. Edgecore publishes no output wattage for the AGR PSUs in any
    document here - the datasheet gives input current only - and not one line
    card, fan or transceiver in the library has a draw figure from any source.
    So this is a to-do list against the SOURCES, not an accusation against the
    author, and an err() would go red across the library on day one and teach
    people to ignore the linter. That is the failure L14 and L21 both had to be
    recalibrated out of.

    L28, error. A figure that cannot be trusted: an ambiguous spelling, or an
    ordering contradiction (min above typical, typical above max). An error and
    not a warning because unlike L26 and L27 neither half depends on a document
    nobody has - renaming `watts` needs no new information, and a card whose
    typical exceeds its max is a transcription slip in this repo, not a fact
    about the world. It is the same line L22 (the group contradicts its members,
    error) draws against L23 (the group has not explained itself, warning), and
    it is what makes the ban in L28 a ban: a warning-level ban is not one.
    """
    attrs = data.get("attrs") or {}
    name = data.get("name")
    # BEFORE L27's early returns, every one of which fires exactly when a figure
    # is present - which is when L52 has something to say.
    _power_provenance(path, data, attrs)
    for key, why in AMBIGUOUS_POWER_KEYS.items():
        if key not in attrs:
            continue
        want, means = _power_advice(data.get("class"))
        err(path, "L28", f"attrs.{key} on a component: {why}. Draw and supply are "
                         f"opposite signs of one unit, so a sum over both is a "
                         f"category error that reads as an answer. Write {want} "
                         f"- {means} - as a number in watts")
    figures = {k: attrs[k] for k in DRAW_KEYS
               if isinstance(attrs.get(k), (int, float))}
    lo, mid, hi = (figures.get("power-draw-min-w"),
                   figures.get("power-draw-typical-w"),
                   figures.get("power-draw-max-w"))
    for a, an, b, bn in ((lo, "min", mid, "typical"), (mid, "typical", hi, "max"),
                         (lo, "min", hi, "max")):
        if a is not None and b is not None and a > b:
            err(path, "L28", f"power-draw-{an}-w is {a} W and power-draw-{bn}-w is "
                             f"{b} W - {an} cannot exceed {bn}. One of the two was "
                             "read off the wrong row")
    cls = data.get("class")
    if cls not in DRAW_CLASSES and cls not in SUPPLY_CLASSES:
        return
    # A GENERIC optic is not a part and cannot have a wattage. A 40GBASE-SR4 is
    # about 1.5 W and a 400G ZR about 20 W, and they are the same drawing -
    # `common/qsfp-transceiver` is a shape that stands in for both, so any figure
    # on it would be a fiction dressed as a fact rather than a missing one.
    #
    # This is L18's argument exactly, and it reuses L18's constant. There, a port
    # inheriting `media: sfp` from a family cage must declare the real media on
    # the placement or the group, because the component can only ever say the
    # family. Here the same is true of watts: the figure is a property of the
    # optic actually fitted, so it belongs on the placement, where a device that
    # knows which optic it ships can source it.
    #
    # So the rule stays QUIET rather than warning forever on something no
    # contributor could ever close - the failure L14 and L21 were recalibrated
    # for. The chassis-level hole stays visible in L29, which is the right place
    # for it: a chassis genuinely cannot total optics it has not been told about.
    # A transceiver with a SPECIFIC media answers for itself and is still asked.
    if cls == "transceiver" and attrs.get("media") in AMBIGUOUS_MEDIA:
        return
    keys = SUPPLY_KEYS if cls in SUPPLY_CLASSES else DRAW_KEYS
    if any(k in attrs for k in keys):
        return
    # AN ATTESTATION IS AN ANSWER. L27 standing forever is right while the
    # question is open and wrong once it has been settled - and "the vendor does
    # not publish it" is a settled answer, not a pending one. Without a way to
    # say so, a searched-and-genuinely-absent figure is indistinguishable from
    # one nobody has looked for, which is what made 249 warnings unreadable as a
    # to-do list. L52 makes the claim carry its provenance.
    if attrs.get("power-absent"):
        return
    want, means = _power_advice(cls)
    # A CONDUIT is neither a draw nor a supply, and telling one to state
    # `power-output-w` is advice to write a wrong number - worse than saying
    # nothing. Casa rates a power entry module in amps and volts and never in
    # watts, because a PEM does not convert or regulate: it filters and
    # distributes what the DC plant feeds it, so its rating bounds what may PASS
    # THROUGH rather than describing an output. Deriving watts means multiplying,
    # and with two current figures across an 18 V-wide input range the product
    # lands anywhere from about 810 W to 1800 W per feed.
    #
    # There is no `conduit` class yet and this message is deliberately doing the
    # work one would do, because one vendor's DC plant is not enough to design a
    # class from - see the design note. What the message must not do meanwhile is
    # instruct the author to guess.
    conduit = (" That is the key if this part CONVERTS or REGULATES. If it only "
               "CARRIES current - a power entry module, a busbar - watts are the "
               "wrong unit for it: the rating bounds what may pass through and is "
               "not an output, so record the vendor's own volts and amps instead "
               "of multiplying them into one answer out of a range."
               if cls in SUPPLY_CLASSES else "")
    warn(path, "L27", f"{name} is class {cls} and states no power figure. Add "
                      f"attrs.{want} - {means} - as a number in watts.{conduit} "
                      "If no "
                      "document you hold states it, leave this warning standing: "
                      "it is the record that the figure is missing, and a chassis "
                      "total is a floor rather than a total until it lands. Do not "
                      "estimate one - an unsourced watt figure is the same number "
                      "minus the warning")


def _power_provenance(path, data, attrs):
    """L52: a watt figure that does not say where it was read from.

    L27's whole argument is that a number without a source is worse than a
    warning, because it is "the same number minus the warning". That holds only
    if the source is WRITTEN DOWN. Twenty-eight figures in the library are not:
    they state watts and carry no `provenance.power`, so nothing distinguishes a
    figure read off a vendor table from one somebody remembered.

    THE FAILURE THIS IS FOR is not the missing figure - L27 has that covered, and
    it fired 249 times without anybody being able to close it. It is the figure
    that arrives WITHOUT A ROW, because vendor power figures are not scalars.
    They are ladders by ambient: MIC-3D-4COC3-1COC12 prints 33.96 W in three
    guides bare and in four more as the 25 C rung of a ladder whose 55 C rung is
    36.48 W. Both numbers are true. Only one is a maximum, they differ by seven
    percent, and once the figure is in `attrs` with no row behind it there is no
    way to tell from the file which one was taken. A re-check means finding the
    document again from nothing.

    So the rule asks only for the record, and does NOT demand an ambient: plenty
    of sources publish a bare maximum and inventing a temperature to satisfy a
    linter would be the L27 failure wearing a different hat. What it demands is
    that whoever wrote the number says what they read.

    A warning, for the L26 and L27 reason exactly. Twenty-eight files would go
    red on the day this lands and the fix for most of them is archaeology, not
    typing - and a red gate that cannot be cleared today is how L14 and L21 both
    taught people to ignore the linter. It also cannot become an error at
    `verified` the way L15 and L42 do, because components carry no maturity at
    all: all 421 of them read `None`. That is worth its own rule one day; it is
    not this one.
    """
    stated = sorted(k for k in (*DRAW_KEYS, *SUPPLY_KEYS) if k in attrs)
    absent = attrs.get("power-absent")
    if not stated and not absent:
        return
    # ANY power-named provenance key counts, not just `power`. Contracts written
    # before this rule existed key the note by the ATTRIBUTE it explains -
    # `power-draw-max-w:`, `power-output-w:`, `power-output:` - which is at least
    # as precise as `power:` and arguably more so when a contract states several
    # figures. Reading only `power` accused eighteen contracts that had done the
    # work, including one quoting its guide verbatim: "The fan module has a power
    # draw of approximately 400W." A rule that fires on correct models teaches
    # people to ignore the linter, which is the failure L14 and L21 were both
    # recalibrated out of.
    prov = data.get("provenance") or {}
    if any(str(v or "").strip() for k, v in prov.items() if k.startswith("power")):
        return
    # AN ABSENCE CLAIM IS A FACT ABOUT THE WORLD and needs sourcing exactly as a
    # number does - more, if anything, because it is what tells the next person
    # to stop looking. Seven MX contracts said "NOT STATED for this model in the
    # module reference extraction", which was true of the book it named and
    # false of the corpus: the FRU power tables were in the chassis guides all
    # along. An unsourced `power-absent` would make that mistake permanent.
    if absent and not stated:
        warn(path, "L52", f"{data.get('name')} claims power-absent: {absent} and "
             "no provenance.power says what was searched. Name the documents, not "
             "one document: 'not stated in the module reference' was true of that "
             "book and false of the corpus, because the FRU power tables live in "
             "the chassis guides. An absence claim is what stops the next person "
             "looking, so it has to say where it looked")
        return
    warn(path, "L52", f"{data.get('name')} states {', '.join(stated)} and no "
         "provenance.power says where it came from. Add it, naming the document "
         "and - if the source gives a ladder by ambient - the row: vendor tables "
         "commonly print the same part at 25, 40 and 55 C, the figures differ by "
         "enough to matter, and a bare number cannot say which rung it is. If the "
         "source states one figure with no temperature, record that; do not invent "
         "an ambient to fill the sentence")



# ---------------------------------------------------------------- L35 / L36
#
# A relief magnitude is a number about the world and until this afternoon the
# library had nowhere to say where it came from. `confidence` and `source` fixed
# that; these two rules are what stop the field being only as good as each
# author's memory.
#
# THE VOCABULARY, so the rule teaches it rather than merely scoring it:
#
#   measured        off this part's own hardware, with an instrument
#   photo-measured  off a photograph of it
#   drawing         off its own artwork, or a vendor figure of it
#   datasheet       the vendor states it
#   registry        from spec/schemas/standards.yaml
#   borrowed        another Portrayal part's MEASURED figure for the same class of
#                   hardware, reused because nobody publishes one for this part
#   estimated       a plausible figure with no source
#   known-wrong     not merely unmeasured - contradicted by something checkable
#
CONFIDENCE_MEASURED = ("measured", "photo-measured")


def _feature_magnitude(feat):
    """The one dimension a relief feature declares, as (key, value), or None.

    `lift`, `knurl`, `thread` and `color` modify a feature; they are not the
    number it is about, and asking a feature which magnitude it carries has to
    ignore them or every stacked cyl looks like two numbers.
    """
    keys = [k for k in ("top", "sink", "out", "dome", "cyl", "bar", "uhandle", "vent")
            if feat.get(k) is not None]
    return (keys[0], float(feat[keys[0]])) if len(keys) == 1 else None


def lint_component_relief_confidence(path, data, lib_roots):
    """L35 (warning) and L36 (error) - where a relief magnitude came from.

    L35 COUNTS THE UNMARKED rather than naming each one, which is L26's and L27's
    shape: most of what it finds is true and was written before the field existed,
    and a rule that prints forty lines per file gets ignored, which is the failure
    L14 and L21 were both recalibrated for. One line per file, with the count.

    Warning, not error, ON PURPOSE. An optional key that becomes mandatory
    retroactively fails features nobody has had the chance to mark, on parts whose
    authors are long gone from this session.

    L36 IS AN ERROR, and the difference is the same line L28 draws against L27.
    `borrowed` does not merely fail to state a source, it ASSERTS one: it says the
    magnitude is another part's MEASURED figure, and that is the only thing it adds
    over `estimated`. A token that asserts a fact must have the fact checked at
    every use, and here the fact depends on nothing but files in this repository -
    so it is checkable, and a warning-level ban is not a ban.

    IT ASKS A STRUCTURAL QUESTION, NOT A STRING ONE. Not "does the origin's prose
    contain the word measured", which measures the author's phrasing; but "does the
    origin carry a relief feature of this same magnitude, and does THAT feature call
    itself measured or photo-measured". That is the query the data supports.
    Borrowing from a borrow fails, which is intended: a chain of citations has to
    terminate in somebody holding an instrument.

    This rule is written because 213 of 216 `borrowed` features in one vendor's set
    asserted a measurement that was never taken - two of them citing origins whose
    own provenance reads "estimated - it stands proud but was not measured". It
    would have caught every one of them at the moment it was written.
    """
    feats = ((data.get("relief") or {}).get("features") or [])
    if not feats:
        return
    unstated = [f["node"] for f in feats if not f.get("confidence")]
    if unstated:
        shown = ", ".join(unstated[:4]) + (" ..." if len(unstated) > 4 else "")
        warn(path, "L35", f"{len(unstated)} of {len(feats)} relief feature(s) state no "
                          f"`confidence` ({shown}). A magnitude with no source is "
                          f"indistinguishable from a measured one. Tokens: measured, "
                          f"photo-measured, drawing, datasheet, registry, borrowed, "
                          f"estimated, known-wrong")
    for f in feats:
        if f.get("confidence") != "borrowed":
            continue
        node, src = f["node"], (f.get("source") or "")
        m = re.match(r"([a-z0-9-]+/[a-z0-9-]+@\d+)", src)
        if not m:
            err(path, "L36", f"{node}: confidence `borrowed` but `source` does not begin "
                             f"with the origin ref. Write it as '<ns>/<name>@<major> - why', "
                             f"so the claim can be checked; or use `estimated`")
            continue
        ref = m.group(1)
        found = resolve_component(ref, lib_roots)
        if not found:
            err(path, "L36", f"{node}: `borrowed` from {ref}, which does not resolve")
            continue
        mine = _feature_magnitude(f)
        origin = load_yaml(found) or {}
        ofeats = ((origin.get("relief") or {}).get("features") or [])
        matches = [o for o in ofeats
                   if mine and (_feature_magnitude(o) or (None, None))[1] == mine[1]]
        if not matches:
            err(path, "L36", f"{node}: `borrowed` from {ref}, which carries no relief "
                             f"magnitude of {mine[1] if mine else '?'}. Either the ref is "
                             f"wrong or the number did not come from there")
            continue
        if not any(o.get("confidence") in CONFIDENCE_MEASURED for o in matches):
            got = sorted({o.get("confidence") or "unstated" for o in matches})
            err(path, "L36", f"{node}: `borrowed` asserts {ref} MEASURED this magnitude, "
                             f"and there it is {'/'.join(got)}. Borrowing does not create a "
                             f"measurement - use `estimated` and say in `source` that the "
                             f"origin did not measure it either")


LAMP_STATES = {"ok", "fail", "fault"}


def _declared_states(data):
    st = data.get("states")
    if isinstance(st, dict):
        return set(st)
    if isinstance(st, list):
        return {s if isinstance(s, str) else str((s or {}).get("name", "")) for s in st}
    return set()


def _lights_up(path, data, lib_roots, seen):
    """Does anything in this part, or anything it composes, read --led-color?"""
    for f in sorted(Path(path).parent.glob("skins/*.svg")):
        if "var(--led-color" in f.read_text():
            return True
    for q in (data.get("parts") or []):
        ref = (q.get("ref") or "").split(":")[0]
        if not ref or ref in seen:
            continue
        seen.add(ref)
        cp = resolve_component(ref, lib_roots)
        sub = load_yaml(cp) if cp else None
        if sub and _lights_up(cp, sub, lib_roots, seen):
            return True
    return False


def lint_component_states_render(path, data, lib_roots):
    """L47: a state nothing draws is a state the viewer offers and cannot show.

    Forty components declared `ok`/`fail` and drew the lamp as a flat
    `fill="#0f1113"`. The states were declared, the CSS was generated, the viewer
    offered them, and clicking one changed nothing - a lamp only lights if some
    element fills from `var(--led-color, ...)`.

    Invisible to everything else by construction. `spec/tests/test_state_css.py`
    checks the OPPOSITE direction, that a state has a CSS class; this is the half
    that asks whether any pixel consumes it.

    TWO SHAPES, ONE RULE, DIFFERENT SENTENCES, because the fix differs. A part
    that draws a lamp and fills it statically wants the fill changed. A part that
    declares a lamp state and draws no lamp at all wants either a lamp or one
    fewer state - and which is right is a question about the hardware, so the
    message asks rather than assumes.

    SEARCHED THROUGH COMPOSITION. A supply whose lamp is a composed `led-dot`
    lights correctly and must not be reported; checking only the part's own skin
    called 166 components broken when 37 were.
    """
    lamps = _declared_states(data) & LAMP_STATES
    if not lamps:
        return
    if _lights_up(path, data, lib_roots, set()):
        return
    art = "".join(f.read_text() for f in sorted(Path(path).parent.glob("skins/*.svg")))
    if not art:
        return
    drawn = sorted(set(re.findall(r'id="([^"]*(?:led|lamp)[^"]*)"', art, re.I)))
    named = ", ".join(sorted(lamps))
    if drawn:
        warn(path, "L47", f"declares {named} and draws {len(drawn)} lamp element(s) "
             f"({', '.join(drawn[:3])}) that never light - none fills from "
             "var(--led-color, ...), so the viewer offers a state the drawing "
             "cannot show")
    else:
        warn(path, "L47", f"declares {named} and draws no lamp at all. Either the "
             "drawing is missing the indicator, or the part has none and should "
             "not declare the state - which of those is a question about the "
             "hardware")


def lint_component_bays_drawn(path, data, lib_roots):
    """L48: a bay the contract declares but the skin never draws orphans its
    occupant.

    render.py stamps a nested `data-path` on the skin element whose id matches the
    bay id. If no skin drew one, there is nothing to stamp: the seated module's
    parent resolves to nothing and the Explorer hangs it off the chassis root,
    several tiers from where the hardware puts it. The MX review hit this on eight
    carriers at once.

    NOTHING ELSE ASKS THIS. The contract validates, the occupant resolves, the
    render succeeds and the SVG is well-formed - the only symptom is a tree that
    reads wrong, which is exactly the kind of defect that survives every gate and
    is found by a human scrolling a panel.

    ZERO HITS TODAY, deliberately. The eight carriers were fixed before this was
    written and the rest of the library was already right, so this rule is a latch
    on a door that is currently shut. It is worth having because the failure is
    silent and the fix - one `<rect id="bay-1">` - is invisible until someone
    opens the tree.
    """
    bays = data.get("bays")
    if not isinstance(bays, dict) or not bays:
        return
    skins = sorted(Path(path).parent.glob("skins/*.svg"))
    if not skins:
        return
    art = "".join(f.read_text() for f in skins)
    ids = set(re.findall(r'id="([^"]+)"', art))
    missing = [b for b in sorted(bays) if b not in ids]
    if missing:
        warn(path, "L48", f"declares bay(s) {', '.join(missing[:4])} that no skin "
             "draws an element for. The renderer nests a seated module under the "
             "element whose id matches its bay; with none, the occupant is hung "
             "off the root instead of inside this part")


_SVG_NS = "{http://www.w3.org/2000/svg}"
_DRAWABLE = ("rect", "circle", "ellipse", "polygon", "path", "text", "line")


def _svg_rot(b, el):
    """SVG rotates about the point named in the transform, not the box centre.

    Getting this wrong called 38 correctly-placed labels off-canvas: a vertical
    model name is rotated about its own anchor, so spinning its box about its
    centre throws it clear of the part.
    """
    m = re.match(r"rotate\(\s*(-?[\d.]+)(?:[ ,]+(-?[\d.]+)[ ,]+(-?[\d.]+))?\s*\)",
                 (el.get("transform") or "").strip())
    if not m:
        return b
    a = math.radians(float(m.group(1)))
    cx = float(m.group(2) or 0.0)
    cy = float(m.group(3) or 0.0)
    ca, sa = math.cos(a), math.sin(a)
    pts = [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca)
           for x in (b[0], b[2]) for y in (b[1], b[3])]
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _svg_box(tag, el):
    """Bounding box of one drawable, in the skin's own user units.

    Text is ESTIMATED - 0.6em per character - because measuring a glyph run
    needs a font engine. That estimate runs about 20% wide, which is why the
    thresholds below are loose and why nothing here reports a near miss.
    """
    def g(k, d=0.0):
        try:
            return float(el.get(k, d) or d)
        except (TypeError, ValueError):
            return d
    if tag == "rect":
        return _svg_rot((g("x"), g("y"), g("x") + g("width"), g("y") + g("height")), el)
    if tag in ("circle", "ellipse"):
        rx = g("r") or g("rx")
        ry = g("r") or g("ry")
        cx, cy = g("cx"), g("cy")
        return _svg_rot((cx - rx, cy - ry, cx + rx, cy + ry), el)
    if tag == "polygon":
        pts = [float(v) for v in re.findall(r"-?[\d.]+", el.get("points", ""))]
        if len(pts) < 4:
            return None
        return _svg_rot((min(pts[0::2]), min(pts[1::2]),
                         max(pts[0::2]), max(pts[1::2])), el)
    if tag == "text":
        txt = "".join(el.itertext()).strip()
        if not txt:
            return None
        fs = g("font-size", 3.0) or 3.0
        w = 0.6 * fs * len(txt)
        x = g("x")
        anchor = el.get("text-anchor", "start")
        x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        y = g("y")
        return _svg_rot((x0, y - fs * 0.8, x0 + w, y + fs * 0.2), el)
    return None


def _svg_drawables(el, fill=None, out=None):
    """Every drawable in paint order, carrying the fill it inherits."""
    out = [] if out is None else out
    for ch in el:
        tag = ch.tag.replace(_SVG_NS, "")
        inherited = ch.get("fill", fill)
        if tag == "g":
            _svg_drawables(ch, inherited, out)
        elif tag in _DRAWABLE:
            out.append((tag, ch, inherited))
    return out


def _paints_over(tag, el, fill):
    if tag in ("text", "line") or not fill or fill == "none":
        return False
    for k in ("opacity", "fill-opacity"):
        try:
            if float(el.get(k, 1) or 1) < 0.9:
                return False
        except (TypeError, ValueError):
            pass
    return True


def lint_component_skin_printing(path, data, lib_roots):
    """L50: printing inside a skin that cannot be read is printing that is not there.

    THE SURFACE NO RULE INSPECTED. Four reviews running, the defects humans find
    are two correct things in one place, and every rule that answers that -
    L13 on a device, L46 between composed parts, L48 on carriers - stops at the
    edge of a component's own SVG. Inside the skin, the modeller is alone. The
    reviews call this the highest-value single check.

    L44 is this rule's counterpart one level up, where it asks whether a device's
    silkscreen runs off the face. This asks the same of a part's own printing:
    does it fall off the part, or vanish under paint applied after it.

    LOOSE ON PURPOSE. Text width is estimated at 0.6em per character with no font
    engine, which runs about 20% wide, so a rule that reported near misses would
    report the estimate. Measured over 487 skins: the deepest burial is 22% (a
    STATUS legend beside its own lamp, entirely legible) and overhang runs to 34%
    on long model names printed to the panel edge - then jumps to `common/pull-tab`,
    whose SERVICE INFO is set at 5.44 in a 16-wide tab and overflows by more than
    double. Half is the empty band between the artefacts and the one real defect.
    """
    for skin in sorted(Path(path).parent.glob("skins/*.svg")):
        try:
            root = ET.parse(skin).getroot()
        except (ET.ParseError, OSError):
            continue          # a malformed skin is already _skin_checks' business
        items = [(t, e, f, _svg_box(t, e)) for t, e, f in _svg_drawables(root)]
        vb = (root.get("viewBox") or "").split()
        face = None
        if len(vb) == 4:
            try:
                vx, vy, vw, vh = (float(v) for v in vb)
                face = (vx, vy, vx + vw, vy + vh)
            except ValueError:
                face = None

        for i, (tag, el, fill, b) in enumerate(items):
            if tag != "text" or not b:
                continue
            area = (b[2] - b[0]) * (b[3] - b[1])
            if area <= 0:
                continue
            words = "".join(el.itertext()).strip()[:24]
            if face:
                inside = (max(0.0, min(b[2], face[2]) - max(b[0], face[0]))
                          * max(0.0, min(b[3], face[3]) - max(b[1], face[1])))
                if inside / area < 0.5:
                    warn(path, "L50", f"{skin.name}: {words!r} is set at "
                         f"font-size {el.get('font-size', '?')} and runs mostly off "
                         f"the part - about {inside/area*100:.0f}% of it lands on the "
                         "face. Printing that falls off the edge is printing the "
                         "viewer never sees")
                    continue
            for tag2, el2, fill2, b2 in items[i + 1:]:
                if not b2 or not _paints_over(tag2, el2, fill2):
                    continue
                ox = min(b[2], b2[2]) - max(b[0], b2[0])
                oy = min(b[3], b2[3]) - max(b[1], b2[1])
                if ox <= 0 or oy <= 0:
                    continue
                if (ox * oy) / area >= 0.5:
                    warn(path, "L50", f"{skin.name}: {words!r} is painted over by "
                         f"<{tag2} id={el2.get('id', '')!r}> drawn after it, which "
                         f"covers {(ox*oy)/area*100:.0f}% of the text. Two correct "
                         "things in one place is the defect humans keep finding and "
                         "no rule inside a skin looked for")
                    break


def lint_component_collisions(path, data, lib_roots):
    """L46: two things a component composes must not be drawn in one place.

    THIS IS THE FAMILY EVERY HUMAN-CAUGHT DEFECT HAS BEEN IN. The MX review's own
    tally: ears over the convention, decor over ports, text over honeycomb, a USB
    outside its hole, ejector levers over model-name chips. The gates check that a
    thing is present and where a source says; nothing checked that two correct
    things are not in the same place. L13 does it for a device's placements; this
    is the same question one level down, inside a component.

    The worked case is the MX960's vertical 40GE DPC: sfp-ganged cages stacked on
    a 7.2 mm pitch when a rotated cage is 14.25 mm tall, so they overlapped 2:1
    and rendered as doubled-up ports.

    A FRACTION, NOT A DISTANCE, and the library says why. Measuring the overlap of
    every composed pair gives 261 hairline ones and two gross: ganged cages
    legitimately share a wall and abut to a hair, so an absolute tolerance either
    floods or misses. As a fraction of the smaller part the distribution is empty
    between 10 and 50 percent - hairline contact on one side, real collision on
    the other - so a threshold in that gap separates them with nothing near it.
    """
    boxes = []
    for q in (data.get("parts") or []):
        if not q.get("at") or not q.get("ref"):
            continue
        size = _instance_size(q["ref"], lib_roots)
        if not size:
            continue
        w, h = size
        x, y = q["at"]
        if q.get("rotate") in (90, 270, -90):
            cx, cy = x + w / 2, y + h / 2
            x, y, w, h = cx - h / 2, cy - w / 2, h, w
        boxes.append((q.get("id", "?"), x, y, x + w, y + h))

    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            ox = min(a[3], b[3]) - max(a[1], b[1])
            oy = min(a[4], b[4]) - max(a[2], b[2])
            if ox <= 0 or oy <= 0:
                continue
            smaller = min((a[3] - a[1]) * (a[4] - a[2]), (b[3] - b[1]) * (b[4] - b[2]))
            if smaller <= 0:
                continue
            frac = (ox * oy) / smaller
            if frac >= 0.25:
                warn(path, "L46", f"composed parts {a[0]} and {b[0]} overlap by "
                     f"{ox:.2f}x{oy:.2f}mm, which is {frac*100:.0f}% of the smaller "
                     "one. Two parts drawn in one place is the commonest defect a "
                     "human finds and no rule saw; if the layering is deliberate, "
                     "say so in provenance")


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
        sub = load_yaml(found)
        if part["ref"] in seen:
            err(path, "L10", f"composition cycle via {part['ref']}")
            continue
        lint_component_parts(found, sub, lib_roots, depth + 1, seen | {part["ref"]})


# PARTS APPLIED OVER THE PANEL RATHER THAN PRINTED INTO IT. Kept in step with
# render.py's list of the same name, which is what stops `--without silkscreen`
# erasing a label's text along with the chassis printing.
APPLIED_CLASSES = {"sticker", "label", "marking"}


def _ungrouped_text(root):
    """How many <text> nodes sit outside a silkscreen group.

    Ancestry, not parentage: a run may be wrapped several levels down inside a
    part's own sub-group, and that still counts as grouped.
    """
    ns = "{http://www.w3.org/2000/svg}"
    parent = {c: p for p in root.iter() for c in p}

    def grouped(e):
        n = e
        while n is not None:
            if (n.get("id") or "").endswith("silkscreen") or n.get("data-class") == "silkscreen":
                return True
            n = parent.get(n)
        return False

    return sum(1 for e in root.iter() if e.tag == ns + "text" and not grouped(e))


def _skin_checks(path, data):
    skins_dir = path.parent / "skins"
    contracted = set((data.get("elements") or {}).keys())
    # L38 SWEEPS EVERY FILE UNDER skins/, not the ones `skins:` names.
    #
    # Scoped to the declared list it read as passing and was blind: `skins:` names
    # the faceplate variants, while body-top, body-left and the rest are reached
    # through the relief body and never appear in it. Twelve of the thirty-three
    # skins this rule was written for are body skins, so the first version agreed
    # the library was clean while unable to open a third of the evidence. A rule
    # that cannot see a file does not just miss it, it certifies it.
    if (data.get("class") or "") not in APPLIED_CLASSES:
        for sp in sorted(skins_dir.glob("*.svg")) if skins_dir.exists() else []:
            try:
                _, root = skin_ids(sp)
            except Exception:
                continue          # L3 reports an unparseable skin
            loose = _ungrouped_text(root)
            if loose:
                err(sp, "L38", f"{loose} printed text node(s) outside a silkscreen "
                               "group. Wrap them in <g id=\"silkscreen\"> - one "
                               "contiguous run at a time, because paint order is "
                               "meaning: consolidating a file\'s text into one group "
                               "moved an OK legend behind the box it is printed on")
    for skin in data.get("skins", ["default"]):
        sp = skins_dir / f"{skin}.svg"
        if not sp.exists():
            err(path, "L3", f"declared skin missing: {sp.name}")
            continue
        ids, root = skin_ids(sp)
        # L38 - printed text belongs in a silkscreen group.
        #
        # `--without silkscreen` gets the right answer today via a backstop that
        # sweeps any remaining <text>, which is sound - printed text on a faceplate
        # IS silkscreen whether or not its author grouped it - but it means the
        # convention is unenforced, and an unenforced convention is one skin away
        # from not being one. Grouping is what makes the layer CHECKABLE rather
        # than merely correct: a tree can list a part's legends only if the drawing
        # says which nodes are legends.
        #
        # A STICKER IS THE EXCEPTION AND IS NOT AN OVERSIGHT. Silkscreen is ink on
        # the metal; a label is a separate part applied over it, and its printing
        # belongs to that part the way a cage's walls belong to the cage. Asking a
        # label to group its own text as silkscreen would be asking it to declare
        # itself printing on something else.
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
        d = load_yaml(c) or {}
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
        _mate_check(path, f"{view_name}/{p['id']}", p["ref"], host["ref"], lib_roots)


def _mate_check(path, where, occ_ref, host_ref, lib_roots):
    """Do these two agree on an interface? Shared by `mate-to` and `occupants:`.

    One check, called twice, because a second copy would be one bad afternoon
    away from disagreeing with the first about what fits - and the whole value
    of an interface key is that everybody asks it the same question.
    """
    hp, op = resolve_component(host_ref, lib_roots), resolve_component(occ_ref, lib_roots)
    if not hp or not op:
        return
    hc, oc = load_yaml(hp), load_yaml(op)

    def _res(ref):
        q = resolve_component(ref, lib_roots)
        return load_yaml(q) if q else None

    # THE HOST MAY PRESENT ITS INTERFACE THROUGH A COMPOSED APERTURE. A vendor
    # cage wraps `std/qsfp-ganged`, which is where the interface lives; reading
    # only the wrapper's own key is why 7,058 ports in this library could not be
    # populated while the mechanism to populate them worked.
    want, _ = presented_interface(hc, _res)
    have = oc.get("mates")
    if not have:
        err(path, "L12", f"{where}: {occ_ref} declares no 'mates', "
                         "so it cannot occupy anything")
    if not want:
        err(path, "L12", f"{where}: host {host_ref} presents no "
                         "'interface', so nothing can mate into it")
    if want and have and want != have:
        err(path, "L12", f"{where}: {occ_ref} mates {have!r} but "
                         f"{host_ref} presents {want!r}")


def lint_device_occupants(path, data, lib_roots):
    """L12 for `occupants:`, which the per-view pass cannot see.

    An occupant lives in a CONFIGURATION and names a receptacle that may be in
    any view, so the view-scoped check never met it: a QSFP transceiver declared
    into an SFP cage, and an occupant naming a port that does not exist, both
    linted clean. The renderer expands occupants into `mate-to` placements, so
    the drawing was right about position and silent about fit.

    Hosts are gathered across every view for the same reason - a configuration
    describes the whole device, and `port-4` being on the front is not something
    the configuration should have to know.
    """
    hosts = {}
    for vname, view in (data.get("views") or {}).items():
        for q in view_parts(view or {})["placements"]:
            hosts.setdefault(q.get("id"), (vname, q))
    for cname, cfg in (data.get("configurations") or {}).items():
        for host_id, spec in ((cfg or {}).get("occupants") or {}).items():
            ref = spec if isinstance(spec, str) else (spec or {}).get("ref")
            where = f"configurations/{cname}/occupants/{host_id}"
            if host_id not in hosts:
                err(path, "L12", f"{where}: names no placement in any view of this "
                                 "device. An occupant plugs into something")
                continue
            vname, host = hosts[host_id]
            if not host.get("at"):
                err(path, "L12", f"{where}: host has no explicit position "
                                 "(occupants cannot host occupants)")
                continue
            if ref:
                _mate_check(path, where, ref, host["ref"], lib_roots)


def lint_device_overlap(path, view_name, view, lib_roots):
    """L13: two placed components must not occupy the same faceplate area.

    Overlap is almost always a sizing mistake rather than a drawing choice: a
    part measured off one device dropped into a tighter gap on another. It is
    invisible in the flat SVG (the later node just paints over the earlier one)
    but obvious in 3D, where an LED dome hangs over the lip of a port cavity.

    Occupants are exempt - a transceiver placed with mate-to is *supposed* to
    sit inside its host's aperture.

    So are two parts that are never both present. `only-in` scopes a piece of
    metal to a set of configurations, and a C40G ordered for AC has one bolted
    panel exactly where a DC chassis has its two power-entry openings. Comparing
    them is comparing two different chassis: the AC panel and the DC bays overlap
    by their whole area and never coexist in any rendered view. Without this the
    rule rejects the correct model, which is the more dangerous direction - an
    author reading a hard error concludes the arrangement is wrong.
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
        sz = (load_yaml(cp) or {}).get("size") or {}
        if "w" not in sz or "h" not in sz:
            continue
        w, h = sz["w"], sz["h"]
        x, y = p["at"][0], p["at"][1]
        # a quarter-turn swaps the footprint about the component centre - the same
        # transform render.py applies when it computes view extents
        if p.get("rotate") in (90, 270, -90):
            cx, cy = x + w / 2, y + h / 2
            x, y, w, h = cx - h / 2, cy - w / 2, h, w
        boxes.append((p["id"], x, y, w, h, p.get("only-in")))
    # Bays occupy faceplate area exactly as placements do. Leaving them out let a
    # rivet row sit on top of five fan bays without a word from the linter.
    for b in view_parts(view)["bays"]:
        # NOT transposed for `rotate`. A placement's size comes from the unrotated
        # component, so a quarter turn swaps it; a bay's size is authored as the
        # ON-PANEL footprint already, and `rotate` only spins the occupant inside
        # it. Transposing here reported the C40G's six horizontal card bays as
        # overlapping each other by 300mm.
        boxes.append((b["id"], b["at"][0], b["at"][1], b["size"]["w"], b["size"]["h"],
                      b.get("only-in")))
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
                # never both present, so never actually overlapping. Absent
                # `only-in` means every configuration, which intersects everything
                if a[5] and b[5] and not (set(a[5]) & set(b[5])):
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


def _footprint(item, lib_roots):
    """Where a bay or placement actually sits, as (x0, y0, x1, y1), or None.

    A bay states its own size; a placement borrows its component's and turns it
    with `rotate`, the same quarter-turn L13 applies about the centre.
    """
    at = item.get("at")
    if not at:
        return None
    sz = item.get("size")
    if isinstance(sz, dict):
        w, h = sz.get("w"), sz.get("h")
    elif isinstance(sz, (list, tuple)) and len(sz) >= 2:
        w, h = sz[0], sz[1]
    else:
        cp = resolve_component(item.get("ref", ""), lib_roots)
        spec = (load_yaml(cp) or {}) if cp else {}
        csz = spec.get("size") or {}
        w, h = csz.get("w"), csz.get("h")
    if not w or not h:
        return None
    x, y = at[0], at[1]
    if item.get("rotate") in (90, 270, -90):
        cx, cy = x + w / 2, y + h / 2
        x, y, w, h = cx - h / 2, cy - w / 2, h, w
    return (x, y, x + w, y + h)


def lint_device_cutouts(path, view_name, view, lib_roots):
    """L39: the panel's holes must agree with what goes in them.

    Cutouts became real data so that a whole class of error could be checked
    rather than eyeballed - the errors that have actually bitten this project,
    which are a chassis measured 12% too wide, forty-eight ports on a wrong
    pitch, and a legend printed where a module would cover it. Gate 2 of the
    modelling skill says "render, overlay, count them"; this is that gate as a
    rule.

    WHAT A CLEAN RUN DOES AND DOES NOT MEAN. Twelve of the library's twenty
    devices declare no cutouts at all, and every check here is silent on them -
    there is nothing to disagree with. A pass means the eight devices that DO
    declare holes are consistent; it says nothing whatever about the other
    twelve, and reading it as library-wide correctness is the mistake this
    docstring exists to prevent.

    `every cutout is filled` is deliberately NOT among the checks. Thirty-three
    cutouts in the library are named by nothing, and all thirty-three are real:
    Cisco power shelves, fan-tray openings, ESD jacks, ground pads and card
    cages, which are holes in the metal with no module modelled behind them. A
    rule there would report correct modelling as a defect.
    """
    panel = (view.get("panel") or {})
    cuts = panel.get("cutouts") or []
    if not cuts:
        return
    boxes = {c["id"]: (c["at"][0], c["at"][1],
                       c["at"][0] + c["size"][0], c["at"][1] + c["size"][1])
             for c in cuts if c.get("at") and c.get("size")}

    # 1. no two holes in the same piece of metal
    ids = sorted(boxes)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ax0, ay0, ax1, ay1 = boxes[a]
            bx0, by0, bx1, by1 = boxes[b]
            ix = min(ax1, bx1) - max(ax0, bx0)
            iy = min(ay1, by1) - max(ay0, by0)
            if ix > 0.001 and iy > 0.001:
                err(path, "L39", f"{view_name}: cutouts {a} and {b} overlap by "
                                 f"{ix:.2f} x {iy:.2f} mm. Two holes cannot share metal")

    placements = view_parts(view)["placements"]
    by_id = {q.get("id"): q for q in placements}

    # 2. a hole matches the standard of whatever sits in it. A rotated part turns
    #    its opening with it, which is why this compares against the rotated
    #    footprint rather than the registry's own orientation.
    for cid, c in ((c["id"], c) for c in cuts):
        q = by_id.get(cid)
        if not q:
            continue
        cp = resolve_component(q.get("ref", ""), lib_roots)
        spec = (load_yaml(cp) or {}) if cp else {}
        conf = spec.get("conforms")
        std = STANDARDS.get(conf) if isinstance(conf, str) else None
        if not std or std.get("w") is None:
            continue
        sw, sh = std["w"], std["h"]
        if ((q.get("rotate") or 0) % 180) == 90:
            sw, sh = sh, sw
        cw, ch = c["size"]
        if abs(cw - sw) > 0.3 or abs(ch - sh) > 0.3:
            err(path, "L39", f"{view_name}: cutout {cid} is {cw:g} x {ch:g} but its "
                             f"occupant conforms to {conf} ({sw:g} x {sh:g}). The hole "
                             "and the part disagree")

    # 2b. THE PART HAS TO LAND ON THE HOLE, which is a different question from
    #     whether it is the right size for it, and 2 above only asks the second.
    #     `rotate:` spins a placement about its OWN pre-rotation centre, so the
    #     author has to back-compute `at` - and the MX204's USB, correctly sized
    #     and correctly rotated, sat 3.75 mm outside its own cutout. Nothing saw
    #     it: the sizes agreed, so 2 passed, and no other rule compares a
    #     placement's LANDED box with the opening it is supposed to fill.
    #
    #     CONCENTRIC, NOT COVERING. This asked whether the part COVERS the hole,
    #     which is right for a module in a cage and wrong for everything with
    #     clearance: an ASR 9922 fan tray is 38.1 tall in a 41.5 opening because
    #     that is how trays fit, and a tray with end grips is WIDER than its
    #     opening because the grips land on the metal. Both are correct hardware
    #     and both were reported. What the USB actually did was sit off-centre,
    #     so that is what is measured now.
    #
    #     Concentricity is also the cleanly separated signal: across 236 landed
    #     parts, 90% are exactly concentric and the 99th percentile is 8.8% of
    #     the opening, so a tolerance of 5% of the smaller side (floored at
    #     0.3mm, which is the drawing precision) sits above the noise and still
    #     catches a 12mm USB placed 3.75mm out.
    for cid, c in ((c["id"], c) for c in cuts):
        q = by_id.get(cid)
        if not q or not q.get("at") or not c.get("at") or not c.get("size"):
            continue
        size = _instance_size(q.get("ref"), lib_roots)
        if not size:
            continue
        w, h = size
        x, y = q["at"]
        if q.get("rotate") in (90, 270, -90):
            cx, cy = x + w / 2, y + h / 2
            x, y, w, h = cx - h / 2, cy - w / 2, h, w
        cw, ch = c["size"]
        tol = max(0.3, 0.05 * min(cw, ch))
        miss = max(abs((x + w / 2) - (c["at"][0] + cw / 2)),
                   abs((y + h / 2) - (c["at"][1] + ch / 2)))
        if miss > tol + 1e-6:
            # WARN, NOT ERR. The old coverage test was an error because a part
            # landing outside its hole is a broken drawing. Off-centre-ness is a
            # disagreement between two measurements, which is the same family as
            # L39's other findings and is recorded the same way.
            warn(path, "L39", f"{view_name}: {cid} does not sit in its own cutout - "
                             f"the part lands at ({x:g}, {y:g}) {w:g} x {h:g} and the "
                             f"hole is at ({c['at'][0]:g}, {c['at'][1]:g}) {cw:g} x {ch:g}, "
                             f"off-centre by {miss:.2f}mm against a {tol:.2f}mm tolerance. "
                             "A part may be smaller than its opening (clearance) or larger "
                             "(a bezel or grips landing on the metal), but it sits centred "
                             "in it. `rotate:` pivots on the part's own centre, so `at` has "
                             "to be recomputed after turning it")

    # 3. you cannot print on a hole
    for m in (view.get("silkscreen") or []):
        if m.get("path") or not m.get("at"):
            continue
        mx, my = m["at"]
        for cid, (x0, y0, x1, y1) in boxes.items():
            if x0 < mx < x1 and y0 < my < y1:
                err(path, "L39", f"{view_name}: silkscreen {str(m.get('text'))[:20]!r} "
                                 f"is printed inside cutout {cid}. There is no metal "
                                 "there to print on")
                break

    # 4. A HOLE WITH NOTHING IN IT. Somebody put a hole in the metal, and if the
    #    model has nothing to put through it the model is unfinished, not the
    #    chassis - the ASR 9904, 9906, 9910 and 9912 all cut a power-shelf
    #    opening and none of them models a shelf, a cover or a module.
    #
    #    SATISFIED BY COVERAGE, NOT BY NAME. A cage is a hole that many things
    #    fill: the ASR 9912's `lc-cage` holds ten slots, none of them called
    #    `lc-cage`. And not by containment either, which is the shape this was
    #    first written in and got wrong - a line card's faceplate is 403.1 mm
    #    tall over a 357.35 mm opening, because a faceplate COVERS an aperture
    #    rather than fitting inside it, so containment reported seven correctly
    #    modelled cages as empty.
    #
    #    A warning: it reports work not done rather than work done wrongly, and
    #    what belongs in a given hole is a modelling question with a source
    #    behind it, not something a linter can decide.
    filled = {q.get("id") for q in placements} | {
        b.get("id") for b in view_parts(view)["bays"]}
    for cid, cb in boxes.items():
        if cid in filled:
            continue
        area = (cb[2] - cb[0]) * (cb[3] - cb[1])
        if area <= 0:
            continue
        covered = 0.0
        for q in placements + view_parts(view)["bays"]:
            qb = _footprint(q, lib_roots)
            if not qb:
                continue
            ix = min(cb[2], qb[2]) - max(cb[0], qb[0])
            iy = min(cb[3], qb[3]) - max(cb[1], qb[1])
            if ix > 0 and iy > 0:
                covered += ix * iy
        if covered / area < 0.5:
            warn(path, "L39", f"{view_name}: cutout {cid} has nothing in it. A hole in "
                              "the metal means something goes through it - a module, a "
                              "bay, a lug, or the cover that blanks it off")

    # 5. a port on a panel that has been punched should have its own hole.
    #    WARNING, not an error: it reports incomplete work rather than wrong work,
    #    and the ASR 9001 has fifteen of them because it declares two cutouts for
    #    clock connectors and none for its ports. Restricted to `port` because no
    #    lamp in the library has a cutout and no button does either - that is a
    #    modelling convention held consistently, not 163 omissions.
    for q in placements:
        cp = resolve_component(q.get("ref", ""), lib_roots)
        if not cp or (load_yaml(cp) or {}).get("class") != "port":
            continue
        if q.get("mate-to"):
            continue          # an occupant sits in its host, not in the metal
        if q.get("id") not in boxes:
            warn(path, "L39", f"{view_name}: port {q.get('id')} has no cutout, on a "
                              "panel that declares them. Either punch it or say why")


# The cages an optic plugs INTO. A management cluster of RJ45, USB and console
# takes no pluggable optic and is not asked about one, and neither is the fixed
# LC fibre on a passive mux - `media: fiber` is a bonded adapter, not a socket.
# Media that name a pluggable cage. A form factor missing from this set is
# invisible to L40 in BOTH directions: its groups are never asked which optics
# run in them, and an `optics-<media>` key naming it reads as unreachable
# knowledge. So a device modelled correctly with a new form factor gets accused
# of the defect it does not have - which is how `osfp` was found, on the first
# 800G box the library carried.
PLUGGABLE_CAGES = {"sfp", "sfp-plus", "sfp28", "sfp-dd", "qsfp", "qsfp28",
                   "qsfp56", "qsfp-dd", "osfp", "xfp", "cfp", "cfp2"}


def _bay_pitch_is_uneven(gaps):
    """Do these consecutive gaps look mis-measured, or like a real cage split?

    Returns the spread as a fraction when the pitch disagrees with itself, and
    None when the layout is a regular pitch broken by wider cage divisions.
    """
    hi, lo = max(gaps), min(gaps)
    if hi <= 0.05 or (hi - lo) / hi <= 0.15:
        return None
    tol = max(0.5, 0.05 * abs(hi))
    clusters = []
    for g in sorted(gaps):
        if clusters and abs(g - clusters[-1][0]) <= tol:
            clusters[-1].append(g)
        else:
            clusters.append([g])
    # one pitch plus a wider break, and the break is the minority: an MX960's
    # SCB column, an MX10016's four-slot cages. Real metal, evenly cut.
    if (len(clusters) == 2 and len(clusters[0]) >= 2
            and len(clusters[0]) > len(clusters[1])):
        return None
    return (hi - lo) / hi


def lint_device_bay_pitch(path, data):
    """L49: members of one group, cut to one size, sit on one pitch.

    The MX304's fan bays were modelled unevenly spaced because photo edge
    detection assigned fan 1's edges to its grille internals - and the provenance
    then ASSERTED the asymmetry as a finding, which is what made it survive. Lint
    passed, the render matched the mis-read overlay, and the sentence read like
    diligence. It was caught by a reviewer's physical-plausibility instinct:
    routers do not stagger their fans.

    SHAPE, NOT SPREAD, and the library is why. Spread alone (>15%, as the review
    proposed) flags three groups today and all three are correct: the MX960's
    60mm SCB column between slots 5 and 6, and the MX10008/MX10016 cage
    divisions. Those share a shape - one pitch, plus a wider break that is the
    minority - which real sheet metal has and a mis-measurement does not. The
    MX304's two gaps of 15.0 and 38.8mm had no majority to agree with.

    Silent on the whole library; fires on the MX304 as it was written.
    """
    for vname, view in (data.get("views") or {}).items():
        groups = {}
        for b in view_parts(view or {})["bays"]:
            if b.get("group") and b.get("at") and b.get("size"):
                groups.setdefault(b["group"], []).append(b)
        for gid, bays in sorted(groups.items()):
            if len(bays) < 3:
                continue
            sizes = set()
            for b in bays:
                sz = b["size"]
                pair = ((sz.get("w"), sz.get("h")) if isinstance(sz, dict)
                        else tuple(sz[:2]) if isinstance(sz, (list, tuple)) else None)
                sizes.add(None if not pair or None in pair
                          else (round(pair[0], 2), round(pair[1], 2)))
            # different-size members have no common pitch to disagree about
            if len(sizes) != 1 or None in sizes:
                continue
            w, h = sizes.pop()
            for axis, extent, name in ((0, w, "horizontally"), (1, h, "vertically")):
                # only a single row or column has a pitch to speak of
                if len({round(b["at"][1 - axis], 1) for b in bays}) != 1:
                    continue
                pos = sorted(b["at"][axis] for b in bays)
                gaps = [round(pos[i + 1] - pos[i] - extent, 3)
                        for i in range(len(pos) - 1)]
                if len(gaps) < 2:
                    continue
                spread = _bay_pitch_is_uneven(gaps)
                if spread:
                    warn(path, "L49", f"{vname}: the {len(bays)} same-size bays of "
                         f"group {gid} are spaced {name} by {min(gaps):.1f} to "
                         f"{max(gaps):.1f}mm, a {spread*100:.0f}% disagreement with "
                         "no majority pitch. Uneven spacing within one group is "
                         "nearly always a mis-measurement - re-measure against a "
                         "second image before recording it as a finding")


def lint_device_rack_ears(path, data):
    """L43: a body as wide as the rack face still has its ears on.

    The library draws devices WITHOUT rack ears - the modelled body is the metal
    between the ear fold lines - and that convention lived in reviewers' heads.
    The MX204 has integral ear flanges and its own table calls the chassis 19
    inches, so the model faithfully included them and nothing said otherwise.

    Structural and cheap: a front or rear face measuring 480-487 mm is almost
    certainly a rack face rather than a body. The widest body in the library
    today is 443 mm, so this costs nothing until it fires.
    """
    for vname, view in (data.get("views") or {}).items():
        if vname not in ("front", "rear"):
            continue
        w = ((view or {}).get("size") or {}).get("w")
        if w and 480.0 <= float(w) <= 487.0:
            warn(path, "L43", f"{vname}: view is {w} wide, which is the 19-inch "
                 "rack face, not a body. Ears are never drawn - measure between "
                 "the fold lines and record the ear extent in provenance")


def _decor_box(d):
    at, sz = d.get("at"), d.get("size")
    if not at or not sz:
        return None
    w, h = (sz["w"], sz["h"]) if isinstance(sz, dict) else (sz[0], sz[1])
    return (at[0], at[1], at[0] + w, at[1] + h)


def lint_device_decor(path, view_name, view, lib_roots):
    """L44: decor is background, and background still has to be true.

    TWO CHECKS, AND ONE OF THEM IS DELIBERATELY NOT THE OBVIOUS ONE. Erroring on
    any decor that a feature overlaps was the first idea and is wrong: decor IS
    what sits behind things, and 206 overlaps across 11 devices are correct by
    construction - a grille band behind a power shelf, a brand band under a
    wordmark, a colour strip behind a port block. A rule that rejects the model
    on eleven devices to catch one is the accusing direction, and worse than
    silence.

    What the MX204 actually did was run a VENT FIELD under an SFP block. The
    tell is not overlap, it is a patterned field drawn where its pattern cannot
    be seen: honeycomb or grille that is almost entirely buried is either
    mismeasured or should not be there. Two fields in the library exceed the
    threshold, which is the signal-to-noise a warning wants.

    The second check is printing that runs off the face - the MX204's model name
    was clipped at the view edge. Text extent is ESTIMATED at 0.62 em per
    character, which is rough; the threshold is set so only a gross overrun
    fires, because a legend half a millimetre over is measurement noise and a
    legend ten millimetres over is a mistake.
    """
    vp = view_parts(view)
    boxes = []
    for b in vp["bays"]:
        bb = _decor_box(b)
        if bb:
            boxes.append(bb)
    for q in vp["placements"]:
        c = _instance_size(q.get("ref"), lib_roots)
        if not c or not q.get("at"):
            continue
        w, h = c
        if q.get("rotate") in (90, 270, -90):
            cx, cy = q["at"][0] + w / 2, q["at"][1] + h / 2
            boxes.append((cx - h / 2, cy - w / 2, cx + h / 2, cy + w / 2))
        else:
            boxes.append((q["at"][0], q["at"][1], q["at"][0] + w, q["at"][1] + h))

    for d in vp["decor"]:
        if not d.get("pattern"):
            continue
        db = _decor_box(d)
        if not db:
            continue
        area = (db[2] - db[0]) * (db[3] - db[1])
        if area <= 0:
            continue
        covered = 0.0
        for fb in boxes:
            ox = min(db[2], fb[2]) - max(db[0], fb[0])
            oy = min(db[3], fb[3]) - max(db[1], fb[1])
            if ox > 0 and oy > 0:
                covered += ox * oy
        pct = min(100.0, 100.0 * covered / area)
        if pct >= 80.0:
            warn(path, "L44", f"{view_name}: the {d['pattern']} field at "
                 f"{d['at']} is {pct:.0f}% buried under the parts on this face, "
                 "so its pattern is drawn where nothing can see it. Either the "
                 "field is mismeasured or it does not belong on this view")

    size = (view or {}).get("size") or {}
    vw = size.get("w")
    if not vw:
        return
    for m in vp["silkscreen"]:
        t, at = m.get("text"), m.get("at")
        if not t or not at:
            continue
        # USE THE SHARED EXTENT, WHICH KNOWS ABOUT `rotate`. This branch used to
        # compute its own width along x and never look at the rotation, so a
        # legend printed DOWN the face - the usual way a PSU bay is labelled at
        # the right-hand edge - had its full length added to x, where the metal
        # ends, instead of to y, where there is room. Two identical marks then
        # behaved differently for no reason but their x: the inboard one passed
        # and the outboard one was reported as running off a face it never
        # touched. A rule that fabricates an error is worse than one that misses,
        # because somebody goes and 'fixes' correct artwork.
        x0, _, x1, _ = _text_extent({"at": at, "text": t,
                                     "font-size": float(m.get("font-size") or 2.5),
                                     "anchor": m.get("anchor") or "start",
                                     "rotate": m.get("rotate", 0)})
        over = max(0.0, -x0) + max(0.0, x1 - float(vw))
        if over > 2.0:
            warn(path, "L44", f"{view_name}: silkscreen {str(t)[:24]!r} runs about "
                 f"{over:.0f}mm off the face (view is {vw} wide). Printing that "
                 "leaves the metal is a position error, not a long word")


def lint_device_empty_views(path, data):
    """L45: a face that is only a size is not a face.

    A view counts toward capability level 3 - `solid`, the one that gets a
    device into 3D - only if something is DRAWN on it. Four size-only faces left
    the MX204 at level 2 with `blocked: 4 views top, bottom, left, right`, and
    the modelling skill says an empty view that states why is fine: true for
    honesty, false for capability, and nothing pointed at the difference.

    A warning rather than an error, because accepting level 2 and saying why is
    a legitimate choice - the ASR 9000v's underside genuinely is unmeasurable.
    What is not legitimate is arriving at level 2 without noticing.
    """
    if (data.get("maturity") or "draft") == "draft":
        return
    # A FACE THE DEVICE HAS ALREADY DECLARED UNKNOWN IS NOT NAGGED ABOUT. The
    # ASR 9910's underside carries `rack-mounting-plane-not-dimensioned-for-this-
    # chassis`, reason needs-drawing, scoped to `bottom` - the author looked,
    # found nothing, and wrote down what would close it. Warning at that is
    # asking twice for a fact somebody has already said the world is short of,
    # and a rule that fires on declared unknowns teaches people to ignore it.
    #
    # IT OVER-EXEMPTS, and that is chosen rather than overlooked. A gap NAMING a
    # view is taken as covering it, but scopes hold whatever the gap is about -
    # the ASR 9006's `chassis-width-sources-disagree` names all four faces and is
    # about a WIDTH, not about whether those faces are drawn. Nothing in a gap
    # says "this is why the face is empty", so telling the two apart needs a
    # field that does not exist. Erring quiet is the right way round here: the
    # cost is one face not asked about, against a rule nobody reads.
    declared = set()
    for g in (data.get("gaps") or []):
        declared.update(g.get("scope") or [])
    for vname, view in (data.get("views") or {}).items():
        if vname in declared:
            continue
        vp = view_parts(view or {})
        if any(vp[k] for k in ("decor", "cutouts", "silkscreen",
                               "bays", "placements", "regions")):
            continue
        if not ((view or {}).get("size") or {}).get("w"):
            continue
        warn(path, "L45", f"{vname}: the face declares a size and nothing else, so "
             "it does not count as drawn and will not carry this device to "
             "`solid`. Give it its honest content - a rail, a label, a vent "
             "field, estimated and marked - or record why it stays empty")


def lint_device_silkscreen_owner(path, data):
    """L42: a mark says what it annotates, or says it annotates the whole unit.

    L14 is the other half of this and has always been half a rule: it checks a
    `for:` that IS stated and is silent on one that is not, so a legend with no
    owner has never been wrong about anything. Rather than fire, the whole
    mechanism simply did not apply, and the count drifted to 459 of 989 marks.

    WHAT AN UNOWNED MARK COSTS is specific, not tidiness. It cannot be checked
    for sitting near the thing it annotates - that is L14, which needs a target
    to measure against. It cannot be hidden by the module that covers it - L21
    needs to know what covers it, and a legend printed under a card is invisible
    on real hardware. It cannot nest under its owner in the tree. And no
    consumer can answer "what is printed next to port 12".

    `for: chassis` IS AN ANSWER, not an escape hatch. A model name on a bezel, a
    vendor wordmark, a compliance line - these annotate the whole unit, and
    saying so is a positive claim that the next reader can check. That is why
    L14 stopped rejecting it: requiring an owner is only fair once chassis-level
    printing has a way to declare itself.

    Warning at `modelled`, error at `verified`, like L15 and L37 - 459 marks
    cannot become errors on the day the rule lands.
    """
    maturity = data.get("maturity", "draft")
    if maturity == "draft":
        return
    for vname, view in (data.get("views") or {}).items():
        bare = [m for m in view_parts(view)["silkscreen"] if not m.get("for")]
        if not bare:
            continue
        shown = ", ".join(repr(m.get("text") or m.get("id") or "<path>")
                          for m in bare[:4])
        more = f" and {len(bare) - 4} more" if len(bare) > 4 else ""
        (err if maturity == "verified" else warn)(
            path, "L42", f"{vname}: {len(bare)} silkscreen mark(s) name nothing - "
            f"{shown}{more}. Add `for:` naming the part each annotates, or "
            "`for: chassis` where the printing is about the whole unit")


def lint_component_forwarded_mate(path, data, lib_roots):
    """L58: a cage's own connection point disagrees with the aperture inside it.

    A vendor cage wraps a standard aperture and presents that aperture's
    interface - see manifest.presented_interface - so the point a module enters
    is the aperture's `mate`, offset by where the wrapper puts it. The wrapper
    usually ALSO declares its own point, named for what plugs in: `net`, `rf`,
    `usb`.

    Those two should be the same place, and almost always are. Measured across
    the library before this rule was written: of thirteen port wrappers composing
    an aperture that carries an interface, TEN agree to within 0.05 mm, which is
    the evidence that forwarding recovers a name rather than inventing geometry.

    When they disagree the wrapper's own point was placed by eye and the
    aperture's was measured, so the drawing and the mating will part company: a
    cable drawn to the declared point and a module seated on the forwarded one.
    `common/qsfp-cage@2` is out by 0.54 mm vertically, which is small, real, and
    exactly the kind of thing nobody finds by looking.

    A warning: which of the two is right is a question about the part, and the
    fix is sometimes to move the declared point and sometimes to correct the
    composition offset.
    """
    if data.get("class") != "port" or data.get("interface"):
        return

    def _res(ref):
        q = resolve_component(ref, lib_roots)
        return load_yaml(q) if q else None

    iface, at = presented_interface(data, _res)
    if not iface or not at:
        return
    own = [(k, v.get("at")) for k, v in (data.get("connection-points") or {}).items()
           if isinstance(v, dict) and v.get("at")]
    if not own:
        return
    if any(all(abs(a - b) <= 0.05 for a, b in zip(o, at)) for _, o in own):
        return
    name, point = own[0]
    off = [round(point[0] - at[0], 3), round(point[1] - at[1], 3)]
    warn(path, "L58", f"connection-point {name!r} is at {point} but the composed aperture "
         f"presents {iface!r} at {at} - {off} apart. A module seats on the aperture's "
         "point and a cable is drawn to this one, so they should be the same place. "
         "Either the declared point was placed by eye, or the part's `at` offset is "
         "wrong; the aperture's own figure is the measured one")


def lint_device_gap_scope(path, data):
    """L54: a declared gap points at something the device does not have.

    A gap describes a DOCUMENT and not the drawing - "the HIG has no port-lamp
    table" - so no rule can check whether it is still true. What a rule can check
    is whether it still points at something. A gap scoped to a bay that was
    renamed, or to a group that was never declared, has drifted from the model it
    annotates and will be read by the next person as applying to a thing that is
    not there.

    MEASURED BEFORE IT WAS WRITTEN, because a rule that fires on correct models
    teaches people to ignore the linter: 166 of the library's 169 scope entries
    resolve. The three that do not are real - `filters` on a chassis whose groups
    are doors, grounding, power-modules and slots, and `ports` and `optics` on a
    device whose port groups are named sfp28 and qsfp28.

    A WARNING AND NOT AN ERROR, because an unresolved scope has an innocent
    reading: the gap may name something the device does not model YET, which is
    sometimes the whole point of the gap. The fix is then to say so in `wanted`
    rather than to delete the scope.
    """
    for what, scope in devicelock.stale_gap_scopes(data):
        warn(path, "L54", f"gap {what!r} is scoped to {scope!r}, which is not a group, "
             "view, configuration, id or attribute of this device. Either it drifted "
             "when the model changed - a renamed bay, a group that went away - or it "
             "names something not modelled yet, in which case `wanted:` should say that "
             "rather than the scope implying the device already has it")


def lint_device_empty_declaration(path, data):
    """L60: a face that declares itself empty must actually be bare.

    `empty` exists so that a face nobody has published anything about can still
    count as finished - see `capability._has_content`. That makes it the one
    field in a device that can turn a failing check green without drawing
    anything, so it needs the matching guard: the claim is "there is nothing on
    this face", and if something is drawn there the claim is false.

    The likely way this goes wrong is not fraud, it is time: a source turns up,
    the feature gets drawn, and the sentence saying nobody could find one stays
    behind and quietly contradicts the drawing above it.

    NOTE FOR L45, which is about the same faces from the other side. Its comment
    records that it over-exempts on purpose - it takes any gap NAMING a view as
    covering it, because "nothing in a gap says 'this is why the face is empty',
    so telling the two apart needs a field that does not exist". That field now
    exists and is this one. Tightening L45 to exempt on `empty` rather than on
    gap scope is deliberately NOT done here: it would start warning on every face
    currently covered by a scope, which is a change worth making on its own.
    """
    for vname, view in (data.get("views") or {}).items():
        view = view or {}
        if not str(view.get("empty") or "").strip():
            continue
        parts = view_parts(view)
        drawn = {k: len(parts[k]) for k in
                 ("decor", "cutouts", "silkscreen", "bays", "placements", "regions")
                 if parts[k]}
        if drawn:
            listed = ", ".join(f"{n} {k}" for k, n in sorted(drawn.items()))
            warn(path, "L60", f"view '{vname}' declares itself empty and draws "
                 f"{listed}. `empty` says a search found nothing published about this "
                 "face, so anything drawn on it contradicts the sentence - which is how "
                 "it reads once a source turns up and the note is left behind. Either "
                 "the note goes, or what is drawn does")


def lint_device_top_level_skus(path, data):
    """L59: SKUs at the top level, where no consumer looks.

    `part-numbers` exists at two levels and the consumers disagreed about which
    to read. The old nautobot exporter read only the top level; `dcim_export.py`
    reads only the per-configuration form. The result was two devices exporting
    under a name nobody can order - `AS5912-54X` and `AS7326-56X` - with ten real
    SKUs each sitting in the file, at the top level, invisible.

    PER-CONFIGURATION IS THE HOME, and not by preference: a SKU that encodes
    airflow and power feed IS a configuration-level fact, and it is what lets one
    device type be emitted per orderable thing. The per-configuration form also
    carries `{part, power-cord}`, which is what distinguishes a regional variant
    from a different machine; the top-level form is a flat string map that cannot
    say it.

    A warning, and one that should be closable: moving the entries is mechanical
    where a configuration exists to move them into. Where none does, the SKU is
    usually describing a variant nobody has modelled yet - which is worth knowing
    and is the more interesting half of what this finds.
    """
    pns = data.get("part-numbers")
    if not pns:
        return
    cfgs = data.get("configurations") or {}
    below = set()
    for cfg in cfgs.values():
        below |= set((cfg or {}).get("part-numbers") or {})
    orphan = sorted(set(pns) - below)
    if not orphan:
        warn(path, "L59", f"{len(pns)} top-level part-number(s) duplicate what the "
             "configurations already carry. Nothing reads the top level, so this is a "
             "second place to edit the same fact and a second place for it to go stale")
        return
    warn(path, "L59", f"top-level part-number(s) {', '.join(orphan[:4])} are not on any "
         "configuration, and nothing reads the top level - so they never reach the DCIM "
         "export, which is why a device with real SKUs in the file can still export under "
         "a model name nobody can order. Move them onto the configuration they describe; "
         "if no configuration describes them, the variant they name is not modelled yet")


def lint_device_configuration_kind(path, data):
    """L57: a configuration says whether you can order it.

    `configurations` was carrying four meanings at once - an orderable SKU, a
    different product, a regional variant, and somebody's illustration - and
    nothing distinguished them. The cost was not theoretical: the DCIM export
    groups by SKU and bay signature and takes the first configuration in each
    group, so the C40G, whose four configurations carry no part numbers at all,
    exported a device type named `C40G bdm-3plus1` - after a redundancy DRAWING,
    chosen because it happened to be listed second. Two other illustrations
    collapsed into it silently.

    `base` is the shape most people want first: the chassis with enough in it to
    power on and log in, traffic slots empty. You spec a chassis you can reach,
    then decide what goes in it. It is the default, and an illustration must not
    be - four devices in this library opened on one, which is how `default` came
    to mean "whatever the drawing happens to be populated with".

    WARNING AT `modelled`, ERROR AT `verified`, the gate L15, L37, L42 and L53
    all use. A device still being drawn should not have to fight the linter over
    a base configuration it has not built yet; a device claiming to be finished
    while its default is an illustration has not finished.
    """
    cfgs = data.get("configurations") or {}
    if not cfgs:
        return
    maturity = data.get("maturity", "draft")
    if maturity == "draft":
        return
    say = err if maturity == "verified" else warn
    bases = [n for n, c in cfgs.items() if (c or {}).get("kind") == "base"]
    unkinded = [n for n, c in cfgs.items() if not (c or {}).get("kind")]
    if unkinded:
        say(path, "L57", f"{len(unkinded)} configuration(s) do not say what kind they are "
            f"- {', '.join(sorted(unkinded)[:4])}. Add `kind:` - base (powers on, traffic "
            "slots empty), orderable (a SKU of this device), example (an illustration, "
            "never a device type) or model (really a different product). Without it a "
            "consumer cannot tell a SKU you can buy from a drawing somebody made")
    if len(bases) > 1:
        err(path, "L57", f"configurations {', '.join(sorted(bases))} all claim kind: base. "
            "There is one chassis-you-can-log-into per device; more than one base means "
            "the word is being used for something else")
    declared = [n for n, c in cfgs.items() if (c or {}).get("default")]
    if len(declared) > 1:
        err(path, "L57", f"configurations {', '.join(sorted(declared))} all claim default")
    if bases and declared and declared[0] not in bases:
        say(path, "L57", f"the default is {declared[0]!r} but the base is {bases[0]!r}. "
            "The base is what a device opens as - a chassis you can reach, before anything "
            "is decided about traffic cards")
    if declared and (cfgs[declared[0]] or {}).get("kind") == "example":
        say(path, "L57", f"the default configuration {declared[0]!r} is an illustration. "
            "Opening on one is how `default` came to mean 'whatever the drawing happens to "
            "be populated with'. Add a `kind: base` configuration and default to that")
    if not bases and any((c or {}).get("kind") for c in cfgs.values()):
        say(path, "L57", "no configuration is `kind: base`. The chassis with supplies, fans "
            "and engines in and the traffic slots empty is the one most people want first, "
            "and without it the default has to be a variant or an illustration")


def lint_overlay_identity(path, data):
    """L56: an overlay's `identity:` names a vendor who could sell it.

    An overlay with `identity:` says the device running this NOS is a distinct
    orderable thing whose vendor is the SOFTWARE house - the buyer's asset
    register says IP Infusion even though Edgecore made the metal. That only
    works if the named vendor exists and is a software vendor: filing a device
    type under a company that makes no software would put the disaggregated SKU
    back under a hardware brand, which is the thing the field exists to avoid.

    AN ERROR AND NOT A WARNING, unlike L55 next door. L55 is soft because the
    entry that matters states a lineage, and a lineage guessed to clear a gate
    is worse than an absent one. Here nothing is being guessed: the overlay has
    already made the claim, and the only question is whether the registry agrees
    the claimed vendor exists and writes software. That needs no document.
    """
    ident = data.get("identity")
    if not ident:
        return                      # opt-in: an overlay without one is a naming layer
    vendor = ident.get("vendor")
    entry = VENDORS.get(vendor)
    if entry is None:
        err(path, "L56", f"identity.vendor {vendor!r} is in no vendor registry. Add it "
            "to spec/schemas/vendors.yaml with role: software and a source saying how "
            "the pairing is known - a NOS vendor is named here and nowhere else, because "
            "the device's own `manufacturer:` is the metal and does not move when the "
            "software changes")
        return
    if entry.get("role") not in ("software", "both"):
        err(path, "L56", f"identity.vendor {vendor!r} has role {entry.get('role')!r}. "
            "An identity names the company that sells this NOS on this hardware, so it "
            "has to be a software vendor. If this company does write a NOS, correct its "
            "role in the registry; if the intent was to say who MADE the metal, that is "
            "the device's `manufacturer:` and it belongs there")
    dev = data.get("device")
    if dev and ident.get("model") and dev.split("/")[-1].lower() in \
            ident["model"].lower().replace(" ", "-"):
        return
    if ident.get("model") and data.get("nos") and \
            ident["model"].strip().lower() == str(data["nos"]).strip().lower():
        warn(path, "L56", f"identity.model {ident['model']!r} names only the NOS. The "
             "same NOS runs on other metal, so a model that does not say which hardware "
             "it is paired with cannot be told from its siblings in a DCIM")


def lint_vendor_registry(root):
    """L55: a vendor namespace that the registry does not know.

    A device states its `manufacturer:` - the name on the metal, which is what
    ENTITY-MIB's entPhysicalMfgName means - and that name must not move when a
    company is sold. So the directory stays put and the lineage lives in
    spec/schemas/vendors.yaml, where a consumer resolves through it: Casa
    Systems no longer exists and a search for Vistance that returns nothing is
    wrong about the world, while `casa/c100g` is right about the metal.

    A namespace with no entry breaks that resolution silently. It is also how
    the gap arrived in the first place - a vendor gets added during intake, the
    lineage is known to whoever staged it that week, and it is never written
    down.

    A WARNING AND NOT AN ERROR, for L51's reason exactly. The minimal entry
    costs one line, but the entry that matters states a LINEAGE, and a lineage
    guessed to clear a red gate is worse than an absent one - it is the same
    number minus the warning. Also reports the registry's own internal breaks,
    which ARE errors: a `successor` naming nothing is a typo in a file this
    repository owns, and needs no document to fix.
    """
    seen = set()
    for base in ("components", "devices"):
        d = root / base
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if not child.is_dir() or child.name in seen:
                continue
            seen.add(child.name)
            if child.name in VENDORS or child.name in NAMESPACES:
                continue
            warn(child, "L55", f"namespace {child.name!r} is in no vendor registry. "
                 "Add it to spec/schemas/vendors.yaml with `display`, `role` "
                 "(hardware | software | both) and `source` - and, if the company "
                 "has been renamed, bought or absorbed since the metal was made, "
                 "`successor`/`parent`/`brands`, because that is the part a "
                 "consumer cannot derive and nobody writes down later. If this is "
                 "not a company at all - a generic shape set like `common/` - "
                 "declare it under `namespaces:` instead")
    for slug, entry in sorted(VENDORS.items()):
        entry = entry or {}
        for key in ("successor", "parent"):
            target = entry.get(key)
            if target and target not in VENDORS:
                err(root / "…", "L55", f"vendor {slug!r} names {key} {target!r}, "
                    "which is not itself a vendor in the registry. A lineage that "
                    "points at nothing cannot be resolved through")
        for brand in (entry.get("brands") or []):
            if brand not in VENDORS:
                err(root / "…", "L55", f"vendor {slug!r} lists brand {brand!r}, "
                    "which is not itself a vendor in the registry")


def lint_device_config_scope(path, data):
    """L41: a bay scoped to configurations that do not exist is a bay in none.

    `only-in` REMOVES geometry - it is the one field that can make a bay vanish
    from every rendered configuration - and it is a free-text list of names. A
    typo does not fail loudly; it silently deletes the opening everywhere, which
    is the failure mode `default: null` had before L6 learned to ask whether any
    configuration filled the bay.

    Two shapes are wrong for opposite reasons. Naming a configuration that is not
    declared is the typo. Naming ALL of them is a no-op written as a constraint,
    which reads to the next author as though the scoping means something.
    """
    cfgs = set((data.get("configurations") or {}).keys())
    for vname, view in (data.get("views") or {}).items():
        parts = view_parts(view)
        for sect in ("bays", "placements"):
            for q in parts[sect]:
                only = q.get("only-in")
                if not only:
                    continue
                if not cfgs:
                    warn(path, "L41", f"{sect[:-1]} {q['id']} on view {vname} is scoped "
                                      f"to {sorted(only)}, but the device declares no "
                                      "configurations at all, so it renders nowhere")
                    continue
                missing = sorted(set(only) - cfgs)
                if missing:
                    warn(path, "L41", f"{sect[:-1]} {q['id']} on view {vname} is scoped to "
                                      f"{missing}, which {'are' if len(missing) > 1 else 'is'} "
                                      "not a declared configuration - the part renders in "
                                      "fewer configurations than the author meant, or none")
                if cfgs and set(only) >= cfgs:
                    warn(path, "L41", f"{sect[:-1]} {q['id']} on view {vname} is scoped to "
                                      "every configuration the device has, which is what "
                                      "omitting `only-in` already means. Drop it, or the "
                                      "next configuration added will silently exclude it")


def lint_device_port_optics(path, data, lib_roots):
    """L40: what runs in a cage, and whether anything can read it.

    Putting an optic in a port means knowing which optics that port takes. The
    mating mechanism exists and works - a cage declares `interface: sfp`, a
    transceiver `mates: sfp`, and L12 holds them to each other - but that only
    says an SFP-SHAPED THING FITS. Which of them lights up is a different fact
    and it is not modelled anywhere.

    THREE STATES, NOT TWO, and keeping them apart is the point. Some groups say
    nothing. Some carry the knowledge as `attrs` prose - `optics-qsfp28:
    100GBASE-SR4/CWDM4/LR4...` - which is real work somebody did off a datasheet,
    and scoring it the same as silence throws that away. None are structured yet,
    and deliberately so: form factor x reach x media x breakout mode is a large
    vocabulary and deriving it from four devices' marketing prose is how the
    portfolio taxonomy would have gone wrong. This rule harvests; it does not
    design. See #13.

    So prose does NOT warn. Silence does, and the register carries the count.
    """
    attrs = attrs_mod.flatten(data.get("attrs"))
    prose = {k for k in attrs if k.startswith(("optics-", "port-modes-"))}
    groups = data.get("groups") or {}
    reachable = set()
    for gid, gdef in groups.items():
        gdef = gdef or {}
        if gdef.get("term") != "Port":
            continue
        media = (gdef.get("attrs") or {}).get("media")
        if media not in PLUGGABLE_CAGES:
            continue
        hits = {k for k in prose
                if k in (f"optics-{media}", f"port-modes-{media}")}
        reachable |= hits
        if not hits:
            warn(path, "L40", f"port group {gid} ({media}) does not say which optics "
                              "run in it. `interface:` says what fits; this is what "
                              "works")
    # AN `optics-` KEY THAT NAMES NO GROUP IS THE SAME DEFECT ONE STEP WORSE: the
    # knowledge was written down and cannot be joined to anything. The AS5912-54X
    # is the case - it carries `optics-sfp` while its group declares
    # `media: sfp-plus`, so the one device that recorded its SFP optics is also a
    # device whose SFP group reads as silent.
    for k in sorted(prose - reachable):
        if k.startswith("optics-"):
            warn(path, "L40", f"`attrs.{k}` names no port group's media. The optics "
                              "are recorded and nothing can reach them")


def lint_device_groups(path, data, lib_roots):
    """L22 and L23 - what a port group promises, and what it actually holds.

    A group is the one place a block of ports says its facts once: the renderer
    merges `groups.<g>.attrs` down into every member, so `media: sfp28` on the
    group is what forty-eight ports draw. That only works if the block really is
    one family. Two rules, from the two directions:

      L22, error. The group DECLARES a media or a speed and a member contradicts
      it. This is the rule that makes group attrs trustworthy - without it a
      group can quietly relabel an RJ45 as SFP28 and the drawing will say so.

      L23, warning. The group SPANS families and does not say why. The S9510-28DC
      is the case: one `ports` group holding QSFP-DD/400G, QSFP28/100G and
      SFP28/25G, which is why it could carry no attrs at all and all twenty-eight
      ports repeated their media individually.

    But a mixed group is not always wrong. A management cluster is SFP+, USB-A,
    RJ45, serial and USB-C because the vendor's faceplate calls it one thing;
    splitting it by media would be a worse drawing. No rule can tell that from
    "nobody sorted this yet", and guessing would be the wrong kind of clever - so
    the author declares it, in `mixed:`, and says what job the block does. Same
    move as a `for:` that names `chassis`: the deliberate case is an answer, not
    an exemption. L23 checks that declaration both ways, because `mixed:` on a
    block that is in fact one family is a claim about the hardware that is false.
    """
    groups = data.get("groups") or {}
    # A group may be used in more than one view - `mgmt` is front on the Edgecore
    # boxes and rear on the DCP-R - so the members are gathered per device, not
    # per view, and a group is judged on everything it holds.
    members = {}
    for vname, view in (data.get("views") or {}).items():
        for p in view_parts(view or {})["placements"]:
            g = p.get("group")
            if not g or g not in groups:
                continue
            if contract_class(p["ref"], lib_roots) != "port":
                continue
            own = (p.get("attrs") or {}).get("media")
            members.setdefault(g, []).append({
                "where": f"{vname}/{p['id']}",
                "declared-media": own,
                "media": own or (contract_attrs(p["ref"], lib_roots) or {}).get("media"),
                "declared-speed": (p.get("attrs") or {}).get("speed"),
            })

    for gname, gdef in groups.items():
        mem = members.get(gname) or []
        if not mem:
            continue
        gattrs = (gdef or {}).get("attrs") or {}
        gm, gs = gattrs.get("media"), gattrs.get("speed")
        # L22 - the promise against the members.
        for m in mem:
            if gm and m["media"] and media_family(m["media"]) != media_family(gm):
                err(path, "L22", f"{m['where']}: group {gname!r} declares media {gm!r}, "
                                 f"but this port is {m['media']!r}. A group's attrs are "
                                 f"merged into every member, so the drawing would call it "
                                 f"{gm!r}")
            elif gm and m["declared-media"] and m["declared-media"] != gm \
                    and m["declared-media"] not in AMBIGUOUS_MEDIA:
                err(path, "L22", f"{m['where']}: group {gname!r} declares media {gm!r}, "
                                 f"but this port declares {m['declared-media']!r}. Same "
                                 f"cage, different media - one of the two is wrong")
            if gs and m["declared-speed"] and m["declared-speed"] != gs:
                err(path, "L22", f"{m['where']}: group {gname!r} declares speed {gs!r}, "
                                 f"but this port declares {m['declared-speed']!r}")
        # L23 - the composition against the declaration. Effective values, because
        # a member that says nothing is answered by its group.
        medias = {m["declared-media"] or gm or m["media"] for m in mem} - {None}
        speeds = {m["declared-speed"] or gs for m in mem} - {None}
        reason = (gdef or {}).get("mixed")
        spans = len(medias) > 1 or len(speeds) > 1
        if spans and not reason:
            found = ", ".join(sorted(medias)) or "one media"
            if len(speeds) > 1:
                found += " at " + ", ".join(sorted(speeds))
            warn(path, "L23", f"groups/{gname}: {len(mem)} ports spanning more than one "
                              f"family ({found}), so the block can declare nothing in "
                              f"attrs and every port must repeat itself. Split it by "
                              f"family, or say in `mixed:` what job they do together")
        elif reason and not spans:
            warn(path, "L23", f"groups/{gname}: declares mixed {reason!r}, but all "
                              f"{len(mem)} ports are {', '.join(sorted(medias)) or 'one family'}. "
                              f"`mixed:` states a fact about the hardware - drop it")


def lint_device_attrs(path, data):
    """L24 and L25 - what the sections of `attrs` promise.

    L25, error. Two sections claiming one key. `attrs` flattens onto the SVG
    root as `data-<key>` and there is no nesting in an attribute list to
    disambiguate them, so one of the two facts would silently win. It is an
    error rather than a warning because the loser is invisible: the drawing
    still compiles and still validates, and only a diff of two builds would
    show which value went missing.

    L24, warning, and it is a CENSUS rather than a complaint. `attrs.other` is
    a real section - 17 of the 22 keys that fit no section appeared on exactly
    one device, and a section per one-off is a taxonomy of nothing. The failure
    mode is not that the tail exists, it is that the tail goes quiet and `other`
    becomes where anything difficult gets put. So it is counted here, every
    build, and carried into the gaps register as `attrs-unclassified`. It either
    shrinks as patterns emerge or it stays visibly unshrunk; what it cannot do
    is become normal.
    """
    attrs = data.get("attrs") or {}
    for key, sections in sorted(attrs_mod.collisions(attrs).items()):
        err(path, "L25", f"attrs key {key!r} is in {' and '.join(sections)} - it "
                         f"flattens to data-{key} either way, so one of the two "
                         "values is silently discarded. A key belongs to one section")
    tail = sorted((attrs.get(attrs_mod.TAIL) or {}).keys())
    if tail:
        warn(path, "L24", f"attrs.other holds {len(tail)} key(s) - {', '.join(tail)}. "
                          "Fits no section yet: either a section is missing or this "
                          "is a genuine one-off. Counted so the tail cannot go quiet")


def _bay_refs_by_view(data):
    """{view: {ref, ...}} for everything the bays of that view can hold.

    Per view rather than per device because a paired I/O module lives on the
    OPPOSITE face from the card it serves - that is what makes it a pairing -
    so L30 cannot ask its question from a flattened set. A configuration's bay
    map is keyed by bay id, so it is attributed to the view that declares the
    bay.
    """
    out, owner = {}, {}
    for vname, view in (data.get("views") or {}).items():
        refs = set()
        for bay in view_parts(view or {})["bays"]:
            refs.update(bay.get("accepts") or [])
            if bay.get("default"):
                refs.add(bay["default"])
            owner[bay["id"]] = vname
        out[vname] = refs
    for cfg in (data.get("configurations") or {}).values():
        for bay_id, ref in (cfg.get("bays") or {}).items():
            if ref and bay_id in owner:
                out[owner[bay_id]].add(ref)
    return out


# ---------------------------------------------------------------- L31
# A region label that states a distance from an edge must agree with something
# drawn at that distance.
#
# This exists because a whole class of defect is invisible to every other rule:
# THE WORDS ARE RIGHT AND ONLY THE NUMBERS ARE WRONG. An ASR 9006 said its air
# filter was "accessible from the rear" while drawing it at the front, and an
# ASR 9906 region said its rails were at 127.0 and 240.0 mm while the geometry
# put them at 78.0 and 191.0. In both cases the file contained its own
# contradiction in plain text and lint stayed green.
#
# WHAT IS NOT CHECKED, deliberately. A bare direction word in a label is not a
# claim about position within a view - "fitted from the rear" is an access
# direction, "rear-panel bracket" is a part name, and "Front air intake" on a
# front view says nothing about depth. Checking those means reading English and
# guessing intent, which is how a rule earns a reputation for crying wolf. THE
# TRIGGER IS A NUMBER WITH A UNIT, because a number is a claim that can be
# wrong. That is also why the fix for a firing is often to ADD the distance to
# a label rather than to move geometry: a label without a number gives the
# drawing nothing to disagree with.
#
# THE OBVIOUS EXTENSION WAS BUILT AND MEASURED AND REJECTED. Recorded here so
# the next reader does not spend a session rediscovering it.
#
# L31 covers 14 of the 61 positional labels and specifically NOT the class that
# prompted it: the ASR 9006's "accessible from the rear" carries no number. So a
# second rule was prototyped in its narrowest defensible form - label names ONE
# depth end, on a face whose axis is known, no number, fire if nothing drawn on
# that face lies in the named half. Population after exclusions:
#
#     61  positional labels
#     21    excluded - front/rear views have no depth axis
#     14    excluded - carries a number, L31 owns it
#     10    excluded - names no depth end (left/right/upper only)
#      8    excluded - names BOTH ends ("front-to-rear cooling path")
#      8  CHECKABLE
#
# On the library as it stands: 8 checked, 0 fired. Replayed against the ASR
# 9006's pre-fix coordinates it DOES catch the motivating defect. That looks
# like a pass, and it is not, because of what the 8 turn out to be:
#
#     4  redundant - the ASR 9001 flanges, already covered by L31's `x = N` form
#     1  the true positive
#     3  QUIET ONLY BY COINCIDENCE
#
# The three are the reason to stop. "Fan tray sits behind this face, fitted from
# the rear" is an ACCESS DIRECTION, and it stays quiet because a grille's centre
# lands in the rear half by 0.2 mm - one edit to that grille and it fires
# falsely. "Not an air path - inlet right side, exhaust upper rear" describes the
# CHASSIS, not anything on the face it sits on, and is quiet only because the one
# cutout there happens to be rearward.
#
# AND THE DISCRIMINATION CANNOT BE MADE MECHANICALLY. "Accessible from the rear"
# is a position and the defect this whole rule exists for; "fitted from the rear"
# is an access direction and a false positive. They are grammatically identical.
# Telling them apart means knowing what a fan tray is, which is not something a
# linter knows - so the honest coverage is 14 of 61, and the remaining 39 need a
# person. There is no narrower form to come back and tune, because the true
# positive and the false positives are the same sentence.
#
# THE GENERAL LESSON, WHICH OUTLIVES THIS RULE:
#
#     A RULE QUIET AT 0.2 MM OF MARGIN HAS NOT PASSED. IT HAS NOT FIRED YET.
#
# That distinction is invisible in exactly the statistics that would have
# shipped it - 8 checked, 0 fired, catches the historical defect - and it
# applies to ANY check validated by counting how many fired rather than by
# reading the cases. Read what the quiet ones say. Three of these eight were
# coin flips, and no summary statistic could have told you.
NUM_RE = r"(\d+(?:\.\d+)?)"
EDGE_ANCHOR = re.compile(r"\bfrom\s+the\s+(front|rear|back)\b", re.I)
MEASURE_RE = re.compile(NUM_RE + r"\s*(in|mm|cm)\b", re.I)
COORD_RE = re.compile(r"\b([xy])\s*=\s*" + NUM_RE + r"\b")
_TO_MM = {"in": 25.4, "mm": 1.0, "cm": 10.0}
# A sentence break is a period followed by whitespace; a decimal point is a
# period followed by a digit. Splitting on the first is what lets "5.00 in and
# 9.45 in from the rear" yield TWO measurements without crossing a sentence.
SENTENCE_BREAK = re.compile(r"[;]|\.\s")
# depth axis index per view, and whether coordinate zero is the FRONT. Derived
# from viewer3d.js, which builds each face in local coordinates (x right, y up,
# z out of the face) and orients it with a fixed rotation, front at +z:
#   right rot [0, +pi/2, 0]  local +x -> world -z   so x = 0 is the FRONT
#   left  rot [0, -pi/2, 0]  local +x -> world +z   so x = 0 is the REAR
#   top   rot [-pi/2, 0, 0]  local +y -> world -z   so y = 0 is the REAR
# LEFT AND RIGHT ARE OPPOSITE because they are two views of one axis from
# opposite sides. Encoding it here is what stops the derivation being lost.
DEPTH_AXIS = {"top": (1, False), "bottom": (1, False),
              "left": (0, False), "right": (0, True)}


def _depth_extents(view, axis):
    """Everything drawn on this face, as (id, lo, hi) along the depth axis."""
    out = []
    panel = view.get("panel") or {}
    for kind in ("decor", "cutouts"):
        for i, el in enumerate(panel.get(kind) or []):
            at, size = el.get("at"), el.get("size")
            if not at or not size:
                continue
            out.append((el.get("id") or f"{kind}[{i}]", at[axis], at[axis] + size[axis]))
    for b in (view.get("bays") or []):
        at, size = b.get("at"), b.get("size") or {}
        if at and size:
            span = size["w"] if axis == 0 else size["h"]
            out.append((b.get("id", "bay"), at[axis], at[axis] + span))
    for pl in (view.get("placements") or []):
        at, size = pl.get("at"), pl.get("size") or {}
        if at and size:
            span = size.get("w") if axis == 0 else size.get("h")
            if span:
                out.append((pl.get("id", "placement"), at[axis], at[axis] + span))
    return out


def _label_claims(label, depth_mm, zero_is_front):
    """(quoted text, coordinate in view space) for each position a label asserts."""
    found = []
    for anchor in EDGE_ANCHOR.finditer(label):
        edge = anchor.group(1).lower()
        window = label[max(0, anchor.start() - 70):anchor.start()]
        cut = None
        for br in SENTENCE_BREAK.finditer(window):
            cut = br.end()
        if cut is not None:
            window = window[cut:]
        for q in MEASURE_RE.finditer(window):
            mm = float(q.group(1)) * _TO_MM[q.group(2).lower()]
            if mm > depth_mm + 1:
                continue                      # too big to be a depth on this face
            from_front = edge == "front"
            coord = mm if from_front == zero_is_front else depth_mm - mm
            found.append((f"{q.group(0)} from the {edge}", coord))
    for m in COORD_RE.finditer(label):
        found.append((m.group(0), float(m.group(2))))
    # "5.73 in (14.55 cm) from the front" states one position twice
    keep = []
    for txt, coord in found:
        if not any(abs(coord - k) < 0.75 for _, k in keep):
            keep.append((txt, coord))
    return keep


def lint_device_label_geometry(path, data):
    for vname, view in (data.get("views") or {}).items():
        if vname not in DEPTH_AXIS or not view:
            continue
        axis, zero_is_front = DEPTH_AXIS[vname]
        size = view.get("size") or {}
        depth_mm = size.get("w") if axis == 0 else size.get("h")
        if not depth_mm:
            continue
        extents = _depth_extents(view, axis)
        if not extents:
            continue                          # nothing drawn: L31 has no opinion
        for region in (view.get("regions") or []):
            label = region.get("label") or ""
            for txt, coord in _label_claims(label, depth_mm, zero_is_front):
                if any(lo - 1.0 <= coord <= hi + 1.0 for _, lo, hi in extents):
                    continue
                # say which way the disagreement runs, in from-the-front terms for
                # both, so a reader can see at a glance which half to fix
                def from_front(c):
                    return c if zero_is_front else depth_mm - c
                near = min(extents, key=lambda e: abs((e[1] + e[2]) / 2 - coord))
                lo, hi = sorted((from_front(near[1]), from_front(near[2])))
                warn(path, "L31",
                     f"{vname}/{region['id']}: label says {txt!r}, which is "
                     f"{from_front(coord):.1f} mm from the front, but nothing is drawn "
                     f"there - nearest is {near[0]} at {lo:.1f}-{hi:.1f} mm from the front")


def lint_device_double_count(path, data, lib_roots):
    """L30 - a chassis whose front and rear figures overlap.

    `power-draw-scope: module-with-paired-io` says a card's figure ALREADY
    contains its rear partner. If that partner then states a figure of its own,
    a sum over populated bays counts the pairing twice, and the result is a
    plausible over-count rather than an error - the failure this whole rule set
    exists to make impossible to reach silently.

    Keyed on the two faces rather than on `pairs-with`, because `pairs-with` is
    exactly what the affected cards do NOT carry: casa/bdm names its partner,
    the five DQM and DCU cards do not, and it is those that the vendor scopes to
    the pair. A rule that needed the partner named would be silent on the
    population it was written for.

    Restricted to `line-card` on both sides so a rear fan or PSU cannot trip it.
    A card's paired I/O module is a line card in this model - casa/io-6p12 is -
    and a fan is not something a card's figure was ever going to include.

    It finds nothing today, which is the point: no rear I/O module has a figure
    yet, and this fires the moment one lands.
    """
    by_view = _bay_refs_by_view(data)
    if len(by_view) < 2:
        return

    def cards(refs):
        """{ref: (scope, has_figure)} for the line cards among these refs."""
        out = {}
        for ref in sorted(refs):
            found = resolve_component(ref, lib_roots)
            if not found:
                continue
            sub = load_yaml(found) or {}
            if sub.get("class") != "line-card":
                continue
            a = sub.get("attrs") or {}
            out[ref] = (a.get("power-draw-scope", "module"),
                        any(k in a for k in DRAW_KEYS))
        return out

    seen = set()
    for vname, refs in sorted(by_view.items()):
        paired = sorted(r for r, (sc, fig) in cards(refs).items()
                        if sc == "module-with-paired-io" and fig)
        if not paired:
            continue
        for other, orefs in sorted(by_view.items()):
            if other == vname:
                continue
            partners = sorted(r for r, (sc, fig) in cards(orefs).items()
                              if fig and sc == "module")
            for partner in partners:
                if (partner, vname) in seen:
                    continue
                seen.add((partner, vname))
                warn(path, "L30",
                     f"{partner} states its own draw and sits in {other}, while "
                     f"{len(paired)} card(s) in {vname} ({', '.join(paired[:3])}"
                     f"{' ...' if len(paired) > 3 else ''}) declare "
                     "power-draw-scope: module-with-paired-io - their figures "
                     "already include a paired I/O module. Summing both sides "
                     "counts the pairing twice. Either the front figures are "
                     "bare after all and their scope is wrong, or this rear "
                     f"figure is for something the front does not cover - say "
                     "which in provenance and set the scopes to match")


def lint_device_module_power(path, data, lib_roots):
    """L29 - a chassis says how much of its own draw it can account for.

    The ask this exists for is "sum the populated bays". The failure it exists
    for is the sum being quotable when it is not: a chassis whose cards have no
    figures totals to a small, confident, wrong number, and nothing in the
    output says which bays were skipped. So the count comes out with the total,
    and while it is non-zero the total is a FLOOR.

    Reported from the device side rather than left to L27, because that is the
    only side the gaps register can see: `capability.derived_gaps` runs the
    DEVICE rules, so a component-scoped warning never reaches `gaps.json` - L26
    does not. Every modular device now carries "N of M accepted modules have no
    power figure" in the register automatically, with the entry disappearing
    when the figures land. Derived, never declared.

    The population is every module a bay can ACCEPT, not only the one installed
    by default. A bay's occupant is a configuration choice and the chassis has
    to be totalled for each of them, so a card that is accepted anywhere and
    has no figure blocks some real configuration's total.

    PSUs are not counted here. Their figure is `power-output-w` and it belongs
    to the supply side of the arithmetic, which is a different sum with a
    different meaning - see L27 for the module itself.
    """
    by_view = _bay_refs_by_view(data)
    refs = set().union(*by_view.values()) if by_view else set()
    modules, unsourced, families = set(), set(), set()
    for ref in sorted(refs):
        found = resolve_component(ref, lib_roots)
        if not found:
            continue                       # L5 reports the broken ref
        sub = load_yaml(found) or {}
        if sub.get("class") not in DRAW_CLASSES:
            continue
        modules.add(ref)
        sattrs = sub.get("attrs") or {}
        if sub.get("class") == "transceiver" and sattrs.get("media") in AMBIGUOUS_MEDIA:
            families.add(ref)
        if not any(k in sattrs for k in DRAW_KEYS):
            unsourced.add(ref)
    # One warning per unsourced module, not one per chassis. The register turns
    # a rule's warning count into the gap's size, and a chassis that cannot
    # account for five of its cards is a bigger hole than one that cannot
    # account for one - which a single warning per device flattens to 1.
    for ref in sorted(unsourced):
        # A family optic cannot be fixed on its contract - see L27 - so pointing
        # the reader at the contract would be pointing at a door that does not
        # open. The hole is real and stays counted; only the remedy differs.
        fix = ("Declare power-draw-max-w on the placement or its group, the way "
               "L18 asks for the real media: this ref is a family rather than a "
               "part, and the figure belongs to the optic actually fitted"
               if ref in families else
               "Add power-draw-max-w to that contract from the vendor's own "
               "per-card table")
        warn(path, "L29", f"{ref} is accepted by a bay here and states no power "
                          f"draw ({len(unsourced)} of {len(modules)} module(s) this "
                          "chassis accepts), so its module total is a floor and not "
                          f"a total. {fix}; where no document states it, "
                          "this count is the honest report of how much of the "
                          "chassis is unaccounted for")


def lint_device(path, validator, lib_roots):
    try:
        data = load_yaml(path)
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

    lint_device_attrs(path, data)
    lint_device_module_power(path, data, lib_roots)
    lint_device_double_count(path, data, lib_roots)
    lint_device_bay_fit(path, data, lib_roots)
    lint_device_midplane_depth(path, data, lib_roots)
    lint_device_label_geometry(path, data)
    declared_groups = set((data.get("groups") or {}).keys())
    for gname, gdef in (data.get("groups") or {}).items():
        check_states(path, f"groups/{gname}", (gdef or {}).get("states"),
                     (gdef or {}).get("attrs"))
    lint_device_groups(path, data, lib_roots)
    lint_device_port_optics(path, data, lib_roots)
    lint_device_config_scope(path, data)
    lint_device_silkscreen_owner(path, data)
    lint_device_rack_ears(path, data)
    lint_device_bay_pitch(path, data)
    lint_device_empty_views(path, data)
    lint_device_occupants(path, data, lib_roots)
    # Every id each view offers, indexed by view name. A `for:` may name a target
    # in ANOTHER view of the same device (`rear/psu-0`), so the check below cannot
    # be answered from the view it is standing in.
    view_ids = {}
    for vn_, vv_ in (data.get("views") or {}).items():
        vpp = view_parts(vv_ or {})
        view_ids[vn_] = ({q["id"] for q in vpp["placements"]}
                         | {b["id"] for b in vpp["bays"]})
    # every bay any configuration names an occupant for, so the bay rule below
    # can tell "nothing ever fills this" from "a different build fills it"
    cfg_filled = set()
    for _c in (data.get("configurations") or {}).values():
        cfg_filled.update((_c or {}).get("bays") or {})
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
        lint_device_cutouts(path, vname, view, lib_roots)
        lint_device_decor(path, vname, view, lib_roots)
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
            # A SLOT MAY NAME AN INTERFACE INSTEAD OF A LIST. `accepts` is the
            # vendor's compatibility matrix, transcribed; an open form factor
            # like PCIe has no matrix to transcribe, so such a bay says which
            # interface it presents and carries no list at all.
            for acc in (b.get("accepts") or []):
                if not resolve(acc):
                    err(path, "L5", f"unresolvable accepts ref {acc} ({b['id']})")
            if b.get("default") and b["default"] not in (b.get("accepts") or []):
                err(path, "L6", f"bay {b['id']} default {b['default']} not in accepts")
            # A BAY NOTHING EVER FILLS RENDERS AS A HOLE, and the modelling skill
            # has
            # said so for a while - "no module means no lamp, so nothing in it is
            # clickable, nothing is addressable, and the 3D viewer finds nothing
            # to extrude". L6 checked that a default, IF PRESENT, is one the bay
            # accepts, and never that one was there at all. Every device in the
            # library followed the convention anyway except one, which is exactly
            # how an unenforced rule fails: not gradually, but on whichever
            # manifest nobody re-read.
            #
            # CONFIGURATIONS COUNT, and the first cut of this rule missed that.
            # It flagged the C40G's four front PSU bays and two rear PEM bays,
            # and all six are correct: `ac-power` fills the PSUs and the three DC
            # builds fill the PEMs, and each set is genuinely empty in the other
            # - an AC chassis has no power entry modules and a DC one has no AC
            # supplies. A bay-level default there would assert a fit-out the
            # device does not have. What is actually wrong is a bay NO
            # configuration ever fills, which on this library is one bay.
            #
            # A warning, because "what is normally fitted here" is a modelling
            # decision with a source behind it, and a linter guessing it would be
            # worse than the hole.
            if not b.get("default") and b["id"] not in cfg_filled:
                warn(path, "L6", f"bay {b['id']} names no default and no "
                                 "configuration fills it, so it draws as an empty "
                                 "frame in every drawing of this device")
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
                boxes[p["id"]] = (p["at"], c, p.get("rotate"), False)
        for b in vp["bays"]:
            # A BAY'S `size` IS ALREADY ITS ON-PANEL FOOTPRINT and must not be
            # transposed; `rotate` spins the OCCUPANT inside the opening. This is
            # the same trap L13 records below, and it was live here: every
            # rotated bay was measured against a footprint spun 90 degrees about
            # its own centre, so the C40G's rear-0 - a horizontal slot at
            # x 39.35 - was tested as a vertical one at x 196.865, and the slot
            # number printed beside it read as 157 mm away. Nothing caught it
            # because no legend had ever named a rotated bay.
            boxes[b["id"]] = (b["at"], (b["size"]["w"], b["size"]["h"]),
                              b.get("rotate"), True)

        def footprint(owner):
            (ax, ay), (bw, bh), rot, is_bay = boxes[owner]
            if rot in (90, 270, -90) and not is_bay:
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
                    # SILKSCREEN MAY NAME THE WHOLE UNIT, and the ban that used to
                    # sit here was an over-reach. It was added alongside cross-view
                    # targets, whose rejection is right and stands: a legend that
                    # labels a part on another face is ink that means nothing. But
                    # `chassis` is not cross-view. It is present on every face, and
                    # a model name silkscreened on a bezel - `C40G`, `HALNY`,
                    # `Cisco ASR 9000 Series` - is printing about the whole unit, on
                    # the face it is printed on. The old message said "printed ink
                    # annotates a part, not the whole unit", and the library holds
                    # some twenty marks that are exactly the thing it said could not
                    # exist.
                    #
                    # It is also the answer L42 needs. Requiring every mark to
                    # declare an owner is only fair if chassis-level printing has a
                    # way to say so, and this is that way - positive, checkable, and
                    # already wired end to end, since the renderer gives the
                    # faceplate data-path="chassis" and the tree nests on it.
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
        #
        # What buries a mark is PAINT, not a bounding rectangle. A placement's box
        # is only the fallback: where the skin can be read, each painted node is
        # tested on its own, so a legend printed in the bare metal a component
        # reserves inside its own box - between two LED holes, inside an unfilled
        # moulding - is correctly left alone. See paint_boxes.
        boxes = []
        for p in vp["placements"]:
            if not p.get("at"):
                continue                      # a mate-to occupant carries no position
            sz = (contract_size(p["ref"], lib_roots) or {})
            if not (sz.get("w") and sz.get("h")):
                continue
            px, py, pw, ph = p["at"][0], p["at"][1], sz["w"], sz["h"]
            painted = paint_boxes(p["ref"], p.get("skin", "default"), lib_roots)
            if painted is None:
                boxes.append((px, py, pw, ph, p["id"]))
                continue
            flip = str(p.get("rotate", 0)) == "180"
            for x0, y0, x1, y1 in painted:
                if flip:                      # a half turn about the box centre
                    x0, x1 = pw - x1, pw - x0
                    y0, y1 = ph - y1, ph - y0
                x0, y0 = max(x0, 0.0), max(y0, 0.0)   # the contracted box is the limit
                x1, y1 = min(x1, pw), min(y1, ph)
                if x1 > x0 and y1 > y0:
                    boxes.append((px + x0, py + y0, x1 - x0, y1 - y0, p["id"]))
        # A BAY PAINTS OVER A LEGEND TOO, and L21 had never looked at one. It
        # gathered boxes from placements alone, so a mark printed where a card
        # goes was reported as fine - and the C40G's slot numbers, all six of
        # them, sit inside `fan-left` and do not appear in the drawing at all.
        # A bay is the most opaque thing on a faceplate: filled it is a card
        # front, empty it is a dark cavity, and either way nothing under it can
        # be read. Its own declared extent is the box, because that is the hole
        # the module fills whatever is in it.
        for b in vp["bays"]:
            if not b.get("at"):
                continue
            bs = b.get("size") or {}
            bw = bs.get("w") if isinstance(bs, dict) else (bs[0] if bs else None)
            bh = bs.get("h") if isinstance(bs, dict) else (bs[1] if bs else None)
            if not (bw and bh):
                continue
            if str(b.get("rotate", 0)) in ("90", "270", "-90"):
                bw, bh = bh, bw
            boxes.append((b["at"][0], b["at"][1], bw, bh, b["id"]))
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
    # L37 - a group says what it is FOR, and a declared group has members.
    #
    # WHY THE GROUP HAS TO SAY IT. A PSU bay, a fan bay and a line-card bay are
    # all data-class `bay` - the same hole with a module in it - so nothing
    # reading the drawing can tell which of them is why the box exists and which
    # two keep it alive. Without `role` the only ordering left is the order the
    # placements happen to be written in, which opened the C40G with its power
    # supplies and the AGR420 with its air filters.
    #
    # WARNING AT `modelled`, ERROR AT `verified`, the same gate L15 uses: a
    # device still being drawn should not have to fight the linter, and a device
    # CLAIMING to be finished has to have answered the question.
    groups = data.get("groups") or {}
    if groups:
        joined = []
        for vw in (data.get("views") or {}).values():
            for kind in ("bays", "placements"):
                for it in ((vw.get("components") or {}).get(kind) or []):
                    if it.get("group"):
                        joined.append(it["group"])
        for gid, gdef in groups.items():
            gdef = gdef or {}
            if not gdef.get("role"):
                (err if maturity == "verified" else warn)(
                    path, "L37", f"group {gid} does not say what it is for. Add "
                    "role: traffic|management|service|indicator|furniture - a PSU "
                    "bay and a line-card bay are the same class, so this is the "
                    "only thing that can rank them")
            # A GROUP NOTHING JOINS IS A CATEGORY THE DRAWING PROMISES AND DOES
            # NOT KEEP. It reads to anyone listing the device as a block the
            # hardware has, and the hardware does not have it. Always a warning:
            # the fix is either to populate it or delete it, and which of those
            # is right is a modelling question, not a lint one.
            if gid not in joined:
                warn(path, "L37", f"group {gid} is declared and nothing joins it. "
                     "Either place something in it or drop it")

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
                cd = load_yaml(c) or {}
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
            bay_accepts[b["id"]] = b.get("accepts") or []
    for cname, cfg in (data.get("configurations") or {}).items():
        for bid, ref in (cfg.get("bays") or {}).items():
            if bid not in bay_accepts:
                err(path, "L8", f"config {cname}: unknown bay {bid}")
            elif ref == "":
                # AN EMPTY STRING MEANS THE BAY IS EMPTY, which is a legitimate
                # thing for a configuration to say and the only way a `kind: base`
                # can leave the traffic slots open while the supplies, fans and
                # engines stay seated. The renderer has always honoured it - it
                # draws the opening as a real hole with the depth of whatever the
                # bay accepts - but nothing had ever written one, so this check
                # had never met the case and rejected the emptiest possible ref
                # for not being a module the bay accepts.
                continue
            elif ref not in bay_accepts[bid]:
                err(path, "L8", f"config {cname}: bay {bid} ref {ref!r} not in accepts")
    return data


def print_matrix(matrix, schemas):
    """One table, every device, level and flags.

    This is what turns lint output from a pass/fail into a dashboard. The
    portfolio's shape - which models can be put in a rack elevation, which can
    go to 3D, which can be exported - was previously only knowable by opening
    thirteen files, so nobody knew it.

    Nothing here is declared. Every column is computed from the manifest, so it
    cannot be optimistic and cannot go stale.
    """
    import capability
    profiles = capability.load_profiles(schemas)
    rows = []
    for path, d in matrix:
        cap, _ = capability.assess(d, profiles=profiles)
        rows.append((d["name"], cap, d.get("profile") or "-",
                     d.get("maturity") or "draft"))
    if not rows:
        return
    w = max(len(r[0]) for r in rows)
    print()
    print(f"PORTFOLIO  {len(rows)} devices")
    print(f"  {'device':<{w}}  lvl  {'capability':<12} {'profile':<11} "
          f"{'maturity':<9} flags / next")
    for name, cap, prof, mat in sorted(rows, key=lambda r: (-r[1]["level"], r[0])):
        # Flags earned, then the ones that could not be tested at all, then the
        # first thing standing in the way. A report that does not say how to fix
        # it is a scoreboard, not a tool - and one that prints the same `no` for
        # "checked and short" as for "never checked" is worse than a scoreboard,
        # because a reader who knows the device has twenty-four attrs concludes
        # the predicate is broken and stops trusting the column.
        tail = " ".join([f"+{f}" for f in cap["flags"]]
                        + [f"?{f}" for f in cap["unknown"]])
        if cap["blocked"]:
            b = cap["blocked"][0]
            tail = (tail + "  " if tail else "") + f"-> {b['level']} {b['name']}: {b['needs']}"
        print(f"  {name:<{w}}  {cap['level']:>3}  {cap['name']:<12} {prof:<11} "
              f"{mat:<9} {tail}")
    earned, unknown = {}, {}
    for _, cap, _, _ in rows:
        for f in cap["flags"]:
            earned[f] = earned.get(f, 0) + 1
        for f in cap["unknown"]:
            unknown[f] = unknown.get(f, 0) + 1
    print("  " + ", ".join(
        f"{f}: {earned.get(f, 0)}/{len(rows)}"
        + (f" (+{unknown[f]} ? unevaluable)" if unknown.get(f) else "")
        for f in capability.FLAGS))
    print("  + earned, ? cannot be evaluated, absent means tested and not met")
    print()



# ---------------------------------------------------------------- L33
FIT_TOL = 0.05          # a rounding difference is not a misfit


def lint_device_bay_fit(path, data, lib_roots):
    """L33 - a bay must reserve enough room for every module it accepts.

    THE 262 MISMATCHES THIS EXISTS FOR were found by a script nobody ran, and a
    finding that lives in a script is a finding that goes stale. The check is
    cheap and belongs in the build.

    What it compares matters more than that it compares. A module has TWO
    extents and they are not interchangeable:

        size    what the skin DRAWS - the faceplate as depicted
        insert  what the slot must ACCOMMODATE, where a source states it
                separately: "Physical dimensions (includes ejector bracket/lever)"

    Cisco publishes both, sometimes in one sheet and often without saying which
    it means, and 35 of this library's cards carry one figure in `size` and the
    other in a provenance sentence. So the comparison is against `insert` where
    it exists and `size` otherwise, never against whichever happens to be
    smaller.

    AND IT WARNS RATHER THAN ERRORING, deliberately. A module wider than its bay
    is usually two figures describing different things rather than a part that
    does not fit, and the fix is often to state the second extent rather than to
    move a number. Erroring would push people toward reconciling the two - which
    silences the only check that can see them.
    """
    for vname, view in (data.get("views") or {}).items():
        for bay in (((view.get("components") or {}).get("bays")) or []):
            bs = bay.get("size")
            if not bs:
                continue
            bw, bh = bs.get("w"), bs.get("h")
            if bw is None or bh is None:
                continue
            if (bay.get("rotate") or 0) % 180 == 90:
                bw, bh = bh, bw
            for ref in sorted(bay.get("accepts") or []):
                found = resolve_component(ref, lib_roots)
                if not found:
                    continue                   # L5 reports the broken ref
                sub = load_yaml(found) or {}
                ext = sub.get("insert") or sub.get("size") or {}
                w, h = ext.get("w"), ext.get("h")
                if w is None or h is None:
                    continue
                over_w, over_h = w - bw, h - bh
                if over_w <= FIT_TOL and over_h <= FIT_TOL:
                    continue
                which = "insert" if sub.get("insert") else "size"
                worst = "wider" if over_w > over_h else "longer"
                by = max(over_w, over_h)
                warn(path, "L33",
                     f"{vname}: bay {bay.get('id')} is {bs['w']:g} x {bs['h']:g} "
                     f"and accepts {ref}, whose {which} is {w:g} x {h:g} - "
                     f"{by:.2f} mm {worst} than the bay. If those two numbers "
                     f"measure DIFFERENT THINGS - a plate that overlaps its "
                     f"aperture, an envelope that includes an ejector - say so by "
                     f"giving the module an `insert:` and leaving `size` as what "
                     f"the skin draws. Do NOT reconcile them by moving one to "
                     f"meet the other unless you measured it")


# ---------------------------------------------------------------- L34
# A front card and a rear card in the same slot position MAY overlap in depth,
# because the rear I/O card is an L: its body sits against the midplane and a
# tongue continues forward THROUGH it to mate with the front card, at reduced
# height. So the honest test is not F + R <= C. It is that the overlap must be
# TONGUE-SIZED. 25 percent of the chassis depth is deliberately generous - it
# admits a ~96 mm tongue on a 386 mm chassis, which is far more than any tongue,
# and still catches the case this exists for: two 380 mm cards in a 386 mm
# chassis, a 374 mm overlap that no interlock can absorb.
MIDPLANE_SLACK = 1.25


def lint_device_midplane_depth(path, data, lib_roots):
    """L34 - front and rear occupants of one slot must fit around the midplane.

    Found by a photograph, not by arithmetic. Every Casa card carried d 380.0 in
    a 386-388 mm chassis, on both faces, and nothing complained: each number was
    individually plausible, honestly marked `estimated`, and propagated cleanly
    across a family. It took a picture of an empty cage with the midplane visible
    to show that two of them cannot both be true.

    That is the shape worth catching. The defect was never in one contract - it
    was in the RELATIONSHIP between two contracts that no rule compared, which is
    the same blind spot L33 exists for one axis over.

    Reads `size-confidence` so a depth already marked `known-wrong` is reported as
    a KNOWN defect rather than a new one: the register and the rule should agree
    about what is already understood, or the rule just re-reports the backlog.
    """
    ch = data.get("chassis") or {}
    cd = ch.get("depth")
    views = data.get("views") or {}
    if not cd or "front" not in views or "rear" not in views:
        return

    def by_pos(vname):
        """Slot bays only, keyed by position.

        ONLY SLOT GROUPS MATE ACROSS A MIDPLANE. A fan tray and a power module
        also carry a rel-pos, and pairing a front fan with a rear line card by
        position alone is how the first draft of this rule produced two
        confident warnings about hardware that never meets. A group whose name
        does not say `slot` is not in this relationship.
        """
        out = {}
        for b in (((views.get(vname) or {}).get("components") or {}).get("bays") or []):
            rp, g = b.get("rel-pos"), b.get("group")
            if rp is not None and g and "slot" in g:
                out.setdefault(rp, []).append(b)
        return out

    def deepest(bay):
        """(depth, ref, confidence) of the deepest thing this bay accepts."""
        best = (None, None, None)
        for ref in (bay.get("accepts") or []):
            found = resolve_component(ref, lib_roots)
            if not found:
                continue
            sub = load_yaml(found) or {}
            d = (sub.get("size") or {}).get("d")
            if d and (best[0] is None or d > best[0]):
                conf = (sub.get("size-confidence") or {}).get("d")
                best = (d, ref, conf)
        return best

    front, rear = by_pos("front"), by_pos("rear")
    seen = set()
    for pos, fbays in sorted(front.items()):
        rbays = rear.get(pos)
        if not rbays:
            continue
        fd, fref, fconf = deepest(fbays[0])
        rd, rref, rconf = deepest(rbays[0])
        if not fd or not rd:
            continue
        total = fd + rd
        if total <= cd * MIDPLANE_SLACK:
            continue
        pair = tuple(sorted((fref, rref)))
        if pair in seen:
            continue                      # one warning per pair of parts
        seen.add(pair)
        known = [r for r, c in ((fref, fconf), (rref, rconf)) if c == "known-wrong"]
        tail = (f" ALREADY RECORDED as known-wrong on {', '.join(known)}."
                if known else
                " NEITHER depth is marked known-wrong, so this is a new defect.")
        warn(path, "L34",
             f"slot {pos}: front accepts {fref} at d {fd:g} and rear accepts "
             f"{rref} at d {rd:g}, together {total:g} mm in a {cd:g} mm chassis. "
             f"A rear I/O card may legitimately OVERLAP the front one - its tongue "
             f"passes through the midplane to mate with it - but by a tongue, not "
             f"by {total - cd:.0f} mm.{tail}")


# ---------------------------------------------------------------- L32
class _DupCounting(yaml.SafeLoader):
    """A loader that RECORDS duplicate mapping keys instead of resolving them.

    WHY NO POST-PARSE CHECK CAN SUBSTITUTE, which is the durable part of this
    rule: a duplicate key is resolved by the parser before any consumer sees the
    document. yaml.safe_load hands back a legal object with one of the two
    values silently gone, so the JSON Schema validates it happily and every
    downstream rule is satisfied by the survivor. The collision has to be caught
    at construction time or not at all.

    ERROR rather than warning, because there is no case where two identical keys
    in one mapping are intended, and the failure is always silent data loss.

    AND IT CAN BE WORSE THAN LOSS. On celestica/psu-1600 the discarded
    `provenance.face` said the geometry was "STILL ESTIMATED - the fan/latch
    spacing was tuned around a c14-inlet that was 20 percent undersized" and the
    surviving one said "photo (psu-face.jpeg ...)". The collapse did not merely
    lose a sentence; it UPGRADED THE APPARENT CONFIDENCE of the component, from
    estimated to photo-sourced, which is exactly what L15 gates `verified` on.

    Recording rather than raising so that one file reports every duplicate it
    has in one run, and so that a bad file does not abort the pass.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.dups = []

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in seen:
                    self.dups.append((key, key_node.start_mark.line + 1))
                seen.add(key)
            except TypeError:          # unhashable key - the schema will catch it
                pass
        return super().construct_mapping(node, deep=deep)


def lint_duplicate_keys(path):
    """L32: no mapping in this file declares the same key twice."""
    loader = _DupCounting(path.read_text())
    try:
        loader.get_single_data()
    except yaml.YAMLError:
        return                          # unparseable: L1 has already said so
    finally:
        loader.dispose()
    for key, line in loader.dups:
        err(path, "L32", f"duplicate key {key!r} at line {line} - YAML keeps the "
            "LAST one and discards the other silently, so whatever the first "
            "declared is gone before any rule or schema sees this file. Give them "
            "distinct names, or merge them into one statement if they are two "
            "accounts of the same fact")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemas", required=True)
    ap.add_argument("--library", action="append", required=True)
    # LINT ONE DEVICE WHILE YOU ARE WORKING ON IT. A full pass reads every
    # component in the library because most rules are about a device AGAINST the
    # library, and that is right for a gate - but it is the wrong unit for the
    # edit-check loop, where one manifest changed and the answer wanted is about
    # that manifest.
    #
    # It narrows the DEVICE pass only. Components are still linted in full,
    # because a device's rules resolve refs into them and half-checked
    # components would make the device answer unreliable; and because that pass
    # is the cheap half once parses are cached.
    #
    # NOT A SUBSTITUTE FOR THE FULL RUN, and the output says so. Cross-device
    # facts - a component nothing accepts, the portfolio matrix - cannot be
    # computed from one device, so they are skipped rather than computed wrongly.
    ap.add_argument("--device", action="append", default=[], metavar="NAME",
                    help="lint only these devices by name or path fragment; "
                         "components are still checked in full")
    args = ap.parse_args()
    schemas = Path(args.schemas)
    std_file = schemas / "standards.yaml"
    if std_file.exists():
        STANDARDS.update(load_yaml(std_file)["standards"])
    if (schemas / "power-roles.yaml").exists():
        global DRAW_CLASSES, SUPPLY_CLASSES, PASSIVE_CLASSES
        DRAW_CLASSES, SUPPLY_CLASSES, PASSIVE_CLASSES = _load_power_roles(schemas)
    # the schemas are YAML too where they are YAML, and a duplicate in the
    # registry would be as silent there as anywhere else
    for f in sorted(schemas.glob("*.yaml")):
        lint_duplicate_keys(f)
    comp_v = load_schema(schemas, "component.schema.json")
    dev_v = load_schema(schemas, "device.schema.json")
    ovl_v = load_schema(schemas, "overlay.schema.json")

    n = 0
    matrix = []
    dev_maturity = {}
    # With --device, check only the components those devices actually reach.
    # Linting all 254 was most of a filtered run - and a component no selected
    # device names cannot affect the answer being asked for.
    wanted = None
    if args.device:
        wanted = set()
        for root in args.library:
            for f in sorted(Path(root).glob("devices/**/device.yaml")):
                if any(sel in str(f) for sel in args.device):
                    wanted |= device_dependencies(f, args.library)
    for root in args.library:
        root = Path(root)
        for f in sorted(root.glob("components/**/contract.yaml")):
            if wanted is not None and f not in wanted:
                continue
            lint_duplicate_keys(f)
            d = lint_component(f, comp_v)
            # a file that would not parse has already been reported; running the
            # rest against None just buries that message under a traceback
            if d is not None:
                _skin_checks(f, d)
                lint_component_parts(f, d, args.library)
                lint_component_collisions(f, d, args.library)
                lint_component_bays_drawn(f, d, args.library)
                lint_component_skin_printing(f, d, args.library)
                lint_component_states_render(f, d, args.library)
                lint_component_mating(f, d, args.library)
                lint_component_aperture(f, d, args.library)
                lint_component_power(f, d)
                lint_component_role(f, d)
                lint_component_forwarded_mate(f, d, args.library)
                lint_component_relief_confidence(f, d, args.library)
            n += 1
        for f in sorted(root.glob("devices/**/device.yaml")):
            if args.device and not any(sel in str(f) for sel in args.device):
                continue
            lint_duplicate_keys(f)
            d = lint_device(f, dev_v, args.library); n += 1
            if d is not None and d.get("kind") == "device":
                lint_device_gap_scope(f, d)
                lint_device_configuration_kind(f, d)
                lint_device_top_level_skus(f, d)
                lint_device_empty_declaration(f, d)
                try:
                    dev_maturity[str(f.parent.relative_to(root / "devices"))] = \
                        d.get("maturity", "draft")
                except ValueError:
                    pass
                matrix.append((f, d))
        if args.device:
            continue
        for f in sorted(root.glob("devices/**/overlays/*.yaml")):
            lint_duplicate_keys(f)
            data = load_yaml(f)
            for e in ovl_v.iter_errors(data):
                err(f, "L1", f"{'/'.join(str(p) for p in e.path)}: {e.message}")
            if isinstance(data, dict):
                lint_overlay_identity(f, data)
            n += 1

    # The matrix is a PORTFOLIO view - it ranks devices against each other - so
    # printing it for a subset would invite reading a partial ranking as a whole
    # one. Say what was skipped instead.
    # L53 IS LIBRARY-WIDE and compares against library/devices.lock.json, so a
    # --device run cannot do it: the lock is one file describing every device and
    # a partial check would report the unexamined ones as unchanged.
    if not args.device:
        for root in [Path(r) for r in args.library]:
            lint_vendor_registry(root)
            if not (root / devicelock.LOCK_NAME).exists() and not list(root.glob("devices/*/*/device.yaml")):
                continue
            for slug_, kind_, msg_ in devicelock.check(root):
                # WARNING WHILE THE DEVICE IS STILL BEING DRAWN, ERROR ONCE IT
                # CLAIMS TO BE FINISHED - the gate L15, L37 and L42 all use. A
                # device at `modelled` is work in progress and should not have to
                # fight the linter mid-edit; a device claiming `verified` while
                # its geometry moved under an unchanged version has broken the
                # promise the version exists to make. No device is verified yet,
                # so this arms itself as the library matures rather than going
                # red on the day it lands.
                (err if dev_maturity.get(slug_) == "verified" else warn)(
                    root / devicelock.LOCK_NAME, "L53", msg_)

    if args.device:
        print(f"LINT: {len(matrix)} device(s) matching {args.device} - "
              "PARTIAL RUN, portfolio matrix and cross-device checks skipped. "
              "Run without --device before committing")
    else:
        print_matrix(matrix, schemas)

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
