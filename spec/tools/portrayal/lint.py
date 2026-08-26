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
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

import attrsections as attrs_mod
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
            contract = yaml.safe_load((base / "contract.yaml").read_text()) or {}
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
        sub = yaml.safe_load(found.read_text()) or {}
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
    sub = yaml.safe_load(found.read_text()) or {}
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
DRAW_CLASSES = ("line-card", "supervisor", "fabric", "switch", "fan", "cooling",
                "transceiver")
SUPPLY_CLASSES = ("psu", "power")
# `switch` is here because all three components carrying it are chassis CARDS in
# rear slots - casa/lc-sw-bdm and smm-sw-bdm-a/b - sitting in the same bays as
# the io-6p12 cards that ARE counted. Leaving them out made a C100G's coverage
# report short by three modules in its denominator, which is the one failure
# this rule set exists to prevent: a total that omits terms without saying so.
# If a physical toggle ever takes this class it will be asked a question it
# cannot answer; there is none today, and `common/power-button` is `button`.
#
# `blank` is deliberately NOT here. A blank faceplate and a slot cover draw
# nothing, and a blank is the honest occupant of an empty bay rather than a
# module whose figure is missing.
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
            sub = yaml.safe_load(found.read_text()) or {}
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
        sub = yaml.safe_load(found.read_text()) or {}
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
                sub = yaml.safe_load(found.read_text()) or {}
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
            sub = yaml.safe_load(found.read_text()) or {}
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
    spacing was tuned around a c13-inlet that was 20 percent undersized" and the
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
    args = ap.parse_args()
    schemas = Path(args.schemas)
    std_file = schemas / "standards.yaml"
    if std_file.exists():
        STANDARDS.update(yaml.safe_load(std_file.read_text())["standards"])
    # the schemas are YAML too where they are YAML, and a duplicate in the
    # registry would be as silent there as anywhere else
    for f in sorted(schemas.glob("*.yaml")):
        lint_duplicate_keys(f)
    comp_v = load_schema(schemas, "component.schema.json")
    dev_v = load_schema(schemas, "device.schema.json")
    ovl_v = load_schema(schemas, "overlay.schema.json")

    n = 0
    matrix = []
    for root in args.library:
        root = Path(root)
        for f in sorted(root.glob("components/**/contract.yaml")):
            lint_duplicate_keys(f)
            d = lint_component(f, comp_v)
            # a file that would not parse has already been reported; running the
            # rest against None just buries that message under a traceback
            if d is not None:
                _skin_checks(f, d)
                lint_component_parts(f, d, args.library)
                lint_component_mating(f, d, args.library)
                lint_component_aperture(f, d, args.library)
                lint_component_power(f, d)
            n += 1
        for f in sorted(root.glob("devices/**/device.yaml")):
            lint_duplicate_keys(f)
            d = lint_device(f, dev_v, args.library); n += 1
            if d is not None and d.get("kind") == "device":
                matrix.append((f, d))
        for f in sorted(root.glob("devices/**/overlays/*.yaml")):
            lint_duplicate_keys(f)
            data = yaml.safe_load(f.read_text())
            for e in ovl_v.iter_errors(data):
                err(f, "L1", f"{'/'.join(str(p) for p in e.path)}: {e.message}")
            n += 1

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
