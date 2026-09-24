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
  L22 device, component: a group's declared media/speed matches the ports it
      holds (a component's groups warn, #511)
  L23 device, component: a port group is one family, or says in `mixed:` why
      it is not
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
  L37 device, component: a group says what it is FOR, and a declared group has
      members
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
  L62 device: an id names the FUNCTION a thing serves, not the connector it is
      built from - the connector is already in `ref:`; and a port lamp is
      spelled the way the library spells it
  L65 component: a DC power part that holds nothing states what it can pass
  L66 device: a power group with more than one bay says whether those bays
      add up or stand in for each other
  L64 device: nothing is bolted to, or printed on, a vent - a perforation is a
      hole in the faceplate and not a surface, so a legend there is printed on
      nothing and a jack there is mounted to nothing
  L67 device: a control-plane or fabric group with more than one bay says
      whether the second card is a working one or a spare
  L68 library: one measurement is spelled one way across devices (ERROR), and a
      fact worth comparing has a name the comparison layer knows (census)
  L69 device: a cooling group with more than one bay says how many of those
      fans the box can lose
  L70 device: a declared vendor silence names a fact that exists, and is not
      contradicted by the device stating that fact anyway
  L76 device: an Ethernet RJ45 is a lamped part and a console or timing RJ45 is
      a bare one - counted, so the two-component convention cannot grow back
      (census; see docs/rj45-family-design.md)
  L89 library: a component major no device reaches carries `unplaced:` saying
      what would seat it - and a part that IS reached does not still carry one
  L117 component: a part `on` a facet names a relief feature that declares
      `facet`, whose node is a declared element, and its projected box lies
      within that element; a facet does not also declare `out`, `profile` or
      `profile-y`
"""
import argparse
import types
import contextlib
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from portrayal import attrsections as attrs_mod
from portrayal import facets
from portrayal import libwalk
from portrayal import capability
from portrayal import dcim_export
from portrayal import devicelock
from portrayal import manifest as _manifest
from portrayal import optical
from portrayal import optical_ports
from portrayal import stacks
from portrayal.faces import DIRECTIONS, OPTICAL_FACES, face_ref
from portrayal.manifest import (view_parts, targets, split_target, presented_interface,
                      VIEW_KEY_ORDER,
                      component_refs, load_yaml, nested_key_host, chained_occupant_ref,
                      drawn_refs, seat_point, slot_default, spanned_slots,
                      spanning_axis, _turn,
                      occupant_spec,
                      PANEL_KEY_ORDER, COMPONENT_KEY_ORDER)
from jsonschema import Draft202012Validator

SEGMENT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# The same test the Explorer applies before it will build state chips. A state
# name is one half of a CSS class - `state-<name>` is what the compiled drawing
# paints on - so anything that is not a token is a class nothing styles.
STATE_TOKEN = re.compile(r"^[a-z0-9-]+$")
# Solid, on and off, or flashing between two colours. Rate is not here yet -
# see the note on `behavior` in the schema.
STATE_BEHAVIORS = {"solid", "blinking", "alternating", "sequence"}
ERRORS = []
WARNINGS = []

# EVERY CODE THE LINTER CAN RAISE, IN ONE PLACE A PERSON CAN READ. A finding
# prints as `path: [Lnn] message`, and the message says what is wrong with this
# file; this table says what the rule IS and what to do about it, which the
# message cannot repeat every time. `--list-rules` prints it; `--list-rules
# --markdown` is what docs/lint-rules.md is generated from, and a test keeps the
# three in step: every code raised here is in this table, every entry here is
# still raised somewhere, and the committed page matches this text.
#
# Scope is what the rule reads: a component contract, a device manifest, an
# overlay, any YAML file, or the library as a whole. L53 is listed because a
# reader meets the code; it is enforced by devicelock.py rather than here.
RULES = {
    "L0":  ("any yaml",   "the file parses as YAML", "fix the syntax the message points at; a `#` after a space inside an unquoted string starts a comment"),
    "L1":  ("any yaml",   "the file validates against its schema", "the path in the message names the key; the schema's description for it says what is accepted"),
    "L2":  ("any id",     "every id and segment matches ^[a-z0-9]+(-[a-z0-9]+)*$ with no double hyphen", "rename the id; it becomes a DOM id segment in every SVG"),
    "L3":  ("component",  "every contracted element id exists in every declared skin", "add the element to the skin, or remove it from `elements:`"),
    "L4":  ("component",  "each skin's viewBox matches the contract size", "set `viewBox=\"0 0 <w> <h>\"` and mm width/height from `size`"),
    "L5":  ("device",     "placement refs resolve in the library, and instance ids are unique per view", "fix the `ref` (namespace/name@major) or the duplicate id"),
    "L6":  ("device",     "a bay's default appears in its accepts list", "add the default to `accepts`, or change the default"),
    "L7":  ("device",     "region members reference existing instance ids", "name ids that exist in the same view"),
    "L8":  ("device",     "a configuration seats only what its bays accept", "add the occupant to the bay's `accepts`, or seat something the bay takes"),
    "L9":  ("component",  "a conforms-declared size matches spec/schemas/standards.yaml", "take the size from the registry, or drop `conforms` if the part is not the standard aperture"),
    "L10": ("component",  "composed parts resolve, ids are unique, composition does not cycle (depth <= 4)", "fix the `parts:` refs; a part must not compose itself"),
    "L11": ("component",  "interface/mates declarations carry a `mate` connection point, and a wrapper keeps the interface of what it composes", "add `connection-points.mate`; do not change the interface in a wrapper"),
    "L12": ("device",     "mate-to resolves to a receptacle whose interface the occupant mates", "point `mate-to` at the receptacle id; check `interface` and `mates` agree"),
    "L13": ("device",     "two placed components do not occupy the same faceplate area", "move one, or declare `for:`/`under:` when one deliberately sits on the other"),
    "L14": ("device",     "a silkscreen `for:` target exists and is nearby", "name the placement or bay the mark annotates, and anchor the mark at it"),
    "L15": ("device",     "a device at `modelled` or above has a provenance block good enough for the level", "add provenance for every figure, or lower `maturity`"),
    "L16": ("device",     "keys inside a view read in manufacturing order", "reorder: empty, size, panel, silkscreen, components, regions"),
    "L17": ("component, device", "a placement's or part's group is declared under `groups:`, and a component that declares groups puts every port part in one", "declare the group with term, role and index-origin; join the loose port to a group"),
    "L18": ("device",     "a port inherits media from its group rather than restating it", "drop the per-port media, or fix the group's `attrs.media`"),
    "L19": ("device",     "an indicator declares `for:` the thing it indicates", "add `for:` to the lamp placement"),
    "L20": ("component, device", "state names are tokens and each `behavior` is well-formed, on a contract's states, an element's, or a placement's", "a state name is a token like `link`; prose goes in `description`; `behavior` is solid, blinking, alternating or sequence, with `behavior.color` for the second colour"),
    "L21": ("device",     "chassis silkscreen does not sit under a bay where the module covers it", "move the mark, or put it in the module's own skin if the module carries it"),
    "L22": ("component, device", "a group's declared media/speed matches the ports it holds", "fix the group's `attrs`, or move the odd port to its own group"),
    "L23": ("component, device", "a port group is one family, or says in `mixed:` why it is not", "split the group by family, or add `mixed:` naming the job they share"),
    "L24": ("device",     "`attrs.other` is counted so the long tail cannot go quiet", "file each key under its section where one fits; otherwise leave it and accept the count"),
    "L25": ("device",     "one attr key is claimed by one section", "rename one of the two; keys flatten to data-<key>"),
    "L26": ("component",  "every `class: cutout` element is backed by a conforming contract or a part that resolves to one", "add `conforms`, or compose the std/ part that owns the aperture"),
    "L27": ("component",  "a power-bearing module states its power figure or records that no document holds it", "add `power-output-w` or `power-draw-max-w` from the guide's appendix, or leave the warning as the record"),
    "L28": ("component",  "a power figure says which way it points and its min/typical/max are ordered", "use `power-output-w` for supplies and `power-draw-*-w` for consumers; never `watts`"),
    "L29": ("device",     "a chassis says how many of the modules it accepts have no figure", "walk the list; each is either in a document you missed or stays as the record"),
    "L30": ("device",     "a card whose figure covers its paired module does not sit beside a module that also states its own", "decide which figure carries the pair and say so"),
    "L31": ("device",     "a region's label matches the group or id it frames", "fix the label text or the region's members"),
    "L32": ("any yaml",   "no mapping declares the same key twice", "remove the duplicate; YAML keeps the last silently"),
    "L33": ("device",     "a bay reserves room for every module it accepts", "size the bay to the largest `insert`/`size` it accepts, or remove the module from `accepts`"),
    "L34": ("device",     "front and rear occupants of one slot fit around the midplane", "check the two depths against chassis depth; one of them is wrong"),
    "L35": ("component",  "a relief magnitude says where it came from", "add `confidence` and `source` to each `relief.features` entry"),
    "L36": ("component",  "a `borrowed` relief magnitude names an origin that actually measured it", "name a part whose own figure is `measured` or `photo-measured`, or use `estimated`"),
    "L37": ("component, device", "a group says what it is for and has members", "add `role`; delete a group nothing joins"),
    "L38": ("component",  "printed text in a skin sits in `<g id=\"silkscreen\">` unless the part is applied over the panel", "wrap the text nodes in the silkscreen group"),
    "L39": ("device",     "the panel's holes agree with what goes in them: no overlap, standard sizes, no legend on a hole, every port has one where cutouts are declared", "fix the cutout size/position, or the placement; one wrong `ref` shows as many overlaps"),
    "L40": ("device",     "a pluggable cage says which optics run in it, and optics prose names a group that exists", "add the group's optics attrs, or fix the group name in the prose"),
    "L41": ("device",     "a bay or placement scoped to configurations names ones that exist, not all, not none", "fix `only-in`"),
    "L42": ("device",     "a silkscreen mark says what it annotates, or `chassis` for printing about the whole unit", "add `for:`"),
    "L43": ("device",     "a front or rear view as wide as the rack face still has its ears in it", "model the body between the ear folds; record the ear extent in provenance"),
    "L44": ("device",     "panel decor agrees with the face: a patterned field is not buried under parts, printing does not run off the edge", "move or trim the decor"),
    "L45": ("device",     "a view at `modelled` draws something or declares itself empty", "add content, or an `empty:` sentence of 40+ characters saying where you looked"),
    "L46": ("component",  "composed parts do not collide inside the part", "move a part, or say in provenance that the layering is deliberate"),
    "L47": ("component",  "a state nothing draws is not declared", "draw a lamp element for the state, or remove the state"),
    "L48": ("component",  "a bay the contract declares is drawn by a skin", "draw the bay opening in every skin, or remove the bay"),
    "L49": ("device",     "members of one group, cut to one size, sit on one pitch", "re-measure; an uneven pitch is usually a mis-read, not a finding"),
    "L50": ("component",  "printing inside a skin is legible at the size it is set", "raise the font size or drop the text"),
    "L51": ("component",  "a class has a power role in spec/schemas/power-roles.yaml", "add the class under `draw`, `supply` or `passive` in power-roles.yaml"),
    "L52": ("component",  "a stated power figure says where it was read from", "add the provenance key the message names"),
    "L53": ("device",     "content changed without the version bump the change requires (see devicelock)", "bump `version`: patch for wording, minor for additions, major for geometry or ids"),
    "L54": ("device",     "a gap's scope names a group, view, configuration, id or attribute the device has", "fix the `scope`, or drop it"),
    "L55": ("library",    "every vendor namespace is in spec/schemas/vendors.yaml", "add the vendor to the registry with display, role and source"),
    "L56": ("overlay",    "an overlay's identity names a software vendor the registry knows", "add the NOS vendor to vendors.yaml"),
    "L57": ("device",     "exactly one configuration is `kind: base`, and each says whether it is orderable", "set `kind` on every configuration"),
    "L58": ("component",  "a cage's own connection point agrees with the aperture inside it", "move the connection point to the composed aperture's"),
    "L59": ("device",     "SKUs live on configurations, not at the top level", "move `part-numbers` into the configuration they belong to"),
    "L60": ("device",     "a face that declares itself empty is actually bare", "remove the `empty:` or the content; not both"),
    "L61": ("device",     "a legend is centred on the thing it names, or plainly not trying to be", "centre it, or move it clear"),
    "L62": ("device",     "an id names the connector the way the rest of the library does", "use the convention the message quotes (e.g. `port-N`, `led-port-N`)"),
    "L63": ("device",     "a configuration binds each face to a view that draws that face; a hole is derived from its part, not drawn around it", "fix the `views` binding, or derive the cutout from the placement"),
    "L64": ("device",     "nothing is bolted to, or printed on, an air hole", "move the part or the mark off the vent field"),
    "L65": ("component",  "a DC power part with nothing seated states what it can pass", "add `power-output-w` for the PEM/terminal"),
    "L66": ("device",     "a power group with more than one bay states its redundancy", "add `attrs.redundancy` (e.g. `1+1`) and a `redundancy-note` citing the guide"),
    "L67": ("device",     "a control-plane or fabric group with more than one bay states its redundancy", "as L66, for the RE/RP/fabric group"),
    "L68": ("library",    "a measurement keeps one attr name and one section across the library", "use the name the message quotes"),
    "L69": ("device",     "a cooling group with more than one bay says how many fans it can lose", "add `attrs.redundancy` (e.g. `n+1`) and a note"),
    "L70": ("device",     "a `fact:` gap names a real fact and does not contradict the device", "fix the gap's scope or remove it"),
    "L71": ("component",  "a body box reaches no further than the part says it is deep", "shrink the body box or raise `body.depth`"),
    "L72": ("device",     "a bay's `plan:` or `rear:` lands in a view that exists, inside the chassis", "fix the plan view name or the coordinates"),
    "L73": ("component",  "a field prints somewhere, and what prints is a field", "add a `data-from` text node for each field, or remove the field"),
    "L74": ("component",  "a lamp that declares states is painted from the lamp-colour variable", "fill or stroke the lamp node with `var(--led-color, <off colour>)`, not a literal colour"),
    "L75": ("component",  "a slot's structured facts agree with its prose, and lanes fit the connector", "fix `lanes`/`connector` or the description"),
    "L76": ("device",     "the RJ45 census: every Ethernet jack says whether it has lamps", "use std/rj45@2 with the lamp parts, or say in provenance the jack is bare"),
    "L77": ("component",  "a `sink` sits in a cavity, because that is what it measures from", "use `pocket` for a recess in an otherwise solid face"),
    "L78": ("component",  "an optical endpoint names a composed connector and a position it has", "fix the part id or the position number"),
    "L79": ("component",  "no fibre position is claimed twice, and a split's ratios sum to 100", "remove the duplicate path, or fix the ratios"),
    "L80": ("component",  "every fibre position is reached by a path or declared unused with a reason", "route it, or add an `optical.unused` entry saying why it terminates nothing"),
    "L81": ("component",  "a composed pitch respects the standard the part conforms to - equal for a target, no narrower for a floor", "move a target onto the standard's pitch, widen a floor to at least it, or say in provenance why this part differs. Where the placements share an x, make their `rotate` agree so a rotated column can be told from a stacked pair"),
    "L82": ("component",  "a part names its plan drawing one way or the other, never both", "keep `plan:` or `faces.plan`, not both - they mean the same thing"),
    "L83": ("component",  "a declared face names a real component, is not the part itself, and that component has no face of the same direction", "fix the ref, or drop the face it names if the chain has no meaning"),
    "L84": ("component",  "a face-qualified optical endpoint names a face the part declares", "add the face to `faces:`, or fix the prefix on the endpoint"),
    "L85": ("component",  "only a face that is another side of the module draws fibres of its own", "move the connector onto the face that really carries it, or extend `faces.OPTICAL_FACES` if this direction genuinely is another side"),
    "L86": ("component",  "a module composing a connector the enum spells two ways states its polish", "add `optical.polish: upc` or `apc`, and say in provenance where it came from"),
    "L87": ("component",  "a module naming what its rear IS has a rear face to name", "add `faces.rear`, or drop `optical.rear-kind`"),
    "L88": ("component",  "a fibre face with more than one row of connectors states its own front numbering", "add `optical.front-order` listing the fibre part ids in the vendor's printed order"),
    "L89": ("library",    "every component major is reachable from a device, or says why it is not", "seat it in a device or in a seated part's bay, or add `unplaced:` saying what would seat it and what is missing"),
    "L90": ("device",     "a manifest's top-level keys read in the canonical order", "reorder them; the message prints the order, and docs/device-template.yaml is written in it"),
    "L91": ("device",     "airflow is stated once - on the chassis, and on a configuration only where it differs", "move it to `chassis.airflow`, or drop the configuration's copy"),
    "L92": ("component",  "a part's size says where it came from", "add a `size:` provenance note; the key for a size is `size`, not a sentence about it"),
    "L93": ("device",     "a provenance entry says how the figure is known, not only where it was read", "add `confidence:` beside the note, from the eight words in the confidence enum"),
    "L94": ("device",     "a `component-attrs` key names a component the device seats, or a placement or bay it declares", "fix the key; one that matches neither sets nothing and is silently ignored"),
    "L95": ("component",  "a power supply says where power enters it", "compose an inlet part, or add `attrs.inlet` from the enum - `none` if the chassis carries it"),
    "L96": ("component",  "a module composing a pluggable cage says what rate it runs at", "add the media attr for that family - `sfp`, `sfp-plus`, `qsfp`, `qsfp28`, `qsfp-dd` - with the port count"),
    "L97": ("component",  "a part that states a size says where each dimension came from", "add `size-confidence: {w: ..., h: ...}` from the confidence vocabulary, and `size-notes` where it needs a sentence"),
    "L98": ("component",  "a character display says how wide it is, and every reading fits", "add `characters:` to the `class: display` element, and keep each `messages[].text` inside it"),
    "L99": ("component",  "a generic stays generic - no rate, reach, wavelength or wattage under generic/", "move the figure to the vendor wrapper's attrs; a generic/ part stands for every module of its kind"),
    "L100": ("component, device", "no key in an `attrs:` map has a null value", "add the missing colon and a value; in flow style `{a: 1, b}` is TWO keys, the second null"),
    "L101": ("component",  "a `superseded-by` names a component major that exists and is not the part itself", "fix the ref, or add the successor if it has not landed yet"),
    "L102": ("component, device", "a device's pluggable media, and a part's `rate` attr, each name a rate spec/schemas/pluggables.yaml actually carries", "fix the media/rate, or add the missing rate to the family in pluggables.yaml"),
    "L103": ("library",    "a pluggable family's `interface` matches at least one component's `interface`", "model the cage, or leave the family as-is if the vocabulary needs it ahead of the metal (sfp-dd today)"),
    "L104": ("device",     "a port's declared media and its cage's presented interface name the same pluggable family", "the declared media governs the accept list render.py's cages[] builds - check the source and fix whichever of the drawing's aperture or the declared media is wrong"),
    "L105": ("device",     "a placement's `interfaces:` are held by a port, named once in the view, and never the id of a placement or bay", "rename the colliding placement or interface - both are real and a DCIM needs a name for each - or move `interfaces:` onto the cage that presents them"),
    "L106": ("component",  "`interface-at` names a declared connection point, and a connection point's `on:` names a `relief.features[]` node that carries an `out`", "fix the name, or give the feature the `out` a part seated on it stands off by; a point on the part's own face needs no `on:`; quote the key (`'on':`) - a bare `on` is YAML boolean true"),
    "L107": ("component, device", "no quoted run in a contract or manifest is longer than 25 words - a vendor's facts are transcribed, its prose is not reproduced", "paraphrase and cite the section (\"the ASR 9903 guide, Power Supply LEDs, says a flashing green lamp means...\"); a state table becomes `state = meaning` pairs, not a quotation"),
    "L109": ("component",  "a declared `optical.polarity` is what the paths actually wire - A straight, AF pair-flipped (and its rows exchanged at 24 fibres), universal", "fix the paths or the polarity; the paths are the evidence, `polarity` is only the claim"),
    "L110": ("component, device", "a port's `speed` is one of the closed set in spec/schemas/speeds.yaml - the highest native rate the port runs at, and nothing else", "spell the rate from the set (a 10/100/1000 jack is `1g`); media goes in `media`, a USB generation in `usb`, a PON flavour in `pon`, a caveat in the placement's `description`"),
    "L108": ("component, device", "a belly-to-belly SFP/QSFP/QSFP-DD cage pair faces the library's way - upper 0 over lower 180, or left 270 beside right 90 on a card drawn on its side - so both bails face outward (OSFP stacks are not checked)", "turn the pair; where a recorded reading says the stack is built otherwise, name the pair in `stack-exceptions:` with that reading as its `reason`"),
    "L111": ("library",    "an alias names one box - no two devices claim the same `aliases[].name` (case-insensitive) unless every claimant marks it `shared: true`, and no alias repeats its own or another device's `model`", "drop or rename the alias; if an OEM name really maps to either of a pair, set `shared: true` on it in EVERY claimant and say why in its `note`"),
    "L112": ("component",  "a connector draws a node 1..N for each of its optical.positions, and a cassette's rear face reuses no front id", "compose a bore with the position's number as its id, or declare an element of class fibre; rename a clashing rear id"),
    "L113": ("device",     "a device port whose effective media carries a network interface (a pluggable cage, or `rj45`) has a `speed` and a group with a `role` - warning at `modelled`, error at `verified`", "add the rate the source states, on the port or its group; a console, timing or alarm jack takes the media that says so (`rj45-serial`, `rj45-tod`, `rj48`) instead of a speed; where no document states a rate, leave it and record the search in `gaps:`"),
    "L114": ("component",  "a `default:` - on a `parts:` entry or at a component's top level - sits on a slot (a part presenting a pluggables family or a registered connector interface) and names a part that slot accepts", "name a ref the slot's `accepts` lists (components.json `cages`), or remove the `default:` from a part that presents no slot; `\"\"` ships a slot empty"),
    "L115": ("component, device", "a slot that SPANS others (an LC duplex adapter over its two bores) and the slots it spans are never both filled - by a configuration, or by what the parts ship", "empty the level you do not want: an empty string on the bores to seat a duplex connector, or one on the adapter's own slot to seat a simplex part in a bore"),
    "L116": ("component",  "a component presenting a spanning connector interface really hosts what it spans - the number of bores the registry says, at the standard's pitch, with its own `mate` at their midpoint, its bores at the depth that point presents, and the axis it derives putting a duplex connector's latches on its bores' keyway side - and a component MATING one is drawn on the canonical axis, the pair running across from its own `mate`", "place the bores at the interface pitch spec/schemas/standards.yaml records, put `mate` on their midpoint, and give each bore the `lift` the feature that point sits `on:` stands at - or drop the `interface:`, because an adapter off the pitch presents no duplex connector; compose the bores in the order whose derived axis carries the latch into the keyway, all at one `rotate`; draw a duplex connector itself with its pair ACROSS and its latches up, because the host's own axis arrives with the seat"),
    "L117": ("component",  "a part `on` a facet names a relief feature that declares `facet`, whose node is a declared element, and its projected box lies within that element; a facet does not also declare `out`, `profile` or `profile-y`", "name the facet feature's node in `on`, declare the node in `elements`, move the part onto the facet, or drop the hand-written slope - the renderer derives it"),
}

# A CODE HANDED OUT TO WORK THAT HAS NOT LANDED YET. Two branches written at
# once cannot both take the next number, so one takes the one after and the
# gap is named here rather than read as a deleted rule. The catalogue test
# counts these as present, and fails once a reserved code is also in RULES -
# whichever branch lands second deletes its line.
RESERVED = {}


def rules_text(markdown=False):
    """The catalogue, for a terminal or for docs/lint-rules.md."""
    order = sorted(RULES, key=lambda c: int(c[1:]))
    if not markdown:
        return "\n".join(f"{c:<4} {RULES[c][0]:<18} {RULES[c][1]}\n     fix: {RULES[c][2]}" for c in order)
    lines = ["# Lint rules",
             "",
             "Generated by `python3 spec/tools/portrayal/lint.py --list-rules --markdown`;",
             "a test fails when this page and the linter disagree. A finding prints as",
             "`path: [Lnn] message`: the message is about the file, this page is about the rule.",
             "",
             "| code | scope | the rule | what to do |",
             "|---|---|---|---|"]
    for c in order:
        scope, rule, fix = RULES[c]
        lines.append(f"| {c} | {scope} | {rule} | {fix} |")
    return "\n".join(lines) + "\n"



@contextlib.contextmanager
def collecting():
    """Findings from the rules called inside this block, and nothing else.

    THE DANCE THIS REPLACES was written out 32 times across the suite:

        saved_e, saved_w = lint.ERRORS[:], lint.WARNINGS[:]
        lint.ERRORS.clear(); lint.WARNINGS.clear()
        try:
            lint_device_alignment(path, doc, [LIB])
            return [w for w in lint.WARNINGS if "L61" in w]
        finally:
            lint.ERRORS[:], lint.WARNINGS[:] = saved_e, saved_w

    Most of the 32 skipped the save and the restore and only cleared, which
    works right up until a rule under test leaves a finding behind and an
    unrelated test three files later reads it. That failure names the wrong
    test, which is the worst kind to debug.

    NOT A CONTEXT OBJECT THREADED THROUGH THE RULES, and #302 records the
    measurement behind that: `warn()` and `err()` are called 208 times across
    ~95 rule functions, all of which would take the parameter, plus the 32 test
    files - a whole-file rewrite of the project's most important gate that could
    not be reviewed as a diff. The review's justification for it was that the
    globals "block testing rules in isolation", and 32 files already test rules
    in isolation. What was true is that the dance repeats and is easy to get
    wrong. This is that, and only that.

        with lint.collecting() as found:
            lint.lint_device_alignment(path, doc, [LIB])
        assert [w for w in found.warnings if "L61" in w]
    """
    saved_e, saved_w = ERRORS[:], WARNINGS[:]
    ERRORS.clear()
    WARNINGS.clear()
    found = types.SimpleNamespace(errors=ERRORS, warnings=WARNINGS)
    try:
        yield found
    finally:
        # THE LISTS ARE HANDED OUT, so they are copied before being restored -
        # a caller that reads `found.warnings` after the block would otherwise
        # be reading whatever the outer run had collected.
        found.errors, found.warnings = ERRORS[:], WARNINGS[:]
        ERRORS[:], WARNINGS[:] = saved_e, saved_w


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
# qsfp112 IS IN THE QSFP FAMILY FOR THE SAME REASON THE REST ARE: it is the 400G
# four-lane QSFP, one generation past qsfp56, and the cage is mechanically the
# same - std/qsfp-ganged@1 seats it unchanged. Left out, L22 accused every one of
# the EXP400-32X's thirty-two ports of contradicting its own group.
MEDIA_FAMILY = {
    "sfp": "sfp", "sfp-plus": "sfp", "sfp28": "sfp", "sfp56": "sfp",
    "qsfp": "qsfp", "qsfp-plus": "qsfp", "qsfp28": "qsfp", "qsfp56": "qsfp",
    "qsfp112": "qsfp", "qsfp-dd": "qsfp",
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
    _CLASS_CACHE[ref] = cls = (libwalk.load_contract(ref, lib_roots) or {}).get("class")
    return cls


def contract_size(ref, lib_roots):
    """The `size` a component declares, or None. Cached alongside class and attrs -
    L21 asks per placement and a 248-placement view would re-read otherwise."""
    if ref in _SIZE_CACHE:
        return _SIZE_CACHE[ref]
    # A MALFORMED REF IS None, NOT A ValueError. This one caught the unpack
    # locally and three siblings beside it did not; `split_ref` answers it once,
    # for every caller.
    _SIZE_CACHE[ref] = size = (libwalk.load_contract(ref, lib_roots) or {}).get("size")
    return size


def contract_attrs(ref, lib_roots):
    if ref in _ATTRS_CACHE:
        return _ATTRS_CACHE[ref]
    _ATTRS_CACHE[ref] = attrs = (libwalk.load_contract(ref, lib_roots) or {}).get("attrs") or {}
    return attrs


def contract_elements(ref, lib_roots):
    """The element ids a component contracts, for L20's per-element states form."""
    if ref in _ELEMENTS_CACHE:
        return _ELEMENTS_CACHE[ref]
    _ELEMENTS_CACHE[ref] = els = set(
        ((libwalk.load_contract(ref, lib_roots) or {}).get("elements") or {}).keys())
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
            # A LETTER GLUED TO ITS NUMBER - `M0 0 L40 0` - dropped that number
            # from the token count and shifted every pair after it, so a 40mm
            # plate measured 20 x 20. Read the subpaths where they can be read.
            if tag == "path":
                rings = _subpaths(d)
                if rings:
                    pts = [q for r in rings for q in r]
                    return (min(q[0] for q in pts), min(q[1] for q in pts),
                            max(q[0] for q in pts), max(q[1] for q in pts))
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
    contract = libwalk.contract_path(ref, lib_roots)
    if contract is None:
        _PAINT_CACHE[key] = None
        return None
    # ONE ITERATION, because `contract_path` already searched the roots in
    # order and answered which one holds it. The loop here was the search
    # repeated, and its `continue` meant a ref present in a later root read its
    # skins from a root that did not have the contract.
    for base in [contract.parent]:
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
            parts = composed_part_boxes(ref, lib_roots)
            boxes = None if parts is None else boxes + parts
        break
    _PAINT_CACHE[key] = boxes
    return boxes


def composed_part_boxes(ref, lib_roots):
    """The boxes a component's `parts:` occupy, in component-local mm, or None
    when one of them has no size to measure."""
    contract = libwalk.load_contract(ref, lib_roots) or {}
    boxes = []
    for p in contract.get("parts") or []:
        psz = contract_size(p.get("ref", ""), lib_roots) or {}
        if not (psz.get("w") and psz.get("h")):
            return None
        px, py = (p.get("at") or [0, 0])[:2]
        boxes.append((px, py, px + psz["w"], py + psz["h"]))
    return boxes


# --------------------------------------------------------------- openings ---
#
# A HOLE THROUGH A PART IS NOT PART OF IT, and every rule that measures a part
# by its box says it is. maiaedge/pbc-2000-bezel@1 is the case that showed it:
# one plate across the whole face with two octagonal windows cut through it,
# and the ports, legends and louvres of the faceplate seen through them. By its
# box it buries all of those - L44 read both louvre fields as 100% buried and
# L21 read three legends as painted over, and all five were exactly where the
# photograph puts them.
#
# THE HOLES ARE READ FROM THE RELIEF, NOT DECLARED A SECOND TIME. A feature
# with `shape: true` already tells the kit to extrude its node's own outline
# and to cut the holes in it (kit/relief.js `ringsOf`), and that is the only
# place the format says "this part has windows". A separate list of openings
# in the contract would be the same octagons typed twice and free to drift from
# the art the viewer actually cuts; reading the art means the 2D rules and the
# 3D model cannot disagree about where the windows are.
#
# The reading mirrors `ringsOf`: every path under the node that is filled (a
# `fill="none"` path is a stroked line, not an area), split into subpaths, and
# a ring whose centroid lies inside a larger one is a hole in it. Only straight
# segments are read - M L H V Z, absolute or relative - and a transform
# anywhere on the way is not composed. Anything else answers NO OPENINGS,
# which is the box, which is what every rule did before: unable to read a hole
# costs a false positive, never a missed one.

_OPENINGS_CACHE = {}


def _subpaths(d):
    """The closed rings of a straight-segment path, or None if it has curves."""
    toks = re.findall(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d or "")
    rings, cur = [], []
    x = y = 0.0
    cmd, i = None, 0
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            if t not in "MmLlHhVvZz":
                return None
            cmd, i = t, i + 1
            if cmd in "Zz":
                if len(cur) > 2:
                    rings.append(cur)
                if cur:
                    x, y = cur[0]
                cur = []
            continue
        if cmd is None or cmd in "Zz":
            return None
        try:
            if cmd in "HhVv":
                v = float(t)
                i += 1
                if cmd == "H": x = v
                elif cmd == "h": x += v
                elif cmd == "V": y = v
                else: y += v
            else:
                a, b = float(toks[i]), float(toks[i + 1])
                i += 2
                if cmd in "ML":
                    x, y = a, b
                else:
                    x, y = x + a, y + b
                if cmd in "Mm":
                    if len(cur) > 2:
                        rings.append(cur)
                    cur = []
                    cmd = "L" if cmd == "M" else "l"   # later pairs are line-tos
        except (ValueError, IndexError):
            return None
        cur.append((x, y))
    if len(cur) > 2:
        rings.append(cur)
    return rings


def _poly_area(ring):
    a = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i - 1]
        x1, y1 = ring[i]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def _in_ring(pt, ring):
    hit = False
    for i in range(len(ring)):
        (ax, ay), (bx, by) = ring[i], ring[i - 1]
        if (ay > pt[1]) != (by > pt[1]) and pt[0] < (bx - ax) * (pt[1] - ay) / (by - ay) + ax:
            hit = not hit
    return hit


def component_openings(ref, skin, lib_roots):
    """The holes through a component, as polygons in component-local mm.

    Read from each relief feature with `shape: true` - see the block above for
    why the relief and not a list of its own. Empty when there are none or when
    the art cannot be read with confidence."""
    key = (ref, skin or "default")
    if key in _OPENINGS_CACHE:
        return _OPENINGS_CACHE[key]
    _OPENINGS_CACHE[key] = holes = []
    contract = libwalk.contract_path(ref, lib_roots) if ref else None
    if contract is None:
        return holes
    feats = [f for f in (((libwalk.load_contract(ref, lib_roots) or {})
                          .get("relief") or {}).get("features") or [])
             if isinstance(f, dict) and f.get("shape") and f.get("node")]
    if not feats:
        return holes
    try:
        root = ET.parse(contract.parent / "skins" / f"{key[1]}.svg").getroot()
    except (ET.ParseError, OSError):
        return holes
    parents = {c: p for p in root.iter() for c in p}
    for f in feats:
        node = next((e for e in root.iter() if e.get("id") == f["node"]), None)
        if node is None:
            continue
        up, ok = node, True
        while up is not None:
            if up.get("transform"):
                ok = False
            up = parents.get(up)
        paths = [node] if node.tag == f"{_SVG_NS}path" else list(node.iter(f"{_SVG_NS}path"))
        rings = []
        for q in paths:
            if (q.get("fill") or "").strip() == "none":
                continue
            if q is not node and any(e.get("transform") for e in q.iter()):
                ok = False
            r = _subpaths(q.get("d"))
            if r is None:
                ok = False
                break
            rings.extend(r)
        if not ok:
            continue
        rings.sort(key=_poly_area, reverse=True)
        shells = []
        for r in rings:
            c = (sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r))
            if any(_in_ring(c, s) for s in shells):
                holes.append(r)
            else:
                shells.append(r)
    return holes


def placed_openings(p, lib_roots):
    """A placement's openings in view mm: translate(at) rotate(deg w/2 h/2), the
    transform render.py draws it with."""
    if not p.get("at") or not p.get("ref"):
        return []
    holes = component_openings(p["ref"], p.get("skin", "default"), lib_roots)
    if not holes:
        return []
    sz = contract_size(p["ref"], lib_roots) or {}
    cx, cy = sz.get("w", 0) / 2.0, sz.get("h", 0) / 2.0
    th = math.radians(float(p.get("rotate") or 0))
    c, s = round(math.cos(th), 12), round(math.sin(th), 12)
    ax, ay = p["at"][0], p["at"][1]
    return [[(ax + cx + c * (x - cx) - s * (y - cy), ay + cy + s * (x - cx) + c * (y - cy))
             for x, y in r] for r in holes]


def _clip_to_box(ring, box):
    """Sutherland-Hodgman against an axis-aligned box. The subject may be
    concave; the area of what comes back is still the area of the overlap."""
    x0, y0, x1, y1 = box
    out = list(ring)
    for inside, cut in (
            (lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
            (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
            (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
            (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1))):
        src, out = out, []
        for i in range(len(src)):
            a, b = src[i - 1], src[i]
            if inside(b):
                if not inside(a):
                    out.append(cut(a, b))
                out.append(b)
            elif inside(a):
                out.append(cut(a, b))
        if not out:
            return []
    return out


def open_area(box, holes):
    """How much of `box` (x0, y0, x1, y1) lies over the given holes."""
    if not holes or box[2] <= box[0] or box[3] <= box[1]:
        return 0.0
    return sum(_poly_area(c) for c in (_clip_to_box(h, box) for h in holes) if len(c) > 2)


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
        # `sequence` says the pattern IS the phase list, so the phase list has to
        # carry it. A sequence whose phases are all dark is a lamp that never
        # lights, and a colour on the state itself is a colour nothing draws -
        # every frame of the cycle sets its own fill, so the base is overwritten.
        if mode == "sequence":
            phases = beh.get("phases") if isinstance(beh, dict) else None
            if not isinstance(phases, list) or len(phases) < 2:
                err(path, "L20", f"{where}/{name}: behavior sequence is a cycle of "
                                 f"phases - give at least two as behavior.phases, "
                                 f"each {{color, seconds}}, a phase with no colour "
                                 f"being the lamp off")
            elif not any(isinstance(p, dict) and p.get("color") for p in phases):
                err(path, "L20", f"{where}/{name}: every phase of this sequence is "
                                 f"dark, so the lamp never lights. That is state "
                                 f"'off' with extra steps")
            elif isinstance(st, dict) and st.get("color"):
                warn(path, "L20", f"{where}/{name}: state names colour "
                                  f"{st['color']!r} AND a sequence. The phases set "
                                  f"the fill on every frame, so the state colour "
                                  f"reaches nothing - put it in a phase")
        # A rate is a blink frequency. On anything that does not blink it is a
        # number the drawing cannot use, which reads as modelled and is not.
        if isinstance(beh, dict) and beh.get("rate") is not None \
                and mode not in ("blinking", "alternating"):
            warn(path, "L20", f"{where}/{name}: behavior {mode!r} carries a rate, "
                              f"but only blinking and alternating have one. For a "
                              f"sequence the timing is `seconds` on each phase")
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
    # THE DEFAULT HAS TO BE THE ONE THE RENDERER USES. render.py draws an
    # unanchored silkscreen mark CENTRED on its `at` (render.py:880); this read
    # it as running rightward from `at`, so every extent check on the 433 marks
    # in this library that state no anchor was off by half a text width - in the
    # direction that hides an overlap on the left and invents one on the right.
    # A mark then lints as one thing and draws as another, and no rule reports
    # the difference because both halves are working from their own assumption.
    anchor = m.get("anchor", "middle")
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
    # EVERY SCHEMA ERROR, NOT THE FIRST. `return` inside the loop reported one
    # and stopped, so a manifest with four schema faults took four runs to fix -
    # each one a full lint to find the next. The return still happens, because
    # the checks below read a shape the schema has just said is wrong; it happens
    # after the whole file has been reported rather than after one line of it.
    # `lint_overlay` a few thousand lines down has always done it this way.
    schema_errors = list(validator.iter_errors(data))
    for e in schema_errors:
        err(path, "L1", f"{'/'.join(str(p) for p in e.path)}: {e.message}")
    if schema_errors:
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
            # THE ERROR PATH MUST NOT BE THE THING THAT BREAKS. An entry written
            # with `source:` instead of `registry:` used to take down the whole
            # run with a KeyError - and only ever when a component ALREADY
            # disagreed with the registry, so the one moment the message was
            # needed was the one moment it could not be printed. Second time a
            # missing key in a message has crashed lint; name it and carry on.
            origin = std.get("registry") or std.get("source") or "no source recorded"
            # WHICH TWO OF THE THREE THIS CONTRACT DRAWS. A registry entry is a
            # box - w, h and depth - and a contract draws one projection of it.
            # The check used to assume every contract was the elevation, which
            # is why a plan view of a standard part could not `conforms:` to the
            # standard it plainly is: 101.6 x 147.0 is not 101.6 x 26.1, and the
            # only way past it was to restate the numbers in a second file and
            # let them drift.
            pres = data.get("presents", "wh")
            trio = {"w": std.get("w"), "h": std.get("h"), "d": std.get("depth")}
            pair = [trio[k] for k in pres]
            rest = trio[({"w", "h", "d"} - set(pres)).pop()]
            # A PITCH-ONLY ENTRY MAKES NO ENVELOPE CLAIM, so there is no size
            # here to agree or disagree with. Seven entries are this shape - a
            # panel adapter's OPENING is standardised where its bezel is not -
            # and `std["w"]` indexed them, so naming one in `conforms:` ended
            # the run in `KeyError: 'w'`. That is the third time a missing
            # registry key has taken lint down rather than printing a message.
            # The pitch rules below still apply; only the size check is skipped.
            if trio["w"] is None and trio["h"] is None:
                pass
            elif any(v is None for v in pair):
                err(path, "L9", f"conforms {conf}: presents {pres} needs a depth "
                    f"from the registry and {conf} does not give one ({origin})")
            else:
                # ORDER WITHIN THE PAIR IS NOT CHECKED, because which way round a
                # part is turned belongs to the placement, not to the standard.
                # The registry fixes an orientation of its own - drive-35 is
                # described lying flat, drive-25 standing on edge - and a bay is
                # free to disagree. What must not drift are the VALUES.
                got, want = sorted([sz["w"], sz["h"]]), sorted(pair)
                if any(abs(a - b) > 0.05 for a, b in zip(got, want)):
                    err(path, "L9", f"conforms {conf}: size {sz['w']}x{sz['h']} is not "
                        f"the registry's {pair[0]}x{pair[1]} in any order "
                        f"for presents {pres} ({origin})")
                if sz.get("d") is not None and rest is not None \
                        and abs(sz["d"] - rest) > 0.05:
                    err(path, "L9", f"conforms {conf}: depth {sz['d']} != {rest} "
                        f"for presents {pres} ({origin})")
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
                        f"!= registry cavity {cav['w']}x{cav['h']} ({origin})")
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
        # a part's ref, every default it ships holding and every face it
        # names (drawn_refs)
        queue.extend(drawn_refs(spec))
    return files


def resolve_component(ref, lib_roots):
    """Locate a component contract from a `ns/name@major` ref."""
    return libwalk.contract_path(ref, lib_roots)


def lint_component_mating(path, data, lib_roots):
    """L11: mating declarations must be usable and must survive composition."""
    cps = data.get("connection-points") or {}
    for key in ("interface", "mates"):
        if data.get(key) and "mate" not in cps:
            err(path, "L11", f"{key}: {data[key]!r} declared but no 'mate' "
                             "connection-point - nothing to align to")
    # AN OCCUPANT MATES WITH ITS OWN POINT. A host may present a mate point
    # FORWARDED from an aperture it composes (manifest.presented_interface);
    # an occupant may not, and render.py says so where it seats one: "the
    # occupant's is its own: a module is the thing that mates, not a wrapper
    # around one". It raises on a `mate-to` placement whose occupant has no
    # `mate`, so a contract without one is a part that cannot be seated. The
    # renderer refuses it; lint refuses it too, at the contract rather than at
    # the first device that tries.
    if data.get("behaviour") == "occupies" and "mate" not in cps:
        err(path, "L11", "behaviour: occupies and no 'mate' connection-point - "
                         "an occupant mates with ITS OWN point, which is not "
                         "forwarded from a composed part the way a host's is, "
                         "and the renderer refuses to seat it without one")
    # a wrapper may re-present the interface of a receptacle it composes, but it
    # must not present a DIFFERENT one - a plug would mate with the wrapper and
    # land on the wrong geometry
    #
    # A SPANNING INTERFACE IS NOT A CONTRADICTION, and it is the one exception:
    # `lc-duplex` is registered in spec/schemas/connectors.yaml as spanning two
    # `lc` bores, so a duplex adapter presenting `lc-duplex` over two
    # `std/lc-bore@3` is stating that registered relationship rather than
    # changing the interface under a plug's feet (B3, "The duplex host"). What
    # keeps it honest is L116: the bores must be at the interface pitch, and
    # the adapter's own mate on their midpoint, or it presents nothing.
    spans = ((_connectors().get(data.get("interface")) or {}).get("spans")
             if data.get("interface") else None)
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
        if spans and sub_if == spans.get("interface"):
            continue
        if data.get("interface") and data["interface"] != sub_if:
            err(path, "L11", f"declares interface {data['interface']!r} but composes "
                             f"{part['ref']} presenting {sub_if!r}")


def _composes_a_standard(data, lib_roots, depth=0, seen=None):
    """Does anything under `parts:` say what standard it is, transitively?

    A leaf satisfies this by declaring `conforms:` OR `interface:`. `conforms:`
    is the strong form - L9 checks it against the registry to the millimetre -
    but an aperture can name the plug it accepts before the registry has an
    entry for the opening: `std/lc-bore@1` carried `interface: lc` and no
    `conforms:` while 82 `lc-duplex-adapter` placements resolved through it.
    That version is gone (#126) and @2 conforms, but the allowance stands for
    the next aperture that arrives ahead of its standard.
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


def _load_pluggable_families(schemas):
    """The pluggable ladder registry, or an empty one if the checkout is broken.

    Loaded at import beside the vendor registry and the power roles, and for
    the same reason: neither rule that reads it may pass everything in silence
    because the file did not load. L102 asks its question OF THE TREE, so an
    empty registry makes it report every media and rate it is asked about.
    L103 asks its question OF THE REGISTRY, so there is nothing for it to
    iterate - it reports the empty load itself instead, as a finding of its
    own, which is the only form the same promise can take from that side.
    """
    path = Path(schemas) / "pluggables.yaml"
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return doc.get("families") or {}


PLUGGABLE_FAMILIES = _load_pluggable_families(
    Path(__file__).resolve().parents[2] / "schemas")


def _load_port_speeds(schemas):
    """The closed speed vocabulary, in ascending order, or () if the checkout is
    broken. Loaded at import for the reason the registries above are: L110 asks
    its question of the tree, so an empty set makes it report every speed it
    sees rather than pass them all in silence."""
    path = Path(schemas) / "speeds.yaml"
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return ()
    return tuple(str(s) for s in (doc.get("speeds") or ()))


PORT_SPEEDS = _load_port_speeds(Path(__file__).resolve().parents[2] / "schemas")


def _pluggable_rates():
    """Every rate any family on the ladder claims, flattened once per call.

    Cheap - nine families, at most a handful of rates each - so this is not
    cached the way the per-component lookups above are; caching a set this
    small would only add a place for a test's monkeypatched registry to be
    read stale from.
    """
    return {r for fam in PLUGGABLE_FAMILIES.values() for r in (fam.get("rates") or [])}


def _family_mated_by(interface):
    """The (name, family) whose `interface` a `mates` value names, or None.

    `mates` on a transceiver names the cage it plugs into by INTERFACE, the
    same field L11 and L12 already hold a receptacle and its occupant to - so
    this looks the value up as an interface rather than assuming it equals a
    family's own key, which is only true of this registry by coincidence.
    """
    for name, fam in PLUGGABLE_FAMILIES.items():
        if fam.get("interface") == interface:
            return name, fam
    return None


def _family_owning_rate(rate):
    """The (name, family) whose `rates` ladder carries `rate`, or None.

    The reverse of `_family_mated_by`: that answers "whose CAGE is this",
    this answers "whose LADDER is this rate a rung of" - the same question
    `test_pluggable_ladder.py`'s own `owner` dict asks of the whole registry,
    asked here of one value at a time against a real device's group.
    """
    for name, fam in PLUGGABLE_FAMILIES.items():
        if rate in (fam.get("rates") or []):
            return name, fam
    return None


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


def lint_component_size_sourced(path, data, _lib_roots=None):
    """L92: a part's size says where it came from.

    Every figure in this library is supposed to name its source, and `size` is
    the figure everything else is built on - a cutout is derived from it, a bay
    is sized to it, a pitch is measured across it. It was also the one figure no
    rule asked about. 41 of 584 contracts stated a size and had no note named
    for it.

    THIRTEEN OF THOSE FORTY-ONE HAD THE NOTE AND NOT THE NAME, under `extent`,
    `face`, `geometry` or `overall`, which is the vocabulary half of #173: with
    579 distinct provenance keys across 584 contracts - 495 of them used fewer
    than five times, some of them whole sentences like
    `adjacent-brackets-overlap-by-1.27-on-purpose` - a rule cannot ask whether a
    figure is sourced, because the key is prose. The same problem forced L52 to
    accept "any power-named key" after it convicted eighteen contracts that had
    done the work. Those thirteen are renamed; the key for a size is `size`.

    THE OTHER TWENTY-SEVEN REALLY DO NOT SAY. `dell/riser-1a-14g` is 107.59 x
    62.0 and carries eight provenance notes, none of which is about where those
    two numbers came from - they cover the body boxes, the slot numbering, the
    electrical facts and why adjacent brackets overlap. Fourteen Dell risers,
    six Casa parts and four ground plates are in that position.

    A WARNING AND NOT AN ERROR, like L27 next door: it fires on the day it lands
    and is meant to shrink, and the figure being unsourced is a fact about the
    library rather than a mistake in the contract in front of you. An axis that
    needs its own note keeps one - `size-width`, `size-depth` - and counts.
    """
    if not data.get("size"):
        return
    prov = data.get("provenance") or {}
    if not isinstance(prov, dict):
        return
    if any(k == "size" or k.startswith("size") for k in prov):
        return
    warn(path, "L92", "states a size and no provenance key names it. The key for a "
                      f"size is `size` (it carries {', '.join(sorted(prov)[:4]) or 'none'}"
                      "); if the figure has no source, say so there in the words the "
                      "library uses - estimated, borrowed, known-wrong")


def lint_component_dc_capacity(path, data, _lib_roots=None):
    """L65: a DC power part with nothing seated in it says what it can pass.

    THE DISTINCTION THIS EXISTS TO HOLD. A power TRAY carries what the supplies
    seated in it produce, so watts are the wrong unit for it and `power-absent`
    is the honest answer - the Cisco a9k trays declare `module-bays: 4` and those
    four supplies each state their own output. A POWER ENTRY MODULE holds
    nothing. On a DC chassis it is the only path power takes into the box, so
    there is no other part to carry the figure, and a chassis whose input
    capacity is stated nowhere cannot answer "how much can this take".

    Both had the same `power-absent: not-applicable` and the same conduit
    argument in their provenance, because the argument was written for the tray
    and inherited by the PEM. Nothing caught it: the Casa PEMs sat unrated until
    somebody looked at a chassis in another tool and asked where the wattage was.

    So the test is not the class or the word DC in a role - it is whether
    anything SEATS in it. A part that holds modules may defer to them; one that
    holds nothing may not.

    A CEILING COUNTS. `power-output-w` with `power-output-scope:
    pass-through-ceiling` is a real answer for a part that neither converts nor
    regulates - it bounds what the metal may pass. What is not an answer is
    silence.
    """
    attrs = data.get("attrs") or {}
    if data.get("class") not in SUPPLY_CLASSES:
        return
    role = str(attrs.get("role") or "")
    inp = f"{attrs.get('input') or ''} {attrs.get('input-voltage') or ''}".lower()
    dc = "dc" in role.lower().split("-") or "vdc" in inp or attrs.get("input") == "dc"
    if not dc:
        return
    # anything seated in it may carry the figure instead
    if attrs.get("module-bays") or data.get("module-bays") or data.get("accepts"):
        return
    if any(str(attrs.get(k) or "").strip() for k in SUPPLY_KEYS):
        return
    # `not-published` IS AN ANSWER and is left alone. It says the figure was
    # looked for and the vendor does not give it, and L52 already makes it name
    # the documents - the Edgecore AGR DC supply lists four and explains why an
    # output cannot be had from an input current. What this rule is about is the
    # OTHER claim: `not-applicable` means watts are the wrong unit, and a part
    # that holds nothing cannot say that, because there is nothing else to hold
    # the number.
    if str(attrs.get("power-absent") or "") == "not-published":
        return
    warn(path, "L65", f"{data.get('name')} takes DC and holds nothing, and states no "
         f"{SUPPLY_KEYS[0]}. A tray may defer to the supplies seated in it; a part with "
         "no bays cannot, and on a DC chassis this is the only place the input capacity "
         "can be stated. If it neither converts nor regulates, a pass-through ceiling "
         "derived from the feeds and their fusing is a real answer - say so with "
         "`power-output-scope: pass-through-ceiling` and show the arithmetic in "
         "provenance. If the vendor really publishes nothing, say `power-absent: "
         "not-published` and name the documents - that is an answer. "
         "`not-applicable` is not, for a part with no bays")


def lint_component_size_confidence(path, data, _lib_roots=None):
    """L97: a part that states a size says where each dimension came from.

    A SIZE IS THE ONE FIELD EVERYTHING DOWNSTREAM TRUSTS, and 502 of the 526
    parts that state one said nothing about where it came from. `size-confidence`
    has existed all along - the schema describes it, `components_index` tallies
    it - and 24 parts used it, so the tally counted almost nothing and the gap
    it exists to show stayed quiet. An instrument nobody fills is the shape
    docs/failure-by-omission.md is about.

    WHY PROSE CANNOT DO THIS, which is the part worth keeping. 104 Juniper
    contracts are sized from their chassis slot rather than from the card, and
    their `provenance/size` says so honestly:

        registry + layout - the face is the slot geometry of its chassis family
        ... NOT measured from a faceplate drawing

    Any search of that prose for a confidence word finds `measured`, in the
    sentence that exists to deny it. #261 found the group by PARSING provenance
    rather than grepping it, and a rule that grepped would have called all 104
    measured - which is worse than saying nothing, because it would have been
    believed.

    A CENSUS WARNING of the L92/L93 kind: it fires on what is unstated and is
    meant to shrink. `estimated` is an answer and so is `known-wrong`; silence
    is not, because silence reads exactly like `measured` to anything that has
    only the number.
    """
    size = data.get("size") or {}
    if not size:
        return
    conf = data.get("size-confidence") or {}
    missing = [dim for dim in ("w", "h", "d") if size.get(dim) is not None and not conf.get(dim)]
    if not missing:
        return
    warn(path, "L97", f"states {', '.join(missing)} and does not say where "
         + ("they came" if len(missing) > 1 else "it came") +
         " from. Add `size-confidence` from the vocabulary - measured, "
         "photo-measured, drawing, datasheet, registry, borrowed, estimated, "
         "known-wrong - with `size-notes` where it needs a sentence. A number "
         "nobody has measured reads exactly like one somebody did")


def lint_component_display(path, data, _lib_roots=None):
    """L98 - a character display says how wide it is, and every reading fits.

    A DISPLAY IS THE ONE INDICATOR THIS LIBRARY COULD NOT ASK A QUESTION OF.
    `class: display` has existed since the Cisco route processors landed and it
    carried a description and nothing else: thirty elements that a reader could
    see were displays and could not ask how many characters they showed or what
    any of them said. The ASR 9901 recorded that as a gap in so many words - "a
    four-character LED matrix has no element class ... `class: led` takes
    colours and this display takes strings" - and this is the other half of
    closing it.

    THE CAPACITY IS WHAT MAKES THE VOCABULARY CHECKABLE. Without `characters` a
    `messages` list is a list of strings nobody can be wrong about; with it, a
    five-character reading on a four-character display is a transcription error
    a rule catches on the day it is written rather than a reader catching it
    years later, or not. That is the whole argument for asking for a number that
    is otherwise only ever equal to what the drawing already shows.

    IT DOES NOT ASK FOR `messages`, and that is deliberate. A seven-segment cell
    is a display whose vocabulary is per-cell glyphs and belongs in `states`; a
    window that frames two digits is a display with no vocabulary of its own at
    all. Requiring messages would push both into inventing one. What every
    display can answer is how wide it is.
    """
    for eid, spec in (data.get("elements") or {}).items():
        if not isinstance(spec, dict):
            continue
        cls = spec.get("class")
        msgs = spec.get("messages") or []
        cells = spec.get("characters")
        if msgs and cls != "display":
            err(path, "L98", f"element {eid} carries `messages` and is class "
                             f"{cls!r}. A message vocabulary is what a DISPLAY "
                             f"reads; a lamp's vocabulary is `states`")
            continue
        if cls != "display":
            continue
        if not cells:
            warn(path, "L98", f"display {eid} does not say how many characters "
                              f"it shows. Add `characters:` - it is what a "
                              f"reading has to fit in, and the only thing that "
                              f"makes a `messages` list checkable")
            continue
        for m in msgs:
            text = str((m or {}).get("text", ""))
            if len(text) > cells:
                err(path, "L98", f"display {eid} shows {cells} characters and "
                                 f"lists the reading {text!r}, which is "
                                 f"{len(text)}. One of the two was mis-read")


GENERIC_FORBIDDEN_ATTRS = ("speed", "reach", "wavelength", "mode",
                           "power-draw-max-w", "power-draw-typical-w")
GENERIC_RATE_TOKENS = re.compile(
    r"(^|-)(sfp28|sfp56|sfp-plus|qsfp28|qsfp56|qsfp112|qsfp-dd800|"
    r"1000base[a-z0-9-]*|"
    r"\d+g|\d+gbase[a-z0-9-]*|\d+km|\d+m)(-|$)")


def lint_component_generic(path, data, _lib_roots=None):
    """L99 - a generic stays generic.

    A `generic/` transceiver stands for every module of its kind, which is the
    whole reason it exists: `generic/sfp-lc` is an SFP, an SFP+ and an SFP28
    alike, and the rate, the reach, the wavelength and the watts are facts about
    the vendor's product that the WRAPPER carries (docs/pluggables-design.md,
    decision 5). `common/sfp-lc-duplex` carried `mode: single-mode, reach: 30km,
    speed: 100m` for a year - a specific module wearing a generic's name - and
    nothing could say so. This can.

    Namespace, not class: a vendor optic is SUPPOSED to carry these attrs, so the
    rule reads the path and asks only under `generic/`.
    """
    if not isinstance(data, dict) or data.get("class") != "transceiver":
        return
    # THE NAMESPACE IS A POSITION, NOT A SUBSTRING: a contract lives at
    # <lib>/components/<ns>/<name>/v<major>/contract.yaml, so the namespace is
    # the fourth part from the end. Asking whether "/generic/" appears anywhere
    # in the path made every vendor optic in a checkout under a directory
    # NAMED generic answer yes.
    is_generic = Path(path).parts[-4:-3] == ("generic",)
    if not is_generic:
        return
    attrs = data.get("attrs") or {}
    hit = [k for k in GENERIC_FORBIDDEN_ATTRS if k in attrs]
    if hit:
        err(path, "L99", f"{data.get('name')} is a generic and carries "
                         f"{', '.join(hit)}. A generic stands for every module of "
                         "its kind; the figure belongs on the vendor wrapper's attrs")
    name = str(data.get("name") or "")
    if GENERIC_RATE_TOKENS.search(name):
        err(path, "L99", f"{name} names a rate. A generic is named by form factor "
                         "and face - sfp-lc, qsfp-mpo12 - never by what runs in it")


def lint_component_cage_rate(path, data, _lib_roots=None):
    """L96: a module composing a pluggable cage says what rate it runs at.

    THE CAGE SAYS WHAT FITS; THE CARD SAYS WHAT RUNS. An SFP housing takes a 1G
    optic and a 10G one, so the DCIM export reads the family from the cage ref
    and the rate from a media attr on the card - and falls back to a per-cage
    DEFAULT when the card declares none. That fallback is a default standing in
    for a fact, and it was reached by 1215 placements across 114 cards with
    nothing anywhere to say so.

    IT HAS BEEN WRONG AT LEAST SEVEN TIMES. `dpce-r-40ge-sfp` exported forty 10G
    interfaces on a card whose model number and description both say 40x1GbE;
    `mic3-3d-2x40ge-qsfpp` exported two 100G ports on a 40GbE MIC; A9K-40GE-B
    did the identical thing in roc-ops/Portrayal#23, three years earlier, and was fixed by
    stating `sfp: 40`. It came back because nothing counted the fallback - which
    is #294, and the shape docs/failure-by-omission.md is about.

    A CENSUS WARNING of the L92/L93 kind: it fires on the day it lands and is
    meant to shrink. Most of what it names is probably right - an SFP-ganged
    strip on a modern line card usually is SFP+ - and "probably right" is
    exactly what cannot be told from "wrong" without asking.

    A FAMILY WITH NOTHING TO DECLARE IS NOT A GAP. XFP runs at one rate and
    `FAMILY_ATTRS` gives it no attrs, so an XFP cage answers for itself and is
    not counted here.
    """
    if data.get("kind") != "module":
        return
    attrs = attrs_mod.flatten(data.get("attrs"))
    want = {}
    for part in (data.get("parts") or []):
        if not isinstance(part, dict) or "ref" not in part:
            continue
        ref = part["ref"].split("@")[0]
        if dcim_export.cage_family_needs_a_rate(ref, attrs):
            want[ref] = want.get(ref, 0) + 1
    if not want:
        return
    for ref, n in sorted(want.items()):
        fam = dcim_export.CAGE_FAMILY[ref]
        names = ", ".join(f"`{a}`" for a, _t in dcim_export.FAMILY_ATTRS[fam])
        warn(path, "L96", f"{n} x {ref} and nothing says what rate they run at, so "
             f"the export types them {dcim_export.PART_IFACE.get(ref)} from the table. "
             f"State {names} with the port count - the cage says what FITS and the "
             "card says what RUNS, and a default that is right is indistinguishable "
             "from one that is not")


def lint_component_inlet(path, data, _lib_roots=None):
    """L95: a power supply says where power enters it.

    A supply that does not draw power from anything is not a thing, and the
    library had 31 of them - half the PSU catalogue, exporting no power port,
    with nothing anywhere to say so. A DCIM built from those exports shows half
    a rack's supplies with no port to cable and raises nothing.

    IT IS NOT 31 OVERSIGHTS, which is why this rule takes a declaration and not
    a drawing. Most of them are DC supplies whose entry is a screw-terminal
    block; the library has one DC terminal component against two IEC ones, so
    the studs were drawn as elements in the skin and the connector named in
    prose - "two-stud screw-terminal block under a hinged plastic cover" and
    twenty more like it. The hardware is modelled. What is missing is a fact a
    tool can read.

    Demanding a composed part would also be wrong for the C40G's supply, whose
    AC inlet is on the end of the module at the REAR of the chassis - a face
    this model does not draw, on purpose. The port exists; the drawing cannot
    show it. `attrs.inlet` can say so where a part cannot.

    A CENSUS WARNING, of the L92/L93 kind: it fires on the day it lands and is
    meant to shrink. The baseline records the backlog so a newcomer can tell it
    from something they just broke.
    """
    if (data.get("class") or "") != "psu":
        return
    attrs = attrs_mod.flatten(data.get("attrs"))
    if attrs.get("inlet"):
        return
    # A COMPOSED INLET IS THE STRONG FORM and needs no attr. Matched on the
    # component's `class` rather than on a list of refs, so a new inlet part
    # counts the day it is written - the mirror-the-table mistake is what #254
    # is about, and this rule is downstream of it.
    for part in (data.get("parts") or []):
        if not isinstance(part, dict) or "ref" not in part:
            continue
        if contract_class(part["ref"], _lib_roots) == "inlet":
            return
    warn(path, "L95", f"{data.get('name')} is a power supply and says nothing about where "
         "power enters it. Compose an inlet part where one is drawn, or state "
         "`attrs.inlet` - c14, c20, dc-terminal, or `other` for a real connector "
         "upstream has no type for. If the CHASSIS carries the inlet, that is "
         "`none`, which is an answer. What is not an answer is silence: it reads "
         "identically to a supply nobody has looked at, and exports no power port "
         "either way")


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
    # `pocket` JOINS THE LIST BECAUSE IT IS ONE OF THESE. It was added as a
    # relief primitive and this helper was not told, so every pocketed feature
    # reported its magnitude as `?` and L36 could not check a single borrowed
    # one - a rule silently unable to see the newest thing it governs, which is
    # the same shape of blindness the rule itself exists to catch.
    keys = [k for k in ("top", "sink", "out", "dome", "cyl", "bar", "uhandle",
                        "vent", "pocket")
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


def lint_component_body_boxes(path, data, _lib_roots=None):
    """L71: a body box reaches no further than the part says it is deep.

    `size.d` is the part's reach into the chassis, and it is what the bay
    hole, the pull distance and every fit check read. A box that runs on past
    it is a PCB the part does not admit to - the riser's first pass declared
    a 170.9 reach and a PCB starting 13.9 behind the plate and running 170.9,
    which is 184.8. The number the part states has to contain its own body.
    A box with no `confidence` is counted, once per file, as L35 counts.
    """
    body = data.get("body") or {}
    boxes = body.get("boxes") or []
    if not boxes:
        return
    d = float((data.get("size") or {}).get("d") or 0)
    unmarked = 0
    for i, b in enumerate(boxes):
        reach = float(b.get("from") or 0) + float(b["depth"])
        if reach > d + 0.05:
            err(path, "L71", f"body box {b.get('id') or i} reaches {reach:g} behind the "
                             f"face and size.d says the part is {d:g} deep")
        if reach > float(body.get("depth") or 0) + 0.05:
            err(path, "L71", f"body box {b.get('id') or i} reaches {reach:g} and "
                             f"body.depth says {body.get('depth')} - the pull distance "
                             f"is read from body.depth, so it must be the reach")
        if not b.get("confidence"):
            unmarked += 1
    if unmarked:
        warn(path, "L71", f"{unmarked} of {len(boxes)} body boxes carry no confidence")


def lint_component_sink_context(path, data, _lib_roots=None):
    """L77: a `sink` sits in a cavity, because that is what it measures from.

    A SINK IS A STEP IN A FLOOR. It measures DOWN FROM A CAVITY FLOOR, and
    relief.js collects it in exactly one place - as a feature of the recess it
    sits in. On a node with no cavity above it there is no floor to measure from,
    nothing collects it and nothing draws it, silently, for as long as the
    contract lives. `common/qsfp-pull-tab@1` declared a speed cut through its
    crossbar that was never built once; `common/lc-duplex-adapter@3` declared the
    inset moulded into its dust caps and it was never built across 490 nodes in
    ten drawings - and because it was never built, nobody noticed that it and the
    cap it belonged to disagreed about where the cap's front was (#230).

    `pocket` is the key for a recess in an otherwise solid face. It compiles to
    `data-depth`, which is the cavity relief.js already knows how to build, floor
    taken from the node's own art. Same number, same lift, and it draws.

    WHAT COUNTS AS A CAVITY ABOVE IT. A part whose own group carries `data-depth`
    is one - that is any part with a depth that is not a solid module and does not
    `mounts`, or one that says `relief.cavity` outright (a screw head's driver
    slot is the library's example, and its slots are correct sinks). Failing that,
    the node has to sit inside something in its own skin that declares a `pocket`.
    A cavity in a COMPOSED part is not an ancestor of this skin's nodes - it is a
    sibling subtree - so it cannot host one of these.
    """
    relief = data.get("relief") or {}
    feats = relief.get("features") or []
    sinks = [f for f in feats if isinstance(f, dict) and f.get("sink") is not None]
    if not sinks:
        return
    solid = (data.get("kind") == "module" or data.get("behaviour") == "mounts")
    is_cavity = bool((data.get("size") or {}).get("d")
                     and (not solid or relief.get("cavity")))
    if is_cavity:
        return
    pockets = {f["node"] for f in feats
               if isinstance(f, dict) and f.get("pocket") is not None and f.get("node")}
    for f in sinks:
        node = f.get("node")
        if node and pockets and _node_under(path, node, pockets):
            continue
        err(path, "L77", f"{node} declares sink {f['sink']:g} and nothing above it is a "
                         "cavity, so no floor exists for it to measure from and relief.js "
                         "collects it nowhere - the recess is declared and never built. "
                         "Use `pocket` for a recess in an otherwise solid face")


def _node_under(path, node, hosts):
    """Is `node` inside one of `hosts` in EVERY skin that draws it?

    Read from the skin because nesting is a fact about the drawing, not about the
    contract - the relief block is a flat list and says nothing about what
    contains what.

    EVERY SKIN, not any. The relief block is shared across all of them, so a node
    that sits inside the pocket in one skin and beside it in another has a floor
    under it on one drawing and nothing on the other - and the drawing without it
    is the defect this rule exists to name. `any` would let one good skin excuse
    the rest. A part whose skins do not draw the node at all is a different
    defect and _skin_checks owns that one, so it is not answered here.
    """
    drawn = 0
    for skin in sorted(Path(path).parent.glob("skins/*.svg")):
        try:
            root = ET.parse(skin).getroot()
        except (ET.ParseError, OSError):
            continue
        parent = {c: p for p in root.iter() for c in p}
        target = next((e for e in root.iter() if e.get("id") == node), None)
        if target is None:
            continue
        drawn += 1
        while target is not None:
            target = parent.get(target)
            if target is not None and target.get("id") in hosts:
                break
        else:
            return False
    return drawn > 0


def _optical_load_ref(lib_roots):
    """A `load_ref` for optical.capacities that reads from the library roots."""
    def load(ref):
        return _contract(ref, lib_roots) or {}
    return load


def lint_component_optical_faces(path, data):
    """L84: a face-qualified endpoint names a face this part declares.

    `rear:mtp.1` on a contract with no `faces.rear` resolves to nothing, and L78
    would report it as an unknown part - true, but it sends the reader hunting
    through `parts:` for an id that was never going to be there. The error is one
    level up, and saying so is the difference between a five-minute fix and an
    hour.

    WHAT THE PART DECLARES IS ASKED THROUGH `face_ref`, not read off
    `faces:` directly. A part naming its plan the legacy way has no `plan` key
    under `faces:` at all, so a literal read would report `plan:pcb.1` on one of
    the eleven risers as a face it does not have - the same blind spot L83 had
    until it was routed through the accessor, in the same release.
    """
    if not isinstance(data, dict):
        return
    have = {d for d in DIRECTIONS if face_ref(data, d)}
    for p in ((data.get("optical") or {}).get("paths") or []):
        for ep, _ratio in optical.endpoints(p):
            try:
                face, _part, _pos = optical.split_endpoint(ep)
            except ValueError:
                continue  # L78's error to report, not this one's
            if face and face not in have:
                err(path, "L84", f"path endpoint {ep} names face {face!r}, but "
                                 "this part declares no such face")


def lint_component_optical_face_capacity(path, data, lib_roots):
    """L85: only a face that is another side of the module draws its own fibres.

    `optical.capacities` walks `faces.OPTICAL_FACES` - today just `rear` -
    because a plan face is the SAME module from above and counting a connector
    drawn there as well would make one physical port into two endpoints. That
    narrowing has to be VISIBLE. A plan face that draws a connector is either
    the front's own port a second time, or a direction the optical model has
    not been extended to; both want a human rather than a shrug, and a fibre
    silently dropped from a count is no better than one silently counted twice.
    """
    if not isinstance(data, dict):
        return
    for direction in DIRECTIONS:
        if direction in OPTICAL_FACES:
            continue
        ref = face_ref(data, direction)
        if not ref:
            continue
        cp = resolve_component(ref, lib_roots)
        if not cp:
            continue                      # L83's error to report, not this one's
        inner = load_yaml(cp) or {}
        drawn = sorted(
            str(pt["id"]) for pt in (inner.get("parts") or [])
            if isinstance(pt, dict) and pt.get("id")
            and ((_contract(pt.get("ref"), lib_roots) or {}).get("optical") or {}
                 ).get("positions"))
        if drawn:
            err(path, "L85",
                f"{direction} face {ref} draws fibre-carrying parts "
                f"({', '.join(drawn)}), but a {direction} face is this module "
                "seen from another angle rather than another side of it, so "
                "its positions are not counted. Move the connector onto the "
                "face that really carries it, or extend `faces.OPTICAL_FACES` "
                "if this direction genuinely is another side")


def lint_component_optical_polish(path, data):
    """L86: a module states the polish where the port type depends on it.

    Section C's enum has `lc-upc` and `lc-apc` and no bare `lc`, so a cassette
    composing LC adapters cannot be projected at all without this. It is asked
    for ONLY where it changes the answer: `mpo`, `st`, `mdc` and `splice` have
    one form each, and `fc` and `lsh` appear only as APC, so demanding a polish
    on those would be a field with one legal value.

    A polish is a CLAIM and belongs in provenance like any other. FS names it on
    19 of its 81 catalogue rows and leaves it unstated on the rest, so the note
    matters: `upc` by convention and `upc` because the vendor said so are
    different facts, and only one of them survives a correction.
    """
    if not isinstance(data, dict):
        return
    opt = data.get("optical") or {}
    if not (opt.get("paths") or []):
        return
    if opt.get("polish"):
        return
    for part in (data.get("parts") or []):
        if not isinstance(part, dict):
            continue
        fam = optical_ports.family_of(part.get("ref") or "")
        if fam in optical_ports.POLISHED:
            err(path, "L86",
                f"composes {part.get('ref')}, whose port type is spelled "
                f"{fam}-upc or {fam}-apc, but states no `optical.polish` - so "
                "there is no type to export. Add it, and say in provenance "
                "whether the vendor named it or it is the convention default")
            return


def lint_component_optical_rear_kind(path, data):
    """L87: `optical.rear-kind` describes a rear face, so there must be one.

    The key says what the back of the module IS when it is not a connector. A
    contract that claims a splice rear and declares no rear face is describing a
    drawing that does not exist, and the projection - which is gated on a rear
    face - would ignore the claim entirely and export nothing, silently.
    """
    if not isinstance(data, dict):
        return
    opt = data.get("optical") or {}
    if not opt.get("rear-kind"):
        return
    if not face_ref(data, "rear"):
        err(path, "L87", f"declares optical.rear-kind {opt['rear-kind']!r} but no "
                         "rear face, so there is nothing for it to describe and "
                         "the projection would ignore it")


def lint_component_optical_front_order(path, data):
    """L88: a fibre face with more than one row states its own numbering.

    `_front_parts` (spec/tools/portrayal/optical_ports.py) derives the DCIM
    front-port numbering from `at.x` alone, and that derivation is safe only
    for a single row of connectors - the position on the face IS the vendor's
    own numbering there, nothing to state. A second row makes it a different
    question: whether the vendor numbers row then row or column then column,
    and which row comes first, is a fact about the SILKSCREEN, and `at.x`/
    `at.y` cannot answer it - the geometry-only derivation would quietly
    guess one, which is exactly what shipped wrong before this rule existed
    (fs/fhd-2mtp12-lc-os2-a@4's own provenance.parts records both retracted
    guesses). So a module whose fibre-bearing parts sit at more than one
    distinct `at.y` states `optical.front-order` explicitly instead of
    leaving it to be derived.
    """
    if not isinstance(data, dict):
        return
    opt = data.get("optical") or {}
    if not (opt.get("paths") or []):
        return
    if opt.get("front-order"):
        return
    ys = set()
    for part in (data.get("parts") or []):
        if not isinstance(part, dict):
            continue
        if optical_ports.family_of(part.get("ref") or "") is None:
            continue
        at = part.get("at") or [0, 0]
        try:
            ys.add(round(float(at[1]), 4))
        except (TypeError, ValueError, IndexError):
            continue
    if len(ys) > 1:
        err(path, "L88",
            f"composes fibre parts at {len(ys)} distinct at.y values but "
            "states no `optical.front-order` - a multi-row face is exactly "
            "the case `at.x` cannot number (see optical_ports._front_parts). "
            "List the fibre part ids in the vendor's own printed order")


def lint_component_optical_endpoints(path, data, lib_roots):
    """L78: an optical endpoint names a composed connector and a position it has.

    `mtp-1.13` on an MPO-12 is not a near miss, it is a fibre that does not
    exist - and without this rule it is also silent, because nothing downstream
    looks up a position it was never told about. The capacity comes from the
    CONNECTOR's own contract, so this also catches an endpoint naming a part
    that is not a connector at all: a path into a status lamp.
    """
    opt = data.get("optical") or {}
    paths = opt.get("paths") or []
    if not paths:
        return
    caps = optical.capacities(data, _optical_load_ref(lib_roots))
    for p in paths:
        for ep, _ratio in optical.endpoints(p):
            try:
                face, part, pos = optical.split_endpoint(ep)
            except ValueError:
                err(path, "L78", f"{ep!r} is not an optical endpoint - they are "
                                 "`<part-id>.<n>` with n from 1")
                continue
            key = optical.part_key(face, part)
            if key not in caps:
                err(path, "L78", f"{ep} names {key!r}, which this part either "
                                 "does not compose or which declares no "
                                 "`optical.positions` - only a connector can "
                                 "carry a fibre")
            elif pos > caps[key]:
                err(path, "L78", f"{ep} asks for position {pos} and {key} "
                                 f"presents {caps[key]}")


def lint_component_optical_conflicts(path, data, _lib_roots=None):
    """L79: no position is claimed twice, and a split's ratios sum to 100.

    A DESTINATION IS EXCLUSIVE, A SOURCE IS NOT. Two strands landing in one bore
    is a contradiction - a bore takes one ferrule. One source reaching several
    destinations is a SPLIT, which is exactly what a tap and a coupler are, so
    counting sources as conflicts would reject the parts this vocabulary exists
    for. The check is therefore on destinations only.

    A COMBINE - two sources landing on one destination - is not expressible
    today. The vocabulary has no syntax for it, so two paths whose destinations
    collide are always an error here, with no declared-combine escape hatch the
    way a declared split has one. `ppm-ad1-1510`'s combine direction (plan 6)
    will need one and none exists yet; see this rule's TODO and the design
    doc's open questions.

    Ratios are checked here rather than in the schema because the schema can say
    a ratio is a number and cannot say two of them add up. 70/40 validates and
    is wrong. THE RATIO LIST IS ALSO THE ONLY FORM THIS CHECK CAN SEE: a split
    written as two plain paths - `{from: common.1, to: split.1}` and
    `{from: common.1, to: split.2}` - carries no ratios at all, so writing a
    genuine split that way hides it from the ratio check entirely. A source
    is therefore allowed to be a `from` in at most one path; a part that
    splits must say so with the ratio list, which is the one form this rule
    can actually verify.
    """
    paths = (data.get("optical") or {}).get("paths") or []
    seen = {}
    sources = {}
    for i, p in enumerate(paths):
        eps = optical.endpoints(p)
        for ep, _r in eps[1:]:
            if ep in seen:
                err(path, "L79", f"{ep} is the destination of two paths "
                                 f"({seen[ep]} and {i}) - a fibre position "
                                 "takes one ferrule")
            seen[ep] = i
        src = p.get("from")
        if src in sources:
            err(path, "L79", f"{src} is the source of two paths "
                             f"({sources[src]} and {i}) - splitting a source "
                             "across two paths hides its ratios from this "
                             "check, so a split is written as ONE path with "
                             "a ratio list, not two plain paths")
        sources[src] = i
        ratios = [r for _e, r in eps[1:] if r is not None]
        if ratios:
            total = round(sum(ratios), 6)
            if total != 100:
                err(path, "L79", f"path {i} from {p['from']} splits into ratios "
                                 f"summing to {total:g}, not 100")


# THE THREE POLARITIES FS BUILDS, as the fibre each front port takes, port by
# port, within one rear connector of n positions. Port p is the vendor's printed
# number (odd = the lower bore of a stacked duplex). Read off FS's own cassette
# diagrams (the FHD universal-polarity blog's Method A and Method B figures, and
# the FHD MTP-12/24 Cassettes Datasheet's Inner Sequence tables): Type A is
# straight through; AF swaps each duplex pair - port 1 takes fibre 2 and port 2
# takes fibre 1; universal pairs fibre j with fibre n+1-j, so port 1 takes fibre
# 1 and port 2 fibre 12.
#
# A 24-FIBRE AF IS NOT THE PAIR SWAP ALONE. The datasheet (p. 6, MTP-24 Type AF)
# also exchanges the two twelve-fibre rows: port 1 takes fibre 14, port 13
# takes fibre 2. Its MTP-12 AF (p. 4) is the pair swap alone.
def _af_pattern(n):
    swapped = [p + 1 if p % 2 else p - 1 for p in range(1, n + 1)]
    if n == 24:
        return [f + 12 if f <= 12 else f - 12 for f in swapped]
    return swapped


POLARITY_PATTERNS = {
    "a": lambda n: list(range(1, n + 1)),
    "af": _af_pattern,
    "universal": lambda n: [(p + 1) // 2 if p % 2 else n + 1 - p // 2
                            for p in range(1, n + 1)],
}


def lint_component_optical_polarity(path, data, lib_roots):
    """L109: a declared polarity is what the paths wire.

    `optical.polarity` was a name the schema accepted and nothing checked - the
    design note always said "checked against the paths, never a substitute for
    them", and until this rule nobody did the checking.

    IT READS PORT NUMBERS, NOT BORES. A port's number is its adapter's place in
    the front order plus the position within the adapter (optical_ports
    `front_label`), so this rule trusts that position 1 IS the port the vendor
    prints first. Whether it is - which bore of a stacked adapter is position 1
    - is the adapter's contract to get right, and a test pins it for the FS
    stacked adapters (the lower bore, FS's odd port). The two FHD adapters had
    it the other way round until this rule's first use exposed it.

    Only rear connectors reached from the front are compared, one at a time,
    port order against the pattern for that connector's width. A polarity this
    table does not know is not judged - it is still a claim, just not one this
    rule can test.
    """
    opt = data.get("optical") or {}
    pol = str(opt.get("polarity") or "").lower()
    pattern = POLARITY_PATTERNS.get(pol)
    if pattern is None or not opt.get("paths"):
        return

    def load_ref(ref):
        f = resolve_component(ref, lib_roots)
        return load_yaml(f) if f else None

    by_rear = {}
    for p in opt["paths"]:
        eps = [p.get("from"), p.get("to")]
        front = next((e for e in eps if e and ":" not in e), None)
        rear = next((e for e in eps if e and ":" in e), None)
        if not front or not rear:
            continue
        label = optical_ports.front_label(data, front, load_ref)
        if label is None:
            continue
        _face, rpart, rpos = optical.split_endpoint(rear)
        by_rear.setdefault(rpart, []).append((int(label), int(rpos)))
    for rpart, pairs in sorted(by_rear.items()):
        pairs.sort()
        ports = [pt for pt, _ in pairs]
        base = ports[0] - 1
        n = len(pairs)
        if ports != list(range(base + 1, base + n + 1)):
            continue            # not one contiguous run of ports - not a cassette pattern
        got = [f for _, f in pairs]
        want = pattern(n)
        if got != want:
            first = next(i for i in range(n) if got[i] != want[i])
            err(path, "L109", f"declares polarity {pol!r}, but port {base + first + 1} takes "
                              f"{rpart} fibre {got[first]} where {pol!r} puts fibre "
                              f"{want[first]} (ports {base + 1}-{base + n} wire "
                              f"{got}); the paths are the evidence - fix them or the claim")


# L112 EXEMPTIONS, BY NAME AND WITH A REASON. A part leaves this table when the
# source that places its fibres arrives; the census test fails if one is added
# silently or names a part that no longer exists.
POSITION_EXEMPT = {
    "common/mdc-adapter": (
        "which bore of which duplex port is position 1-4 is not sourced, and a "
        "guessed order is a wrong address that looks like a right one"),
    "common/fibre-splice": (
        "a placeholder that draws no fibres; markers on it would be addresses "
        "without a place"),
}


def _component_key(path):
    parts = Path(path).parts
    return "/".join(parts[-4:-2])


def lint_component_optical_position_nodes(path, data, lib_roots):
    """L112: every fibre position a connector declares is a node you can point at.

    A fibre endpoint `X.n` in `optical.paths` is drawn at path `X/n`, so the
    explorer and every consumer can turn one into the other without a table.
    That holds only if a connector with `optical.positions: N` draws nodes
    `1`..`N`: a composed bore, or a contracted element of class `fibre`.

    It also refuses a cassette whose rear face composes an id its front also
    uses. Both would be drawn at the same path on two faces as two different
    connectors, which is the one thing a path must never be.
    """
    own = {str(p.get("id")) for p in data.get("parts") or [] if p.get("id") is not None}
    rear = (data.get("faces") or {}).get("rear")
    rear_ref = rear.get("ref") if isinstance(rear, dict) else rear
    if rear_ref:
        f = resolve_component(rear_ref, lib_roots)
        rd = load_yaml(f) if f else None
        clash = sorted(own & {str(p.get("id")) for p in (rd or {}).get("parts") or []})
        if clash:
            err(path, "L112", f"rear face {rear_ref} composes {clash}, which the front also "
                              "composes; one path would name two connectors - rename one side")
    if data.get("class") != "port":
        return
    n = (data.get("optical") or {}).get("positions")
    if not n or _component_key(path) in POSITION_EXEMPT:
        return
    have = own | {str(k) for k, v in (data.get("elements") or {}).items()
                  if isinstance(v, dict) and v.get("class") == "fibre"}
    want = {str(i) for i in range(1, int(n) + 1)}
    missing = sorted((int(i) for i in want - have))
    if missing:
        err(path, "L112", f"declares optical.positions {n} but draws no node for position(s) "
                          f"{missing}; compose a bore with that id or declare an element of "
                          "class fibre, so fibre X.n has a path X/n")
    extra = sorted(int(i) for i in have if i.isdigit() and int(i) > int(n))
    if extra:
        err(path, "L112", f"draws position node(s) {extra} beyond optical.positions {n}")


def lint_component_optical_coverage(path, data, lib_roots):
    """L80: every position is reached by a path or declared unused, with a reason.

    smartoptics/ppm-ocu-97-3@2 carries this in provenance today:

        THE SECOND BORE IS DEAD. It is captioned NA and terminates nothing.

    True, and unverifiable. A four-bore faceplate on a three-port coupler leaves
    one position with nothing behind it, and the difference between "nothing
    behind it" and "somebody forgot a path" is the whole question. Declaring it
    turns a sentence into a claim.

    IT BITES BOTH WAYS. An entry for a position a path DOES reach is also an
    error - otherwise `unused` becomes a way to silence the rule rather than a
    statement about the hardware, and the first person under time pressure finds
    that out.

    IT ONLY ASKS THE QUESTION OF A PART THAT OPTED IN. A component composing
    fibre connectors but declaring no `optical.paths` at all returns here
    unchecked - deliberately. This rule can only fire once a component has
    started describing its optical model; running it against every component
    that merely composes a connector would error on every part in the library
    that carries an LC adapter and no optical model, which today is all of
    them. That would force the rule to land as a warning, and a warning that
    fires everywhere gets ignored everywhere. The cost is real: a part that
    declares connectors and no paths is not checked by L80, and nothing yet
    catches that gap.

    AN `unused` KEY IS ALSO CHECKED AGAINST SOMETHING. The schema's
    `propertyNames` can only shape-check the string - `<part-id>.<n>` - and the
    loop above walks real positions only, so `unused: {ghost.7: "..."}` or
    `common.9` on a two-bore adapter validated and was silently ignored: a
    claim about hardware that does not exist, checked by nothing. Every key is
    now required to name a position on a connector this component actually
    composes.
    """
    opt = data.get("optical") or {}
    if not (opt.get("paths") or []):
        return
    caps = optical.capacities(data, _optical_load_ref(lib_roots))
    hit = optical.reached(data)
    unused = opt.get("unused") or {}
    for part, n in sorted(caps.items()):
        for pos in range(1, n + 1):
            ep = f"{part}.{pos}"
            if ep in hit and ep in unused:
                err(path, "L80", f"{ep} is declared unused and a path reaches "
                                 "it - one of the two is wrong")
            elif ep not in hit and ep not in unused:
                err(path, "L80", f"{ep} is a fibre position no path reaches and "
                                 "nothing declares. Route it, or add an "
                                 "`optical.unused` entry saying what terminates "
                                 "there")
    for ep in sorted(unused):
        try:
            face, part, pos = optical.split_endpoint(ep)
        except ValueError:
            err(path, "L80", f"{ep!r} is not an optical endpoint - `unused` "
                             "keys are `<part-id>.<n>` with n from 1")
            continue
        key = optical.part_key(face, part)
        if key not in caps or pos > caps[key]:
            err(path, "L80", f"{ep} is declared unused but names no position "
                             "this component composes - `unused` claims a "
                             "position exists and terminates nothing, so it "
                             "is checked against real hardware like any other "
                             "endpoint")


# 90, 270 and their negatives turn a row into a column; 0 and 180 do not, so a
# 180-rotated pair still runs along x and must not be read down y.
SWAPS_AXES = {90, -90, 270, -270}


def lint_component_composed_pitch(path, data, lib_roots):
    """L81: a composed pitch respects the standard the composed part conforms to.

    THE LIBRARY HELD BOTH NUMBERS AND COMPARED NEITHER. standards.yaml carried
    `lc-duplex-receptacle.pitch: 6.25` at verified confidence, from IEC 61754-20
    / TIA-604-10 FOCIS 10, while common/lc-duplex-adapter@3 composed its two
    bores 6.60 apart from a vendor stencil. 5.6% apart, both written down, for as
    long as both existed.

    A component composing SEVERAL copies of one part that `conforms:` to a
    standard carrying a `pitch` is making a claim about that pitch whether it
    means to or not. This checks it. Only the evenly-spaced case is checked -
    parts at irregular spacing are a different drawing, not a pitch.

    THE FIRST VERSION OF THIS RULE TREATED EVERY PITCH AS A TARGET, AND THAT WAS
    WRONG. `standards.yaml` states outright, in the notes of five of its six
    `pitch` entries (`xfp`, `cfp`, `cfp2`, `cxp`, `qsfp-ganged`), that the figure
    is a FLOOR - a minimum spacing a device may sit wider than - not a fixed
    target. Only `lc-duplex-receptacle` is a fixed interface pitch. An equality
    check against a floor flags every device that legitimately spaces its ports
    out for thermal or mechanical reasons, and the only fix on offer was to
    write a `provenance.pitch-note` explaining that the "violation" was fine -
    which is how 18 contracts ended up carrying a note working around a defect
    in this rule rather than recording a fact about hardware. `pitch-kind` on
    the standard (`target` or `floor`; absent means `target`, the stricter
    reading) tells this rule which check applies:

    - `target`: the composed pitch must equal the standard's, as before.
    - `floor`: the composed pitch must be AT LEAST the standard's - narrower is
      an error, wider is explicitly allowed and raises nothing.

    The escape hatch is deliberate and narrow: a part that really does violate
    its standard's pitch - a target it misses, or a floor it undercuts - says so
    in `provenance.pitch-note`, and the rule stands down. Silence is not an
    escape hatch. A note is not owed to a floor a part merely exceeds; that is
    compliance, not an exception.
    """
    parts = [p for p in (data.get("parts") or []) if isinstance(p, dict)]
    if len(parts) < 2:
        return
    if (data.get("provenance") or {}).get("pitch-note"):
        return
    by_ref = {}
    for p in parts:
        if p.get("ref") and p.get("at"):
            by_ref.setdefault(p["ref"], []).append(
                (float(p["at"][0]), float(p["at"][1]),
                 p.get("rotate") in SWAPS_AXES))
    for ref, pts in sorted(by_ref.items()):
        if len(pts) < 2:
            continue
        sub = _contract(ref, lib_roots) or {}
        key = sub.get("conforms")
        if not key:
            continue
        std = STANDARDS.get(key) or {}
        want = std.get("pitch")
        if not want:
            continue
        rotated = all(r for _x, _y, r in pts)
        # A cage rotated 90 degrees runs its array down `at`'s y, not its x - a
        # whole rotated column shares one x, and reading x alone would see
        # every gap as zero and call that a matched pitch.
        #
        # SHARING AN X IS NOT ENOUGH TO MEAN ROTATED, though, and that is what
        # this used to test. A duplex shell with its two ports STACKED shares one
        # x too, and it is not the same part turned: a rotated part keeps its
        # interface pitch, where a stacked pair is genuinely further apart. The
        # arithmetic settles it - a std/lc-bore@3 is 6.3 tall, so two of them at
        # lc-duplex-receptacle's 6.25 would overlap, which means 6.25 never
        # described a stacked pair in the first place. Reading the y of one would
        # compare a vertical spacing against a horizontal standard and call the
        # difference a violation.
        #
        # So fall back to y only when the placements SAY they are rotated. A
        # group that shares one x but is not rotated is skipped below instead -
        # see why at the `continue`.
        if len({x for x, _y, _r in pts}) == 1:
            if len({r for _x, _y, r in pts}) > 1:
                # NEITHER READING IS SAFE. A rotated column and a stacked pair
                # both share an x, and `rotate` is the only thing separating
                # them - so when the placements disagree, reading y compares a
                # stack against a horizontal standard and reading x compares
                # zero. Skipping in silence is not free either: it drops a
                # check that was being made before the stacked case existed,
                # and the likeliest way to land here is forgetting `rotate` on
                # one member of a rotated column.
                err(path, "L81",
                    f"composes {len(pts)} x {ref} sharing one x, but some are "
                    "rotated onto the other axis and some are not. A rotated "
                    "column and a stacked pair share an x for different "
                    "reasons, so until the placements agree there is no pitch "
                    "here to read")
                continue
            if not rotated:
                # A stacked pair shares an x by construction, not by chance - it
                # is not a rotated column, so there is no x-based pitch to read
                # here either. Falling through to the x path would measure the
                # gap between two identical x values (zero) and report THAT as
                # missing this standard's pitch, which is a fabricated number,
                # not a measurement of the hardware.
                continue
            vals = sorted(y for _x, y, _r in pts)
        else:
            vals = sorted(x for x, _y, _r in pts)
        gaps = [round(vals[i] - vals[i - 1], 4) for i in range(1, len(vals))]
        if len(set(gaps)) != 1:
            continue                      # irregular spacing is not a pitch
        got = gaps[0]
        want = float(want)
        kind = std.get("pitch-kind", "target")
        if kind == "floor":
            if got < want - 0.01:
                err(path, "L81",
                    f"composes {len(pts)} x {ref} at a pitch of {got:.2f}, "
                    f"narrower than {key}'s floor of {want:.2f}. Widen them to "
                    f"at least the floor, or record `provenance.pitch-note` "
                    f"saying why this part sits tighter than it")
            # wider than a floor is compliant, not an exception - raise nothing
        else:
            if abs(got - want) > 0.01:
                err(path, "L81",
                    f"composes {len(pts)} x {ref} at a pitch of {got:.2f} and "
                    f"{key}'s target is {want:.2f}. Move them onto the "
                    f"standard, or record `provenance.pitch-note` saying why "
                    f"this part differs")


def lint_component_faces_once(path, data):
    """L82: a part names its plan drawing one way or the other, never both.

    `plan:` is sugar for `faces.plan`. A contract carrying both leaves every
    reader to pick one, and the two will agree right up until somebody edits a
    face and does not notice there is a second copy of it three lines away.
    """
    if not isinstance(data, dict):
        return
    if (data.get("plan") or {}).get("ref") and \
            ((data.get("faces") or {}).get("plan") or {}).get("ref"):
        err(path, "L82", "declares both `plan:` and `faces.plan` - they mean the "
                         "same thing, so keep one. `plan:` is the legacy spelling")


def lint_component_faces_resolve(path, data, lib_roots, name=None):
    """L83: every declared face names a real component, not itself, with no
    face of its own direction.

    A face is an ordinary part, so a typo in its ref fails silently - nothing
    draws, and the contract still lints. This used to check `rear` alone,
    because `rear` was the direction the rule was written for; `plan` got none
    of it, so `faces: {plan: {ref: t/nope@1}}` lints clean today even though
    the argument for checking it is identical. Iterating `DIRECTIONS` through
    `face_ref` closes that gap for both spellings of `plan` at once, instead of
    adding a second rear-shaped code path for it.
    """
    if not isinstance(data, dict):
        return
    for direction in DIRECTIONS:
        ref = face_ref(data, direction)
        if not ref:
            continue
        if name and ref == name:
            err(path, "L83", f"names itself as its own {direction} ({ref})")
            continue
        cp = resolve_component(ref, lib_roots)
        if not cp:
            err(path, "L83",
                f"names {direction} face {ref}, which is not in the library")
            continue
        inner = load_yaml(cp) or {}
        if face_ref(inner, direction):
            err(path, "L83",
                f"names {direction} face {ref}, which declares a {direction} "
                "of its own - a part has one of each direction, so this "
                "chain says the wrong part was drawn")


def lint_component_superseded_by(path, data, lib_roots):
    """L101: a `superseded-by` names a component major that exists, and is not
    the part itself.

    A dangling successor is worse than none: it reads as a working pointer to
    a consumer that would use it to steer someone away from a retired part, and
    fails silently right up until that consumer tries to resolve it. ERROR, not
    warning, for the same reason L83 refuses a face that does not resolve - the
    two fields are the same shape, a `ns/name@major` ref this rule can check
    exactly rather than guess at.

    A SELF-POINTER IS THE ONE THAT RESOLVES AND STILL LIES, which is why it
    is checked separately: the target is a real file - its own - so "the ref
    resolves" says nothing, and a consumer following the pointer to show the
    replacement loops. A full cycle walk (A -> B -> A) is deliberately not
    attempted: that needs two deliberate edits in two files, where this needs
    one careless copy-paste in one.
    """
    if not isinstance(data, dict):
        return
    ref = data.get("superseded-by")
    if not ref:
        return
    # A PART IS NOT ITS OWN SUCCESSOR. This resolves - the file is right
    # there - so the existing check passes it, and a consumer that follows
    # the pointer to show the replacement (the use the schema description
    # invites) never terminates. L83 refuses a face that names itself for the
    # same reason and in the same words.
    if ref == libwalk.ref_of(path):
        err(path, "L101",
            f"superseded-by: {ref}, which is this part itself - a successor "
            "has to be a different component major")
        return
    if not resolve_component(ref, lib_roots):
        err(path, "L101",
            f"superseded-by: {ref}, which is not in the library")


def lint_component_pluggable_rate(path, data, _lib_roots=None):
    """L102: a part's `rate` attr, if it states one, is a rate its `mates`
    family actually carries.

    THE CAGE SAYS WHAT FITS (`mates`); THIS SAYS WHAT RUNS. `interface`/`mates`
    already tie a plug to a receptacle (L11, L12) - a QSFP transceiver mates
    `qsfp` and seats in anything the QSFP family's cage accepts. That is
    mechanical compatibility, not the rate the module runs at, and R1 of the
    pluggables design (docs/pluggables-design.md) is that a GENERIC carries no
    rate and fits every rung of its family's ladder while a VENDOR OPTIC
    declares one. `attrs.rate` is where a vendor optic would say so.

    NOTHING IN THE LIBRARY DECLARES `rate` YET - every generic composes a cage
    and states nothing, which is correct, and no vendor wrapper has been built
    on top of one. This rule ships anyway: it is what makes R1 a fact the tree
    can be held to rather than a sentence in a design doc, and it needs to be
    in place before the first vendor optic lands with a rate outside its own
    family, not added after. Its test drives it with synthetic contracts.

    Why `rate` and not `media` or `speed`: `media` is overloaded - the two
    retired parts (`superseded-by`, L101) carry `media: sfp`/`media: qsfp`, a
    RATE, while every live generic carries `media: fiber`, a MEDIUM, and
    reading `media` as the rate would look for `fiber` on a ladder and find
    nothing. `speed` is a bitrate (`10G`, `25G`) that `GENERIC_FORBIDDEN_ATTRS`
    already reserves for vendor parts and is a different fact from the cage
    generation - an SFP-10G-LR has `speed: 10G` AND needs an `sfp-plus` cage.
    """
    if not isinstance(data, dict):
        return
    rate = attrs_mod.flatten(data.get("attrs")).get("rate")
    if not rate:
        return
    mates = data.get("mates")
    found = _family_mated_by(mates) if mates else None
    if found is None:
        err(path, "L102", f"attrs.rate: {rate!r}, but mates {mates!r} names no "
            "family in spec/schemas/pluggables.yaml - there is nothing to check "
            "the rate against")
        return
    fam_name, fam = found
    if rate not in (fam.get("rates") or []):
        err(path, "L102", f"attrs.rate: {rate!r} is not a rate of the "
            f"{fam_name!r} family that mates {mates!r} names (rates: "
            f"{fam.get('rates')}) - spec/schemas/pluggables.yaml and this part "
            f"disagree about what {mates!r} runs")


def lint_component_fields(path, data, _lib_roots=None):
    """L73: a field prints somewhere, and what prints is a field.

    A field is a promise to a form: set this and the drawing changes. It is
    kept by a `data-from` node of that name in EVERY skin, or the value goes
    nowhere on the skin that lacks it. And a `data-from` node the contract
    does not declare is a field a form cannot find - the drive carriers
    carried five of those for a year. A choice with no options is a text
    box pretending.

    A NODE PAINTED FROM AN ATTR KEEPS THE PROMISE THE SAME WAY. `data-fill-from`
    sets a `fill` where `data-from` sets text, and the rule is about whether the
    drawing is wired to the field at all, not about which attribute carries it -
    so both count, in both directions. Reading only one of them would have
    called the RJ45 family's `finish` an unkept promise and, worse, let a skin
    paint itself from an attr no form is ever offered. `data-stroke-from` joined
    them in #177, for the same reason and with the same standing: a coloured part
    is a fill AND an outline, and a mechanism that could only say half of it
    would have produced blue handles wearing dark red edges. `data-stroke-derive`
    (#482), an outline drawn as a shade of a colour field, is read the same way:
    a skin deriving from a key no contract declares is deriving from nothing.
    """
    fields = data.get("fields") or {}
    skins_dir = path.parent / "skins"
    seen = {}
    for skin in (data.get("skins") or ["default"]):
        sp = skins_dir / f"{skin}.svg"
        if not sp.exists():
            continue
        text = sp.read_text(errors="replace")
        keys = set(re.findall(r'data-(?:(?:fill-|stroke-)?from|stroke-derive)="([^"]+)"', text))
        seen[skin] = keys
        for k in fields:
            if k not in keys:
                err(path, "L73", f"field {k} has no data-from, data-fill-from or "
                                 f"data-stroke-from node in skin {skin}")
    undeclared = set().union(*seen.values()) - set(fields) if seen else set()
    if undeclared:
        warn(path, "L73", f"skin fills {', '.join(sorted(undeclared))} from attrs but the "
                          f"contract declares no such field - a form cannot offer them")
    for k, f in fields.items():
        if (f or {}).get("type") == "choice" and not (f or {}).get("options"):
            err(path, "L73", f"field {k} is a choice with no options")
        if (f or {}).get("options") and f.get("default") is not None and f["default"] not in f["options"]:
            err(path, "L73", f"field {k}: default {f['default']!r} is not one of its options")


def lint_component_lamp_colour(path, data, _lib_roots=None):
    """L74: a lamp that declares states has to be painted from the variable.

    A state is a CSS class that sets `--led-color`; a node is lit by reading it
    - `fill="var(--led-color, <off>)"`, or the stroke for a glyph. A skin node
    with a literal colour ignores every state its contract declares, in 2D
    and in 3D alike: the R740xd's control panel declared amber faults on five
    glyphs and two bars and none of them could ever turn amber.
    """
    skins_dir = path.parent / "skins"
    # a button with an `on` state is lit the same way; a display is lit per
    # segment by opacity and is not
    lit = {k for k, e in (data.get("elements") or {}).items()
           if isinstance(e, dict) and e.get("states") and e.get("class") in ("led", "button")}
    if not lit:
        return
    for skin in (data.get("skins") or ["default"]):
        sp = skins_dir / f"{skin}.svg"
        if not sp.exists():
            continue
        try:
            root = ET.parse(sp).getroot()
        except ET.ParseError:
            continue
        for node in root.iter():
            k = node.get("id")
            if k not in lit:
                continue
            sub = ET.tostring(node, encoding="unicode")
            if "var(--led-color" not in sub:
                err(path, "L74", f"{skin}: lamp {k} declares states but its node paints a "
                                 f"literal colour - no state can light it; use "
                                 f"var(--led-color, <off colour>) on its fill or stroke")


def lint_component_slots(path, data, _lib_roots=None):
    """L75: a slot's structured facts agree with its prose, and a slot cannot
    carry more lanes than its connector.

    The prose attr is what a reader sees and the `slot:` block is what a card
    feature reads; two statements of one fact drift unless something holds
    them together. And a connector is the widest link it can carry: x16 lanes
    on an x8 connector is a typo, not a slot.
    """
    width = {"x1": 1, "x4": 4, "x8": 8, "x16": 16}
    prose_re = re.compile(r"^x(\d+), (full height|low profile), (full length|half length), processor (\d)")
    attrs = data.get("attrs") or {}
    for bid, b in (data.get("bays") or {}).items():
        sl = (b or {}).get("slot") if isinstance(b, dict) else None
        if not sl:
            continue
        if sl["lanes"] > width[sl["connector"]]:
            err(path, "L75", f"bay {bid}: {sl['lanes']} lanes on an {sl['connector']} connector")
        prose = attrs.get(bid)
        if isinstance(prose, str):
            m = prose_re.match(prose)
            if m:
                want = (int(m.group(1)), m.group(2).split()[0], m.group(3).split()[0], int(m.group(4)))
                have = (sl["lanes"], sl["height"], sl["length"], sl.get("processor"))
                if want != have:
                    err(path, "L75", f"bay {bid}: slot says lanes {have[0]}, {have[1]} height, "
                                     f"{have[2]} length, processor {have[3]} but the attr reads {prose!r}")


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
        facet = facets.facet_of(data, q["on"]) if q.get("on") else None
        x0, y0, x1, y1 = facets.projected_box(q["at"], w, h, q.get("rotate"), facet)
        boxes.append((q.get("id", "?"), x0, y0, x1, y1))

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


def lint_component_facets(path, data, lib_roots):
    """L117: a tilted part stands on a facet that exists and holds it.

    docs/superpowers/specs/2026-09-24-tilted-facets-design.md. The facet's rectangle is
    its front-view footprint; a part on it is measured by its PROJECTED box (true size
    foreshortened by cos(deg)), which is what occupies the face.
    """
    feats = {f.get("node"): f for f in (data.get("relief") or {}).get("features") or []}
    elements = data.get("elements") or {}
    for node, f in feats.items():
        if f.get("facet"):
            for k in ("out", "profile", "profile-y"):
                if k in f:
                    err(path, "L117", f"feature {node!r} declares a `facet` and also `{k}` - "
                        "the renderer derives the slope from the facet, and two sources for "
                        "one slope drift apart")
            if node not in elements or not elements[node].get("size"):
                err(path, "L117", f"facet node {node!r} is not a declared element with a "
                    "size - the renderer needs its front-view rectangle to derive the wedge")
    for q in data.get("parts") or []:
        on = q.get("on")
        if not on:
            continue
        facet = facets.facet_of(data, on)
        if not facet:
            err(path, "L117", f"part {q.get('id')!r} is `on: {on}`, which is not a relief "
                "feature on this contract that declares a `facet`")
            continue
        el = elements.get(on) or {}
        size = _instance_size(q.get("ref"), lib_roots)
        if not el.get("size") or not size or not q.get("at"):
            continue
        x0, y0, x1, y1 = facets.projected_box(q["at"], size[0], size[1], q.get("rotate"), facet)
        ex, ey = el["at"]
        ew, eh = el["size"]
        tol = 0.5
        if x0 < ex - tol or y0 < ey - tol or x1 > ex + ew + tol or y1 > ey + eh + tol:
            err(path, "L117", f"part {q.get('id')!r} on facet {on!r} projects to "
                f"({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f}), outside the facet's "
                f"({ex},{ey})-({ex + ew},{ey + eh}) by more than {tol} mm")


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
        found = libwalk.contract_path(part["ref"], lib_roots)
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
        # A contract with no `size` used to raise KeyError here and take the
        # WHOLE RUN down - 570-odd files linted, one omission, no output at all
        # and a traceback instead of the finding that names the file. A linter
        # that cannot survive the mistake it exists to catch is worse than one
        # that misses it, because the author is left with no report to read.
        size = data.get("size")
        if not size:
            err(sp, "L4", "contract states no size, so nothing can check the "
                          "skin's viewBox against it")
            return data
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
                             "explicit position (this pass reads one view's "
                             "declared placements and does not walk a mate-to "
                             "chain the way render.py's fixed point does)")
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
    want, _, _ = presented_interface(hc, _res)
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

    A DEVICE-LEVEL KEY CAN NAME A CHAINED OCCUPANT TOO - `port-4-occupant` is
    the plug seated on the optic `port-4` seats, and render.py's occupants
    expansion runs to a fixed point to draw exactly that. Once `host_id` is
    not a placement, `chained_occupant_ref` walks this configuration's own
    device-level occupants for the one that produced it - the same resolver
    `nested_key_host` uses for a cage on a seated card, shared rather than
    reimplemented so the two directions cannot disagree about what a chained
    key names.
    """
    hosts = {}
    for vname, view in (data.get("views") or {}).items():
        for q in view_parts(view or {})["placements"]:
            hosts.setdefault(q.get("id"), (vname, q))

    def terminal(h):
        q = hosts.get(h)
        return q[1]["ref"] if q else None

    for cname, cfg in (data.get("configurations") or {}).items():
        cfg = cfg or {}
        occupants = cfg.get("occupants") or {}
        # Candidates a device-level chain can resolve against: the OTHER
        # device-level keys of this same configuration - a nested ("/") key
        # belongs to a module and is resolved by nested_key_host instead.
        # A key whose value is "" empties its slot (P4) and produces nothing
        # a chain could name.
        siblings = {k: (v if isinstance(v, dict) else {"ref": v})
                    for k, v in occupants.items() if "/" not in k and v != ""}
        for host_id, spec in occupants.items():
            ref = spec if isinstance(spec, str) else (spec or {}).get("ref")
            where = f"configurations/{cname}/occupants/{host_id}"
            if "/" in host_id:
                # A CAGE ON A SEATED CARD (#484, R2), keyed by the card's
                # module-less path, or a slot at any depth (B3): walked down
                # THIS configuration's bays, then the parts of what they seat,
                # or from a placement down its parts, by
                # manifest.nested_key_host - the walk the build's
                # slot_key_prefix / occupants_under answer from the other end -
                # and a chained key to the occupant it names.
                def _res(r):
                    q = resolve_component(r, lib_roots)
                    return load_yaml(q) if q else None
                try:
                    host_ref, _mref, _mpath = nested_key_host(host_id, data, cfg, _res)
                except ValueError as e:
                    err(path, "L12", f"configurations/{cname}/{e}")
                    continue
                if ref:
                    _mate_check(path, where, ref, host_ref, lib_roots)
                continue
            if host_id in hosts:
                vname, host = hosts[host_id]
                if not host.get("at"):
                    err(path, "L12", f"{where}: host has no explicit position")
                    continue
                if ref:
                    _mate_check(path, where, ref, host["ref"], lib_roots)
                continue
            try:
                host_ref = chained_occupant_ref(host_id, siblings, terminal)
            except KeyError:
                err(path, "L12", f"{where}: names no placement in any view of "
                                 "this device, and no occupant of this "
                                 "configuration seats it either")
                continue
            except ValueError as e:
                err(path, "L12", f"{where}: occupant chain cycles back to {e}")
                continue
            if ref:
                _mate_check(path, where, ref, host_ref, lib_roots)


def lint_device_overlap(path, view_name, view, lib_roots):
    """L13: two placed components must not occupy the same faceplate area.

    Overlap is almost always a sizing mistake rather than a drawing choice: a
    part measured off one device dropped into a tighter gap on another. It is
    invisible in the flat SVG (the later node just paints over the earlier one)
    but obvious in 3D, where an LED dome hangs over the lip of a port cavity.

    Occupants are exempt - a transceiver placed with mate-to is *supposed* to
    sit inside its host's aperture.

    So is a part that FRAMES another: a rear drive cage's face is two rails and
    two tabs, its box contains four drive bays, and its ink touches none of
    them. `frames:` names what its openings clear. This is not the same claim as
    `mounts` - a cage surrounds its drives and draws BEFORE them.

    So is a SURFACE-MOUNTED part, which is supposed to lie over what is behind
    it: a PowerEdge's rear handle is bolted to the outside of the panel and its
    rail crosses two riser slots and a NIC card. `behaviour: mounts` is the
    declaration, and it is the same key render.py reads to draw such a part in
    front of the openings - so a part drawn on top is exactly a part allowed to
    be on top. Two MOUNTED parts overlapping each other is still reported.

    So are two parts that are never both present. `only-in` scopes a piece of
    metal to a set of configurations, and a C40G ordered for AC has one bolted
    panel exactly where a DC chassis has its two power-entry openings. Comparing
    them is comparing two different chassis: the AC panel and the DC bays overlap
    by their whole area and never coexist in any rendered view. Without this the
    rule rejects the correct model, which is the more dangerous direction - an
    author reading a hard error concludes the arrangement is wrong.

    And so are two parts at DIFFERENT HEIGHTS, when one says so. Every exemption
    above is a faceplate exemption: it lets two things share a plan because one
    of them is not really in the plan. A view with its lid off is not a
    faceplate. The R740xd's top, cover pulled, is a SECTION through four
    heights - the system board at 40.63, the air shroud at 84.88, the mid tray
    at 85.63, the fan cage at 86.34, against an 86.8 panel - and everything in
    it overlaps in plan precisely because it is stacked. `under:` on a
    placement names the parts that lie over it, and a pair one of which has
    declared itself under the other is not compared.
    THE DECLARATION IS CHECKED, NOT TRUSTED. A part can only be under something
    if there is somewhere for it to be: it must be a well (`size.d` on a part
    that is neither a module nor mounted - the aperture rule), or the part over
    it must be `behaviour: mounts`, a lid. A flat part claiming to be under
    another flat part is the sizing error this rule exists for, wearing a new
    key, and is reported as one.
    """
    boxes = []
    parts_ = view_parts(view)["placements"]
    # An indicator that DECLARES it belongs to a part may sit on it: a status
    # LED `for:` its host port overlaps the port by construction. `for:` is
    # the declaration, so honour it here the same way mate-to is honoured.
    owned = {p["id"]: set(targets(p.get("for"))) for p in parts_}
    # A SURFACE-MOUNTED PART IS SUPPOSED TO LIE OVER WHAT IS BEHIND IT. The
    # R740xd's rear handle is bolted to the outside of the panel and its rail
    # crosses a riser slot, a low-profile slot and the NIC card by 4.96, 4.31
    # and 1.14 mm of real ink. That is the hardware, not a sizing mistake.
    # `behaviour: mounts` is the declaration - the same key render.py reads to
    # draw the part in its second pass, in front of the openings - so the two
    # cannot drift apart: a part drawn on top is a part allowed to be on top.
    # TWO MOUNTED PARTS OVERLAPPING EACH OTHER IS STILL REPORTED. Exempting the
    # whole class would hide two labels printed on the same square millimetre,
    # which is a real error and a common one.
    # A FRAME'S BOUNDING BOX IS NOT ITS FOOTPRINT. The rear drive cage's face is
    # a top rail, a bottom rail and two thumbscrew tabs; its box contains four
    # drive bays and its ink touches none of them. `frames:` is the declaration,
    # honoured exactly as `for:` and `mate-to` are. It is NOT interchangeable
    # with `behaviour: mounts` below - that says a part lies OVER what is behind
    # it and draws after the bays, where a cage surrounds its drives and must
    # draw before them.
    framed = {p["id"]: set(targets(p.get("frames"))) for p in parts_}
    # A PART THAT LIES UNDER ANOTHER IS NOT IN THE SAME PLACE AS IT. `under:`
    # names what is over this placement - the board names the shroud and the
    # fan wall, the shroud names the lid. Checked below, per pair: the lower
    # part is a well or the upper is a lid, or the claim is the error.
    # A BAY CAN BE UNDER SOMETHING TOO - it is an opening, so it always has
    # somewhere to be: the R740xd's DIMM sockets are under the mid tray and
    # its drive bays, on the configurations that carry one.
    bays_ = view_parts(view)["bays"]
    under = {p["id"]: set(targets(p.get("under"))) for p in parts_}
    under.update({b["id"]: set(targets(b.get("under"))) for b in bays_})
    bay_ids = {b["id"] for b in bays_}
    every_id = {p["id"] for p in parts_} | bay_ids
    for pid, ups in under.items():
        for u in ups - every_id:
            err(path, "L13", f"{view_name}: {pid} is under '{u}', which is not in this view")
    # `in:` IS THE SAME STACK SEEN FROM THE OTHER END. A part or a bay that
    # stands on a well's floor is over that well, so the well is under it -
    # recorded here so the pair is exempt without the well having to list
    # everything that stands on it. Checked below, once the contracts are in
    # hand: the target must be a well in this view.
    stands = {q["id"]: q.get("in") for q in (*parts_, *bays_) if q.get("in")}
    for pid, w in stands.items():
        if w not in every_id:
            err(path, "L13", f"{view_name}: {pid} is in '{w}', which is not in this view")
        else:
            under.setdefault(w, set()).add(pid)

    def _contract(pid):
        q = next((z for z in parts_ if z.get("id") == pid), None)
        if not q:
            return {}
        cp = resolve_component(q["ref"], lib_roots)
        return (load_yaml(cp) or {}) if cp else {}

    def _mounted(pid):
        return _contract(pid).get("behaviour") == "mounts"

    def _well(pid):
        # the aperture rule, as render.py applies it: a non-module, non-mounted
        # part's `size.d` is a hole depth, so such a part has a floor below the
        # panel for something else to stand over
        if pid in bay_ids:
            return True
        c = _contract(pid)
        if not (c.get("size") or {}).get("d") or c.get("kind") == "module":
            return False
        # a mounted part is solid - unless it says `relief.cavity`, which is
        # the same override render.py honours: the mid tray lifts out AND is
        # the recess its drives sit in
        return not _mounted(pid) or bool((c.get("relief") or {}).get("cavity"))

    for pid, w in stands.items():
        if w in every_id and not _well(w):
            err(path, "L13", f"{view_name}: {pid} says it is in {w}, which is not a well - "
                             "only a recess has a floor to stand on")
    # A SHELF CANNOT BE BELOW THE FLOOR. `floor:` on a bay puts its occupant on
    # a shelf inside the well; a shelf deeper than the well is a hole in it.
    for b in bays_:
        if b.get("floor") and b.get("in") in every_id and b["in"] not in bay_ids:
            d = float((_contract(b["in"]).get("size") or {}).get("d") or 0)
            if d and float(b["floor"]) > d + 0.05:
                err(path, "L13", f"{view_name}: {b['id']} puts its shelf {b['floor']} down "
                                 f"in {b['in']}, which is only {d:g} deep")
            # AND NOT SO SHALLOW THAT THE OCCUPANT STANDS OUT OF THE FACE: a
            # card rises its own `d` from the shelf, and a shelf nearer the face
            # than that puts the card through the lid - riser 3's did, by 0.8
            occ = 0.0
            for ref in (b.get("accepts") or []):
                cp = resolve_component(ref, lib_roots)
                c = (load_yaml(cp) or {}) if cp else {}
                occ = max(occ, float((c.get("size") or {}).get("d") or 0))
            if occ and float(b["floor"]) + 0.05 < occ:
                err(path, "L13", f"{view_name}: {b['id']} puts its shelf {b['floor']} down and "
                                 f"its occupant is {occ:g} tall - it would stand "
                                 f"{occ - float(b['floor']):.1f} out of the face")

    def _stacked(lo, hi):
        if hi not in under.get(lo, ()):
            return False
        if _well(lo) or _mounted(hi):
            return True
        err(path, "L13", f"{view_name}: {lo} says it is under {hi}, but it is not a "
                         f"well and {hi} is not mounted - there is no height between them")
        return True
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
    for b in bays_:
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
                if b[0] in framed.get(a[0], ()) or a[0] in framed.get(b[0], ()):
                    continue
                if _mounted(a[0]) != _mounted(b[0]):
                    continue
                if _stacked(a[0], b[0]) or _stacked(b[0], a[0]):
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


def _is_class(placement, cls, lib_roots):
    cp = resolve_component(placement.get("ref", ""), lib_roots)
    return bool(cp) and (load_yaml(cp) or {}).get("class") == cls


def lint_device_cutouts(path, view_name, view, lib_roots, seen_through=()):
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
    #    A BAY ON ANOTHER FACE CAN FILL ONE. An open back is a hole whose
    #    contents are seated from the front - a bay's `rear:` names the cutout
    #    it is seen through - so `seen_through` counts as filled.
    filled = {q.get("id") for q in placements} | {
        b.get("id") for b in view_parts(view)["bays"]} | set(seen_through)
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
    #    clock connectors and none for its ports.
    #
    #    LAMPS AND BUTTONS ARE IN NOW, AND THE REASON THEY WERE NOT USED TO BE
    #    FALSE. This read "no lamp in the library has a cutout and no button does
    #    either - that is a modelling convention held consistently". There were
    #    46, across nine devices; the MX204 alone punched twenty. The real
    #    position was that the library disagreed with itself - Juniper cut its
    #    lamps, Cisco and Edgecore did not - and #68 settled it by measuring
    #    rather than by preference: 35 of those 46 already used the same rule as
    #    every port, so cutting the rest was not a new convention but the one
    #    already in use. A faceplate lamp penetrates the metal, and the drawing
    #    may as well say so.
    def _covered(fb):
        """Is this footprint already accounted for by a hole or a connector?"""
        area = (fb[2] - fb[0]) * (fb[3] - fb[1])
        if not area:
            return True
        for b in list(boxes.values()) + [_footprint(x, lib_roots) for x in placements
                                         if _is_class(x, "port", lib_roots)]:
            if not b:
                continue
            ix = min(fb[2], b[2]) - max(fb[0], b[0])
            iy = min(fb[3], b[3]) - max(fb[1], b[1])
            if ix > 0 and iy > 0 and (ix * iy) / area > 0.5:
                return True
        return False

    for q in placements:
        cp = resolve_component(q.get("ref", ""), lib_roots)
        cls = (load_yaml(cp) or {}).get("class") if cp else None
        if cls not in ("port", "led", "button"):
            continue
        if q.get("mate-to"):
            continue          # an occupant sits in its host, not in the metal
        if q.get("id") in boxes:
            continue
        if cls in ("led", "button"):
            # A LAMP CAN ALREADY BE PUNCHED under a different id than its hole,
            # and that is real hardware rather than bookkeeping: four Juniper
            # files break the shared-id convention, declaring the hole as
            # `esd-rear` while the part is `esd-rear-jack`; going by id alone
            # punched the same hole twice, which L39 itself then reported as
            # two holes sharing metal. It is found by asking where the thing
            # sits, not what it is called.
            fb = _footprint(q, lib_roots)
            if fb and _covered(fb):
                continue
        what = "port" if cls == "port" else "lamp"
        warn(path, "L39", f"{view_name}: {what} {q.get('id')} has no cutout, on a "
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
# sfp56 AND cxp WERE MISSING, and a cage missing from this set is never asked -
# `media not in PLUGGABLE_CAGES` skips the group in silence, which is the same
# shape as a type table with no row for a form factor. Two groups on two devices
# escaped L40 entirely while sfp, sfp-plus, sfp28 and qsfp56 were all listed;
# test_silent_drops.py holds the set against the media the library actually uses.
# qsfp112 JOINED ON THE DAY IT LANDED, which is what that test is for. The
# EXP400-32X is the library's first QSFP112 device - the 400G four-lane QSFP, one
# generation past qsfp56 on the same cage - and adding the device without adding
# the media would have made its port group the third to escape L40 in silence.
# The test failed first and this line is its answer, not the other way round.
PLUGGABLE_CAGES = {"sfp", "sfp-plus", "sfp28", "sfp56", "sfp-dd", "qsfp", "qsfp28",
                   "qsfp56", "qsfp112", "qsfp-dd", "osfp", "xfp", "cfp", "cfp2",
                   "cxp"}


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


# THE DEFINITION LIVES IN capability.py AND IS IMPORTED, not copied. It used to
# live here, and the grader had its own idea of the same face: the linter
# accepted the Dell R740xd's 482.6 mm front because its ears carry a VGA and a
# power button, while the capability grader called that a chassis-width
# disagreement and stopped the device at level 2 with six good views. One face,
# two rules, opposite answers. See issue #105.
EAR_ZONE_MM = capability.EAR_ZONE_MM
RACK_FACE_MM = capability.RACK_FACE_MM
_seated_in_an_ear = capability.seated_in_an_ear


def lint_device_rack_ears(path, data):
    """L43: a body as wide as the rack face still has its ears on.

    The library draws devices WITHOUT rack ears - the modelled body is the metal
    between the ear fold lines - and that convention lived in reviewers' heads.
    The MX204 has integral ear flanges and its own table calls the chassis 19
    inches, so the model faithfully included them and nothing said otherwise.

    Structural and cheap: a front or rear face measuring 480-487 mm is almost
    certainly a rack face rather than a body. The widest body in the library
    today is 443 mm, so this costs nothing until it fires.

    UNLESS THE EARS CARRY COMPONENTS, WHICH IS A DIFFERENT DEVICE. The rule was
    written for the MX204, whose flanges are bare metal - subtract them and
    nothing is lost. Dell builds the ears into the faceplate and PUTS PORTS IN
    THEM: a PowerEdge R740xd has a VGA and a USB in the right-hand ear and the
    power button and status indicators in the left, and its front measures
    482.6 x 86.8, which Gate 1 confirms against the render at 2.10% where the
    434 mm body fails at 13.5%. Modelling that face at 434 mm would leave real,
    addressable, field-visible ports with nowhere to live.

    So the test is what is SEATED out there, not how wide the face is. Bare
    flanges have nothing in the outer 25 mm; populated ears do. No new field to
    author and nothing to remember - the drawing says which kind of device it is.
    """
    for vname, view in (data.get("views") or {}).items():
        if vname not in ("front", "rear"):
            continue
        w = ((view or {}).get("size") or {}).get("w")
        if not (w and RACK_FACE_MM[0] <= float(w) <= RACK_FACE_MM[1]):
            continue
        if _seated_in_an_ear(view or {}, float(w)):
            continue
        warn(path, "L43", f"{vname}: view is {w} wide, which is the 19-inch "
             "rack face, not a body. Ears are never drawn - measure between "
             "the fold lines and record the ear extent in provenance. If this "
             "device's ears are integral AND carry components, seat them "
             f"within {EAR_ZONE_MM:g}mm of an end and this rule will stand down")


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
    # (box, holes): a part's windows are not part of what buries a field. The
    # MaiaEdge PBC-2000's louvres are seen through its bezel's two octagons,
    # and by the bezel's box alone both fields read 100% buried.
    boxes = []
    for b in vp["bays"]:
        bb = _decor_box(b)
        if bb:
            boxes.append((bb, []))
    for q in vp["placements"]:
        c = _instance_size(q.get("ref"), lib_roots)
        if not c or not q.get("at"):
            continue
        w, h = c
        holes = placed_openings(q, lib_roots)
        if q.get("rotate") in (90, 270, -90):
            cx, cy = q["at"][0] + w / 2, q["at"][1] + h / 2
            boxes.append(((cx - h / 2, cy - w / 2, cx + h / 2, cy + w / 2), holes))
        else:
            boxes.append(((q["at"][0], q["at"][1], q["at"][0] + w, q["at"][1] + h), holes))

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
        for fb, holes in boxes:
            ox = min(db[2], fb[2]) - max(db[0], fb[0])
            oy = min(db[3], fb[3]) - max(db[1], fb[1])
            if ox > 0 and oy > 0:
                covered += ox * oy - open_area(
                    (max(db[0], fb[0]), max(db[1], fb[1]),
                     min(db[2], fb[2]), min(db[3], fb[3])), holes)
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
                                     "anchor": m.get("anchor") or "middle",
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
    `common/qsfp-cage@2` was out by 0.54 mm vertically, which is small, real, and
    exactly the kind of thing nobody finds by looking (@3 puts the point on the
    aperture's).

    A warning: which of the two is right is a question about the part, and the
    fix is sometimes to move the declared point and sometimes to correct the
    composition offset.
    """
    if data.get("class") != "port" or data.get("interface"):
        return

    def _res(ref):
        q = resolve_component(ref, lib_roots)
        return load_yaml(q) if q else None

    iface, at, _ = presented_interface(data, _res)
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


def lint_component_seat_point(path, data, _lib_roots=None):
    """L106: the point an interface is presented at, and the feature it sits on.

    `presented_interface` presents a contract's own `interface` at the point
    `interface-at` names (default `mate`), and lifts a part seated there by the
    `out` of the relief feature that point sits `on:` (pluggables D, D3). Both
    are names, and a name that points at nothing does not fail loudly anywhere
    else: an `interface-at` naming no point falls back to the old `mate`
    answer, and an `on:` naming no feature - or one with no `out` - lifts 0.0.
    Either way a boot is drawn inside the plug it wraps and nothing says so.

    ERRORS, not warnings: there is no reading of a dangling name that is right.
    A feature with no `out` does not stand proud, so it has no rear face to
    seat on; `sink`, `top` and `lift` answer other questions.
    """
    cps = data.get("connection-points") or {}
    at = data.get("interface-at")
    if at is not None and at not in cps:
        err(path, "L106", f"interface-at: {at!r} names no connection point - "
                          f"declared: {', '.join(sorted(cps)) or 'none'}")
    features = {f.get("node"): f for f in
                ((data.get("relief") or {}).get("features") or [])
                if isinstance(f, dict)}
    for name, cp in cps.items():
        # AN UNQUOTED `on:` IS NOT THE KEY `on`. YAML 1.1 - which yaml.safe_load
        # speaks - reads a bare `on` as boolean true, so `{..., on: body}` loads
        # as `{True: 'body'}`, `cp.get("on")` finds nothing, and the point
        # silently lifts 0.0: the exact failure this rule exists to make loud.
        # The library already quotes it elsewhere (`states: ['off', 'on']`).
        # `k is True`, not `True in cp`: True == 1 == 1.0, so the membership
        # test also matched a YAML key of 1 and called it an unquoted `on:`.
        if isinstance(cp, dict) and any(k is True for k in cp):
            err(path, "L106", f"connection-point {name!r} has a key YAML read as "
                              "boolean true - an unquoted `on:`; write it `'on':`")
        on = cp.get("on") if isinstance(cp, dict) else None
        if on is None:
            continue
        f = features.get(on)
        if f is None:
            err(path, "L106", f"connection-point {name!r} is on: {on!r}, which is "
                              "no relief.features[] node of this part")
        elif f.get("out") is None:
            err(path, "L106", f"connection-point {name!r} is on: {on!r}, which has "
                              "no `out` - a part seated there needs the depth of "
                              "the feature's rear face to stand on")


def lint_device_power_redundancy(path, data):
    """L66: a power group with more than one bay states its redundancy.

    WHAT THIS IS FOR. `power-output-w` on a supply says what one module makes.
    Two of them in a chassis is then ambiguous in exactly the way that matters:
    2 x 1600 W is either a 3200 W box or a 1600 W box that survives losing a
    supply, and the modules cannot tell you which - only the chassis knows. A
    reader summing the bays gets the wrong number half the time, and it is the
    half where the answer is "this box draws twice what you provisioned".

    So the module states what it passes and the GROUP states whether they add.
    One bay needs no such statement: there is nothing to add and nothing to
    stand in.

    The form is the vendor's own notation - `1+1`, `2+2`, `n+1`, `n+n` - and
    `redundancy-note` carries the sentence it was read from, because the forms
    collapse detail that the note keeps: whether the pair is active-active or
    standby, and, on a chassis sold in two power variants, which variant the
    figure belongs to.
    """
    groups = data.get("groups") or {}
    bays = {}
    for view in (data.get("views") or {}).values():
        for b in ((view or {}).get("components") or {}).get("bays") or []:
            g = b.get("group")
            if g:
                bays[g] = bays.get(g, 0) + 1
    for name, g in groups.items():
        g = g or {}
        if (g.get("role") or "") != "service" or bays.get(name, 0) < 2:
            continue
        # the group has to actually hold power - a fan group is service too
        term = str(g.get("term") or "").lower()
        if not any(w in name.lower() or w in term for w in ("psu", "power", "pem")):
            continue
        if str(((g.get("attrs") or {}).get("redundancy")) or "").strip():
            continue
        warn(path, "L66", f"group '{name}' has {bays[name]} power bays and does not say "
             f"whether they add up. Two supplies are either twice the capacity or the "
             f"same capacity twice - set attrs.redundancy to the vendor's form "
             f"('1+1', 'n+1', 'n+n', '2+2') with a redundancy-note quoting the source")



# The words that make a service group a CONTROL-PLANE or a FABRIC group. Matched
# as whole tokens of the group name and of the words of its term, never as
# substrings: `re` inside "furniture" and `fc` inside any three-letter run would
# otherwise drag in half the library. Each vendor gets to keep its own spelling -
# Cisco RSP/RP, Juniper RE/RCB/SCB/SFB/SIB, a supervisor, a Casa SMM.
CONTROL_PLANE_WORDS = {
    "re", "res", "rp", "rps", "rsp", "rsps", "scb", "scbs", "rcb", "rcbs",
    "sup", "sups", "supervisor", "supervisors", "smm", "smms",
    "routing", "engine", "engines", "processor", "processors", "control",
}
FABRIC_WORDS = {
    "fabric", "fabrics", "fc", "fcs", "sfb", "sfbs", "sib", "sibs", "sfc", "sfcs",
}
# Whole words here too, and for the same reason: `fan` is inside "fanless",
# which several access switches are. `cooling` and `thermal` are what the
# chassis vendors call the same tray.
FAN_WORDS = {
    "fan", "fans", "fantray", "fantrays", "cooling", "thermal", "blower", "blowers",
}


def _group_words(name, term):
    return set(re.split(r"[^a-z0-9]+", f"{name} {term}".lower())) - {""}


def lint_device_control_plane_redundancy(path, data):
    """L67: a control-plane or fabric group with more than one bay states its
    redundancy.

    WHAT THIS IS FOR. L66 next door settled the power question - two supplies are
    either twice the capacity or the same capacity twice - and the cards that run
    and switch the box are ambiguous the same way, for higher stakes. A chassis
    with two RSPs is either two working processors or one processor plus a spare,
    and the CARD cannot say which: the ASR 9000's RSP is one part number that is
    active/standby for control and active/active for fabric on the same chassis,
    on the same day. Only the chassis knows. A reader who counts the bays gets
    the capacity wrong in the direction that hurts - "we have seven fabric cards,
    so we have seven planes of headroom", when six of them carry the traffic and
    the seventh exists so that losing one costs nothing.

    So the group states it, in the vendor's own notation, with
    `redundancy-note` carrying the sentence it was read from. The forms here are
    wider than power's: 1+1 for an RSP/RP or Routing Engine pair, 2+1 for the
    MX960's three SCBs, 6+1 for the ASR 9912/9922's seven FC cards, 7+1 for the
    MX2008's eight SFBs, n+1 where the guide itself declines to spell the n.

    THE FORM DOES NOT HAVE TO MATCH THE BAY COUNT, and two entries in the library
    deliberately do not. The ASR 9910 has five FC bays and states 6+1, because
    Cisco counts fabric planes across the RSP pair as well as the FCs. The MX960
    has two dedicated SCB bays and states 2+1, because the third SCB seats in
    line-card slot 6. Both notes say so. Arithmetic on the bay count is exactly
    the reasoning this rule exists to replace, so a rule that policed the sum
    would be enforcing the mistake.

    WHAT GOING WRONG LOOKS LIKE - and this is why the match is on whole tokens
    rather than substrings. The first pass at the sibling power rule keyed on any
    `N+M` in the file and read a fan tray's "5+1" as a power figure. The same
    trap is worse here because the abbreviations are two letters long: a naive
    substring search for `re` matches "furniture", and one for `fc` matches
    nothing useful but would match anything. So the group's name and term are
    split into words and only whole words count.
    """
    groups = data.get("groups") or {}
    bays = {}
    for view in (data.get("views") or {}).values():
        for b in ((view or {}).get("components") or {}).get("bays") or []:
            g = b.get("group")
            if g:
                bays[g] = bays.get(g, 0) + 1
    for name, g in groups.items():
        g = g or {}
        if (g.get("role") or "") != "service" or bays.get(name, 0) < 2:
            continue
        words = _group_words(name, str(g.get("term") or ""))
        kind = ("control-plane" if words & CONTROL_PLANE_WORDS else
                "fabric" if words & FABRIC_WORDS else None)
        if kind is None:
            continue
        if str(((g.get("attrs") or {}).get("redundancy")) or "").strip():
            continue
        warn(path, "L67", f"group '{name}' has {bays[name]} {kind} bays and does not say "
             f"whether the second card is a working one or a spare. Set attrs.redundancy "
             f"to the vendor's form ('1+1', '2+1', '6+1', 'n+1') with a redundancy-note "
             f"quoting the sentence and naming the guide it came from")


def lint_library_comparable_facts(roots, docs):
    """L68: a measurement keeps one name, and one section, across the library.

    WHAT THIS IS FOR. A side-by-side of the MX204 and the S9510-28DC printed
    "Max draw: 280 vs 137", which reads as the UfiSpace box drawing half what
    the Juniper does. It draws more - 306 W on DC, 301.2 on AC, filed under
    `power-max-dc-w` and `power-max-ac-w`. The comparison asked for
    `power-max-w`, did not find it, and reached for the closest key it could
    see. The defect was not a missing number; it was a WRONG one, and nothing
    on the page could have told a reader.

    Two halves, and both are censuses rather than complaints - the same stance
    L24 and L40 take, because a vocabulary harvested from what accumulates is
    worth more than one designed from a dozen devices.

    THE TAIL. A spelling no fact in facts.py claims cannot appear in a
    comparison at all. Reported per key with the count of devices carrying it,
    so the ones worth promoting are the ones that show up.

    THE DRIFT, and this one is an error the existing rules cannot see. L25 is
    an ERROR for two sections claiming one key - but it reads ONE DEVICE, so
    `optics-qsfp28` under `features` here and `performance` there passes it
    while making the key unfindable by section. The module docstring of
    attrsections says keys are globally unique; this is what actually holds
    them to it.
    """
    from portrayal import comparable as facts_mod
    homes, tail = {}, {}
    for path, doc in docs:
        for section, body in (doc.get("attrs") or {}).items():
            if not isinstance(body, dict):
                continue
            for k in body:
                homes.setdefault(k, {}).setdefault(section, []).append(path)
        for k in facts_mod.unclaimed(doc):
            tail[k] = tail.get(k, 0) + 1

    for key in sorted(homes):
        where = homes[key]
        if len(where) > 1:
            named = ", ".join(f"{s} ({len(where[s])})" for s in sorted(where))
            # AN ERROR, and it was a warning for exactly as long as it took to
            # empty. L25 is already an error for the same defect inside one
            # device; being lenient across devices made the section axis a
            # suggestion, which is how 17 keys came to have two homes. The
            # library is at zero, so this can hold the line rather than
            # describe a backlog.
            err(roots[0], "L68", f"attrs key {key!r} is filed under more than one "
                f"section across the library - {named}. L25 only sees one device at "
                f"a time, so this passes it while making the key unfindable by "
                f"section. One fact, one section")

    if tail:
        top = sorted(tail.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        shown = ", ".join(f"{k} ({n})" for k, n in top)
        warn(roots[0], "L68", f"{len(tail)} attrs spelling(s) are claimed by no "
             f"comparable fact, so nothing can line them up between two devices. "
             f"Most-used: {shown}. A census, not a complaint - promote the ones "
             f"that recur into comparable.py, leave the genuine one-offs alone")


def lint_library_aliases(docs):
    """L111: an alias resolves to one drawing, or says it knowingly does not.

    `aliases:` exists so an HCL row reading AS7535-28XB or NCP-40C lands on one
    Portrayal id (#514). A name two devices both claim sends that row to
    whichever the consumer happened to read first, and an alias equal to some
    device's `model` makes the canonical name ambiguous with a nickname. Both
    are library-wide facts no single manifest can see, so this reads them all.

    `shared: true` is the one way out and it has to be unanimous: an OEM that
    sells either of a pair under one name is a real fact (DriveNets NCP-96X6C-S
    on the S9600-102XC and the S9601-102XC), but one device saying so while the
    other stays silent is a collision nobody decided. A `shared` flag nothing
    else claims is stale, and is an error for the same reason.
    """
    models, claims = {}, {}
    for path, doc in docs:
        if not isinstance(doc, dict) or doc.get("kind") != "device":
            continue
        m = str(doc.get("model") or "").strip().casefold()
        if m:
            models.setdefault(m, []).append(path)
    for path, doc in docs:
        if not isinstance(doc, dict) or doc.get("kind") != "device":
            continue
        own = str(doc.get("model") or "").strip().casefold()
        seen = set()
        for a in doc.get("aliases") or []:
            if not isinstance(a, dict) or not a.get("name"):
                continue
            name = str(a["name"])
            key = name.strip().casefold()
            if key in seen:
                err(path, "L111", f"alias {name!r} is listed twice (names compare "
                    f"case-insensitively). List it once")
                continue
            seen.add(key)
            if key == own:
                err(path, "L111", f"alias {name!r} repeats this device's own `model`. "
                    f"`model` is already the canonical name; drop the alias")
            for other in models.get(key, []):
                if other != path:
                    err(path, "L111", f"alias {name!r} is the `model` of {other}. An "
                        f"alias may not shadow another device's canonical name")
            claims.setdefault(key, []).append((path, name, a.get("shared") is True))
    for key, who in sorted(claims.items()):
        if len(who) == 1:
            path, name, shared = who[0]
            if shared:
                err(path, "L111", f"alias {name!r} says `shared: true` but no other "
                    f"device claims it. Drop the flag, or add the alias to the device "
                    f"it is shared with")
            continue
        if all(s for _, _, s in who):
            continue
        for path, name, shared in who:
            if not shared:
                others = ", ".join(str(p) for p, _, _ in who if p != path)
                err(path, "L111", f"alias {name!r} is also claimed by {others}, so a "
                    f"lookup by it cannot pick one drawing. Drop it from all but one, "
                    f"or mark it `shared: true` in every claimant and say why in `note`")


def lint_device_fan_redundancy(path, data):
    """L69: a cooling group with more than one bay says how many fans it can lose.

    The third of the family, after L66 for power and L67 for the cards that run
    and switch the box, and it closes the set: every group whose bays hold
    interchangeable redundant modules now states whether the spare is spare.

    WHY IT WAS WORTH DOING SEPARATELY. The comparison layer resolved
    `fan-redundancy` on 0 of 84 devices while 23 of them carried the figure as
    `attrs.fan-redundancy` prose and 14 more had it in their own description.
    The data was in the library the whole time and no consumer could reach it,
    because prose is not a field - which is the same gap `power-envelope`
    filled badly when a redundancy column went looking for something to show.

    THE ARITHMETIC IS NOT POLICED, and deliberately. A form is the vendor's
    claim and a bay count is ours; on the 40 stated here they happen to agree
    exactly - a six-bay tray says 5+1 - but the ASR 9910 states 6+1 for a
    five-bay cage because Cisco counts planes across the RSP pair, and a rule
    that demanded the sum would have called that an error. Where the two
    disagree it is a question, not a fault.

    WHAT THE CONFLICTS TAUGHT. Four Edgecore chassis are left unstated on
    purpose. Their staged datasheets hold TWO different fan figures each, and
    in every case exactly one of them fills the bay count - so the tempting move
    is to take the one that fits. That is arithmetic wearing a citation, the
    same move refused for the ASR 9000 power trays, and it stays refused.
    """
    groups = data.get("groups") or {}
    bays = {}
    for view in (data.get("views") or {}).values():
        for b in ((view or {}).get("components") or {}).get("bays") or []:
            g = b.get("group")
            if g:
                bays[g] = bays.get(g, 0) + 1
    for name, g in groups.items():
        g = g or {}
        if (g.get("role") or "") != "service" or bays.get(name, 0) < 2:
            continue
        # whole words: `fan` is inside "fanless" and this rule is about trays
        if not (_group_words(name, str(g.get("term") or "")) & FAN_WORDS):
            continue
        if str(((g.get("attrs") or {}).get("redundancy")) or "").strip():
            continue
        warn(path, "L69", f"group '{name}' has {bays[name]} cooling bays and does not "
             f"say how many fans the box can lose. Set attrs.redundancy to the "
             f"vendor's form ('3+1', '5+1', 'n+1') with a redundancy-note quoting "
             f"the sentence and naming where it came from")


def lint_device_declared_silence(path, data):
    """L70: a `fact:` gap names a real fact, and does not contradict the device.

    THE THIRD STATE, and the reason it needs guarding. A blank in a comparison
    meant two things that looked identical - the vendor publishes nothing, or
    nobody has looked. Six ASR 9000 chassis had the first case written down in
    provenance ("this is the vendor being silent, not this model being thin")
    where no consumer could reach it. Scoping a `vendor-silent` gap
    `fact:<name>` makes that reachable.

    Which buys two ways to be wrong, and both are silent without this rule.

    A MISSPELLED FACT NAME claims nothing. `fact:peak-power` resolves to no
    fact, the gap looks discharged in the file and the comparison still shows a
    bare blank - the worst outcome, because somebody did the work and it did
    not land.

    A CONTRADICTION is worse than either state alone: the device states a
    figure AND says the vendor publishes none. One of the two is wrong and
    nothing here can tell which, so the resolver refuses to prefer one and this
    asks a person. It is an error rather than a warning because a reader shown
    a number has no way to know a retraction was filed against it.
    """
    from portrayal import comparable as facts_mod
    stated = facts_mod.resolve(data)
    for name, why in facts_mod.declared_silence(data).items():
        if name not in facts_mod.BY_NAME:
            err(path, "L70", f"a vendor-silent gap is scoped 'fact:{name}', which is "
                f"not a comparable fact. The gap reads as discharged and the comparison "
                f"still shows a blank, so the work does not land. Known names are in "
                f"comparable.py")
            continue
        if stated.get(name, {}).get("readings"):
            got = stated[name]["readings"][0]
            err(path, "L70", f"the device states {name} as {got['value']!r} from "
                f"{got['from']} AND declares the vendor silent on it "
                f"({why.get('what')}). One of the two is wrong; a reader shown the "
                f"number cannot know a retraction was filed against it")


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


def lint_pluggable_family_interfaces(root):
    """L103: a family's `interface` matches at least one component's
    `interface` - the reverse of L102's question.

    L102 asks whether the tree resolves against the registry; this asks
    whether the registry resolves against the tree. A family whose cage no
    component declares is a family the vocabulary needs without the metal to
    back it, which is exactly `sfp-dd`'s situation today - the SFP-DD MSA
    defines a real cage, `sfp-dd` is one of the fifteen values `media`
    carries, and no `std/` part for it has been modelled yet.

    A REGISTRY THAT LOADED NO FAMILIES IS ITSELF A FINDING HERE, reported
    before the loop. Every question this rule asks is asked of the registry,
    so an empty one would otherwise make it pass by having nothing to check -
    exactly what `_load_pluggable_families`'s `return {}` is justified by.

    WARNING, NOT ERROR, and deliberately the opposite of L102's severity.
    `sfp-dd` is a correct registry entry, not a defect, and an error here
    would fail the whole corpus for stating the vocabulary the media values
    already demand. A warning that stays exactly one family wide, forever,
    is a fine outcome; a warning that grows is the corpus and the registry
    drifting apart the way L102 catches in the other direction.
    """
    root = Path(root)
    # A REGISTRY THAT DID NOT LOAD IS REPORTED, NOT PASSED OVER IN SILENCE.
    # `_load_pluggable_families` returns `{}` on a broken checkout precisely
    # so the rules that read it say so - but this rule's whole body is a loop
    # over the registry, so an empty one made it the check that passes by
    # having nothing to check, which is the failure mode that justification
    # exists to prevent. L102 reports from the tree's side; this is L103's.
    if not PLUGGABLE_FAMILIES:
        warn(root / "…", "L103", "spec/schemas/pluggables.yaml loaded no "
             "families - every question this rule asks is asked OF the "
             "registry, so with none loaded it can report nothing else")
        return
    # A ROOT WITH NO `components/` AT ALL is nothing to check against, not a
    # library where every family is unmodelled - the same way
    # `lint_vendor_registry` and `lint_unplaced_majors` treat one. This guard
    # has to stay ahead of the walk: `iter_components` tolerates a missing
    # root by yielding nothing, which here would read as an empty library.
    if not (root / "components").is_dir():
        return
    # THE ONE TRUE WALK. `comp_root.glob("**/contract.yaml")` matched at any
    # depth, so a contract.yaml outside the components/<ns>/<name>/v<major>/
    # grammar counted as a component, and came back unsorted.
    interfaces = set()
    for f in libwalk.iter_components([root]):
        d = load_yaml(f)
        if isinstance(d, dict) and d.get("interface"):
            interfaces.add(d["interface"])
    for name, fam in sorted(PLUGGABLE_FAMILIES.items()):
        fi = fam.get("interface")
        if fi and fi not in interfaces:
            warn(root / "…", "L103", f"family {name!r} names interface {fi!r}, "
                "which no component in the library declares - model the cage, "
                "or leave it as the vocabulary's answer to a form factor not "
                "yet built, per this family's own `source` in "
                "spec/schemas/pluggables.yaml")


# A ref is a whole string or it is prose. `ufispace/psu-120-ac@1` appears inside
# a sentence on the S9502 explaining why that device does NOT place it, and a
# substring search would have read that explanation as a use - turning the one
# part whose absence is best documented into the one part that looked seated.
MAJOR_REF = re.compile(r"^[a-z0-9_-]+/[a-z0-9._-]+@[0-9]+$")


def _ref_strings(node):
    """Every string in a parsed manifest that IS a component ref.

    Deliberately not a list of the keys a ref may appear under. That list is
    already written twice in this repository - `component_refs` for devices,
    `_inputs` for the renderer - and BOTH of them stop at a contract's `parts`,
    so neither sees the sixteen MIC twins that `mpc1e-3d-v960` names in a bay.
    A rule that decides whether a part may be DELETED cannot afford that shape
    of miss, and the failure modes are not symmetric: reading one string too
    many leaves a dead part alive, reading one too few deletes a live one.
    """
    if isinstance(node, str):
        if MAJOR_REF.match(node):
            yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _ref_strings(k)
            yield from _ref_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _ref_strings(v)


def _major_of(contract_path):
    """`ns/name@major` from library/components/<ns>/<name>/v<major>/contract.yaml."""
    return (f"{contract_path.parents[2].name}/{contract_path.parents[1].name}"
            f"@{contract_path.parent.name[1:]}")


def lint_unplaced_majors(root):
    """L89: a component major nothing reaches says why nothing reaches it.

    THE LIBRARY IS THE ONLY CONSUMER. Every reference to a part is inside this
    repository, so "does anything use this" is a question that can be answered
    exactly rather than guessed at - and until now nothing asked it. 55 majors
    of 587 were reachable from no device at all, and from the outside they were
    indistinguishable from the 532 that were: same shape of contract, same
    provenance, same place in the catalogue.

    They are not the same, and neither is the right answer for all of them. The
    38 Cisco ASR 9000 cards were drawn off stencils and datasheets and are
    waiting on chassis `accepts` lists that name a different card generation.
    `common/qsfp-drawing` is a reference drawing that nothing should ever seat.
    `common/psu-550w@1` was superseded and is still one of two answers to an open
    question on the PBC-2000, which is why the superseded check below asks
    whether anything NAMES a major and not only whether something seats it.
    Deleting all of those would throw away sourced work; keeping all of them
    quietly is how the count got to 55.

    So the rule asks for the SENTENCE, not for the deletion. `unplaced:` is the
    same shape as `optical.unused` (L80) and a view's `empty:` (L45): the
    library already accepts "nothing here, and here is why" as an answer, and
    what it does not accept is the question going unasked.

    Two ways to fail, and the second is what keeps the first honest:

      - nothing reaches the part and it says nothing about that
      - something DOES reach it and it still carries `unplaced:`, which is a
        waiver outliving what it waived. Without this half, the field becomes a
        line you add once and nobody ever removes.

    A part reached only from an `unplaced:` part is fine and says nothing: the
    QSFP pull tab is composed by the QSFP transceiver, and one sentence about
    the transceiver covers both. Requiring a waiver per part would put the
    reason on the sub-part, which is the one place a reader is not looking.
    """
    comp_root = Path(root) / "components"
    if not comp_root.is_dir():
        return
    contracts = {}
    for c in sorted(comp_root.glob("*/*/v*/contract.yaml")):
        contracts[_major_of(c)] = c

    refs = {}
    for ref, c in contracts.items():
        refs[ref] = set(_ref_strings(load_yaml(c) or {}))
    device_refs, named_by = set(), {}
    for d in sorted((Path(root) / "devices").glob("**/*.yaml")):
        for r in _ref_strings(load_yaml(d) or {}):
            device_refs.add(r)
            named_by.setdefault(r, d)

    def reach(seeds):
        seen, queue = set(), [r for r in seeds if r in contracts]
        while queue:
            r = queue.pop()
            if r in seen:
                continue
            seen.add(r)
            queue.extend(c for c in refs.get(r, ()) if c in contracts)
        return seen

    # SEATED is reachable from a device. JUSTIFIED widens that with the parts a
    # declared-unplaced part composes, which are explained by its sentence.
    seated = reach(device_refs)
    declared = {r for r, c in contracts.items() if (load_yaml(c) or {}).get("unplaced")}
    justified = seated | reach(declared)

    # NON-VACUITY. Every rule here that sweeps a corpus can pass by finding
    # nothing, and this one would report a clean library if the glob broke or if
    # `devices/` moved. The library cannot be mostly unreachable and be working.
    if contracts and len(seated) < len(contracts) // 2:
        err(Path(root) / "…", "L89",
            f"only {len(seated)} of {len(contracts)} component majors are reachable "
            "from any device - this rule's walk is broken, not the library")
        return

    # SUPERSEDED IS NOT UNPLACED, and #172 settled which of the two it is. The
    # `v<major>` level stays, and what pays for it is that an old major goes
    # once nothing references it - otherwise the level accumulates exactly the
    # dead directories that made keeping it look indefensible. Three did:
    # `common/psu-ac-650@1` and `@2` behind an `@3`, `psu-dc-650@1` behind a
    # `@2`, none of them named anywhere.
    #
    # THE EXCEPTION IS WHY THIS CHECKS FOR A MENTION AND NOT JUST A SEATING.
    # `common/psu-550w@1` is also superseded and also seated by nothing, and
    # deleting it would have broken an argument: the PBC-2000 carries a
    # `sources-disagree` gap whose note says the rear photograph reads closer to
    # THIS major's 84.0 than to the 73.5 its device actually places. A retired
    # major can still be one side of an open question, and the way that shows is
    # that something names it in prose.
    mentions = set()
    for f in sorted(Path(root).glob("**/*.yaml")):
        text = f.read_text(errors="ignore")
        own = _major_of(f) if f.name == "contract.yaml" else None
        for ref in contracts:
            if ref != own and ref in text:
                mentions.add(ref)

    live_successor = {}
    for ref in contracts:
        name, major = ref.rsplit("@", 1)
        for other in seated:
            oname, omajor = other.rsplit("@", 1)
            if oname == name and int(omajor) > int(major):
                live_successor[ref] = other

    for ref in sorted(contracts):
        if (ref not in seated and ref in live_successor and ref not in mentions):
            err(contracts[ref], "L89",
                f"{ref} is superseded by {live_successor[ref]}, is reachable from no "
                "device, and is named nowhere. #172 kept the `v<major>` level on the "
                "terms that a dead major goes: delete the directory rather than "
                "describing it in `unplaced:`")
            continue
        if ref not in justified:
            err(contracts[ref], "L89",
                f"{ref} is reachable from no device. Seat it in a device, or in the "
                "`accepts`/`default` of a bay on a part that is seated - or add "
                "`unplaced:` saying what would seat it and what is missing")
        elif ref in seated and (load_yaml(contracts[ref]) or {}).get("unplaced"):
            # NAME WHAT SEATS IT. "something reaches this now" sends the reader
            # back to a search this rule has already done, and the answer is
            # usually one file.
            who = named_by.get(ref)
            where = f"{who}" if who else "a part that is itself seated"
            err(contracts[ref], "L89",
                f"{ref} carries `unplaced:` but IS reachable from a device now, "
                f"through {where}. Remove the sentence; it describes a gap that "
                "has been closed")


# The order a device manifest reads in, top to bottom: what it IS, who sells it,
# where the facts came from, the facts, what is missing, the drawing, and the
# documents behind it. Derived rather than invented - of the four orderings that
# were argued for, this is the one 53 of the 89 manifests already used, so the
# sweep that introduced it moved 25 files instead of 88.
TOP_LEVEL_ORDER = (
    "format", "kind", "name", "version", "maturity",
    "manufacturer", "model", "aliases", "portfolio", "description", "profile",
    # `lint:` sits with `provenance:` rather than at the end, because it is the
    # same kind of statement: this is what we know and how we know it, and this
    # is the rule we have argued with and why.
    "lint", "provenance", "attrs", "chassis", "gaps", "groups", "views",
    "configurations", "datasheet", "references",
)


def lint_device_key_order(path, data):
    """L90: a manifest's top-level keys read in one order across the library.

    L16 has enforced key order INSIDE a view since early on, for the reason that
    a reader who knows where to look stops looking things up. Nothing enforced it
    at the top level, and 89 manifests had grown 22 distinct orderings - `gaps`
    before `groups` in some and after `configurations` in others, `profile`
    floating, `description` and `portfolio` swapping places.

    None of that is wrong and all of it is friction: a reviewer comparing two
    devices reads two different documents, and a contributor copying a nearby
    manifest inherits whichever arrangement they happened to open.

    A KEY THE ORDER DOES NOT KNOW is not an error here. L1 has already reported
    it against the schema, and a second complaint about where it sits would be
    noise on top of a message that already says it does not belong.
    """
    keys = [k for k in data if k in TOP_LEVEL_ORDER]
    want = [k for k in TOP_LEVEL_ORDER if k in keys]
    if keys == want:
        return
    # name the first key that is out of place rather than printing both lists:
    # one key moved is the usual case and the whole order is hard to read.
    for a, b in zip(keys, want):
        if a != b:
            err(path, "L90", f"top-level key {a!r} comes before {b!r}; the order is "
                             + " ".join(want))
            return


def lint_device_airflow_home(path, data):
    """L91: airflow is stated once.

    It had two homes - `chassis.airflow` in 10 manifests and
    `configurations.*.airflow` in 124 places - and the library was split between
    them with no rule for which. The rule the evidence supports is the one
    `render.py` has always implemented, `config.get("airflow") or
    chassis.airflow`: the chassis is the home, and a configuration says it only
    when it DIFFERS.

    That is not what #171 assumed, and the corpus is why. Airflow genuinely
    varies by configuration in 7 of the 48 devices that state it; in 39 it was
    one value repeated across every configuration, five times on the DCP-2. And
    the two schemas never agreed: `chassis.airflow` admits `side` and `passive`,
    a configuration's admits only front-to-back and back-to-front - so half the
    devices stating it on the chassis could not have moved even if the rest
    should have.
    """
    chassis = (data.get("chassis") or {}).get("airflow")
    cfgs = data.get("configurations") or {}
    stated = {n: (c or {}).get("airflow") for n, c in cfgs.items()}
    stated = {n: v for n, v in stated.items() if v}
    if chassis:
        same = sorted(n for n, v in stated.items() if v == chassis)
        if same:
            err(path, "L91", f"configuration(s) {', '.join(same)} restate the chassis "
                             f"airflow {chassis!r}. A configuration states airflow only "
                             "when it differs from the chassis")
        return
    if stated and len(set(stated.values())) == 1 and len(stated) == len(cfgs):
        v = next(iter(stated.values()))
        err(path, "L91", f"every configuration states airflow {v!r} and the chassis "
                         "states none. One fact, one home: put it on the chassis and "
                         "let a configuration override it only where it differs")


def lint_device_provenance_confidence(path, data):
    """L93: a device's provenance entry says how the figure is known.

    THE CENSUS #167 CREATED, and it is the point of that migration rather than a
    side effect. Device provenance was `{key: prose}` - 530 distinct keys across
    89 devices, a median value of 566 characters and a maximum of 6,704 - and the
    confidence word was a convention at the front of the sentence that 35% of
    entries did not follow. So the question "which figures on this device are
    estimated" had no answer a machine could give, which is why L15's `verified`
    gate was a prefix match that saw 42 of 122.

    Restructuring it to `{confidence, note}` does not by itself fill anything in.
    944 entries opened with one of the library's eight words and were migrated
    with it; 744 did not, and NO WORD WAS INVENTED FOR THEM - reading 744
    paragraphs and deciding measured-or-estimated by eye is precisely how an
    estimate becomes a measurement, and this library has a rule against that.

    What changed is that the 744 are now countable. This is the count. It is a
    warning because the entries are honest as they stand - the prose says what
    was done, it just does not say it in a word - and because a census is meant
    to shrink rather than to fail a build somebody else has to unblock.
    """
    prov = data.get("provenance") or {}
    if not isinstance(prov, dict):
        return
    bare = sorted(k for k, v in prov.items()
                  if isinstance(v, dict) and not v.get("confidence"))
    if not bare:
        return
    warn(path, "L93", f"{len(bare)} of {len(prov)} provenance entries state no "
                      f"`confidence` ({', '.join(bare[:4])}"
                      f"{', ...' if len(bare) > 4 else ''}). Add the word the note "
                      "already implies - and where the prose does not say, that is "
                      "a figure whose standing nobody has written down")


# L107's quote shapes. An opening quote is not preceded by a word character and
# is followed by non-space; a closing one is preceded by non-space and not
# followed by a word character. So `don't` never opens or closes, the inch mark
# in `17.32"` never opens, and `'1'` is a quoted numeral, not the start of a
# paragraph-long run that ends at the next apostrophe.
QUOTE_MAX_WORDS = 25
_QUOTED = (re.compile(r'(?<!\w)"(?=\S)([^"\n]*?)(?<=\S)"(?!\w)'),
           re.compile("\u201c([^\u201d]*)\u201d"),
           re.compile(r"(?<!\w)'(?=\S)([^'\n]*?)(?<=\S)'(?!\w)"))


def long_quotes(data, limit=QUOTE_MAX_WORDS, _key=""):
    """(key path, word count, quoted text) for every quoted run in `data`'s
    strings longer than `limit` words. Library-wide census tests call this too,
    so the rule and the count it is held to cannot drift apart."""
    if isinstance(data, str):
        for rx in _QUOTED:
            for m in rx.finditer(data):
                n = len(m.group(1).split())
                if n > limit:
                    yield _key.lstrip("."), n, m.group(1)
    elif isinstance(data, dict):
        for k, v in data.items():
            yield from long_quotes(v, limit, f"{_key}.{k}")
    elif isinstance(data, list):
        for i, v in enumerate(data):
            yield from long_quotes(v, limit, f"{_key}[{i}]")


def lint_quoted_prose(path, data):
    """L107: a vendor's facts are transcribed; its prose is not reproduced.

    README promises it, NOTICE rests on it, and #156 paraphrased the library
    back into line once. Nothing held the line after that, and by 2026-09-21
    (#451) there were 341 quoted runs over 25 words across 202 contracts and
    manifests - 156 distinct passages, 220 of the runs Cisco guide prose, one
    passage copied into 23 contracts. The audit that filed #451 counted 51, because it paired
    quote marks naively; the pairing above is what makes the number real.

    TWENTY-FIVE WORDS, NO EXEMPTION LIST. A lamp-state table is facts, and the
    way to keep facts is to transcribe them - `flashing green = input present,
    output off` - which this rule does not see, rather than to quote the table
    and ask for an exception. A short quotation that pins a disputed word
    ("the C-type appliance inlet") is well under the cap and stays.

    IT WAS A CENSUS FOR ONE DAY. It landed as a warning of the L92/L93 kind
    with test_quoted_prose holding the count from rising (#472), the vendors
    were paraphrased in three passes (#475, #477, #478) and the five shared
    parts in the last one, and at zero it became an error - so the next long
    quotation fails the build instead of joining a backlog.
    """
    runs = list(long_quotes(data))
    if not runs:
        return
    keys = sorted({k for k, _, _ in runs})
    err(path, "L107", f"{len(runs)} quoted run(s) over {QUOTE_MAX_WORDS} words "
                       f"(longest {max(n for _, n, _ in runs)}) at {', '.join(keys[:3])}"
                       f"{', ...' if len(keys) > 3 else ''}. Paraphrase and cite the "
                       "section; transcribe a state table as `state = meaning` pairs")


def lint_device_component_attrs_resolve(path, data):
    """L94: a `component-attrs` key names something the device actually has.

    The key was a component name and is now a component name OR a placement or
    bay id (#193). That is what lets a configuration say something true of ONE
    instance - the ASR 9001-S's two licence-disabled SFP+ ports, where keying by
    the component marks all six `std/sfp-ganged` on the chassis.

    THE COST OF WIDENING A KEY IS THAT MORE TYPOS LOOK LIKE INTENT. Before, a key
    that matched no component did nothing and nothing said so; now there are two
    ways to be right and still the same silence when you are wrong. A
    configuration that sets `sfp-plus-4: {...}` on a chassis with four ports
    numbered 0 to 3 renders exactly as if the line were not there, which is the
    failure #254 is about - not a wrong answer, an absent one.
    """
    names, ids = set(), set()
    for view in (data.get("views") or {}).values():
        parts_ = view_parts(view or {})
        for q in parts_["placements"]:
            if q.get("id"):
                ids.add(q["id"])
            if q.get("ref"):
                names.add(q["ref"].split(":")[0].split("/")[-1].split("@")[0])
        for b in parts_["bays"]:
            if b.get("id"):
                ids.add(b["id"])
            for a in (b.get("accepts") or []) + ([b["default"]] if b.get("default") else []):
                names.add(str(a).split(":")[0].split("/")[-1].split("@")[0])
    for cname, cfg in (data.get("configurations") or {}).items():
        for key in (cfg or {}).get("component-attrs") or {}:
            if key in names or key in ids:
                continue
            err(path, "L94", f"configuration {cname}: `component-attrs` key {key!r} is "
                             "neither a component this device seats nor a placement or "
                             "bay id it declares, so it sets nothing and says nothing")
        # `bay-attrs` is keyed by bay path and was documented with no user at all
        # until #193 gave it one, so it has never been checked. Its first key is
        # its first chance to be wrong.
        for key in (cfg or {}).get("bay-attrs") or {}:
            if key.split("/")[0] in ids:
                continue
            err(path, "L94", f"configuration {cname}: `bay-attrs` key {key!r} names no bay "
                             "this device declares, so it sets nothing and says nothing")


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


def lint_device_pluggable_media(path, data, _lib_roots=None):
    """L102: a device's pluggable media names a rate spec/schemas/pluggables.yaml
    actually carries.

    PLUGGABLE_CAGES is the vocabulary of media values L40 already treats as a
    cage rather than a fixed jack or bonded fibre - `media: fiber` and
    `media: rj45` are not asked about here, the same media filter L40 uses.

    L40'S `term: Port` FILTER IS DELIBERATELY *NOT* MIRRORED. This rule asked
    only groups whose term was `Port`, while the two things that consume a
    group's media - render.py's `cages[]` accept list and L104 - look the
    group up by id and ask its term nothing. A `term: Slot` group declaring
    `media: qsfp-dd400` was therefore consumed by both and validated by
    neither: `_family_by_rate` returns None for it, the accept list silently
    falls back to the aperture's family, and the gap between the corpus and
    the registry that this rule exists to catch goes unreported at exactly
    the placement that reads it. A group whose media is in PLUGGABLE_CAGES is
    answering a cage question whatever its term, so every group is asked.
    Nothing in the corpus changes today - the only non-`Port` groups carrying
    media are `dell/r740xd`'s two `Drive` groups with `media: sff-2.5`, which
    is not a pluggable cage - this only widens an error that fires nowhere.

    Among
    those, `test_pluggable_ladder.py` holds the registry to PLUGGABLE_CAGES
    directly and today the two agree exactly. This rule is the same fact
    checked from the other side, against a real device rather than the
    vocabulary the registry was built from: a device declaring a pluggable
    media the registry has no family for is a gap in one of the two files, and
    the accept list Task 3 builds would silently produce nothing for that
    port - silence being exactly the failure mode L40's own docstring warns
    about for a missing cage.

    ERROR, not warning - unlike L40's optics prose, which is real work that
    accumulates device by device, a media the registry cannot place is a
    contradiction between two files this repository owns, fixable in either
    one without touching a datasheet.
    """
    groups = data.get("groups") or {}
    rates = _pluggable_rates()
    for gid, gdef in sorted(groups.items()):
        gdef = gdef or {}
        media = (gdef.get("attrs") or {}).get("media")
        if media not in PLUGGABLE_CAGES:
            continue
        if media not in rates:
            err(path, "L102", f"group {gid} declares media {media!r}, "
                "which PLUGGABLE_CAGES recognises as a pluggable cage but no "
                "family in spec/schemas/pluggables.yaml carries as a rate")



def _stack_findings(path, data, lib_roots, is_device):
    """L108: every belly-to-belly cage pair faces the library's way, or says why not.

    THE CONVENTION IS ONE MEANING OF `rotate` (docs/pluggables-3d-design.md,
    the stacked-cage decisions of 2026-09-21): 0 is a module seated upright,
    bail at the top and belly at the bottom, which is how every std cage skin
    and every generic transceiver draws. A seated optic takes its cage's turn,
    so a stack drawn the other way round seats its optics with their bails in
    the band between the rows, where no thumb reaches them. Before this rule
    the library drew 1,721 device stacks and 838 card stacks five different
    ways, some to match a photograph under the old art and some by analogy.

    THE PAIRING IS stacks.py's, and the tests read the same module - a rule and
    a census that disagreed about what a pair is would each pass on its own.
    Exceptions are per pair, in `stack-exceptions:`, and one that names no
    checked pair is a finding too. OSFP stacks are skipped, and the message
    says so, because std/osfp@1's art may follow a different convention.
    """
    def resolve(ref):
        c = _contract(ref.split(":")[0], lib_roots) if ref else {}
        return c or None
    for msg in stacks.findings(data, resolve, is_device):
        err(path, "L108", msg)


def lint_device_stack_orientation(path, data, lib_roots):
    """L108 for a device manifest's views. See `_stack_findings`."""
    _stack_findings(path, data, lib_roots, True)


def lint_component_stack_orientation(path, data, lib_roots):
    """L108 for the cages a component composes. See `_stack_findings`."""
    _stack_findings(path, data, lib_roots, False)


_SLOT_CORE = {}


def _slot_core(lib_roots):
    """(render module, Library, families, connectors, candidates) for
    `lib_roots`, built once per process and only when a `default:` exists.

    L114 ASKS THE BUILD'S OWN QUESTION: what does this slot accept? The answer
    is render.slot_entry's - the one core behind components.json `cages` and a
    device's `cages[]` - so a default lint passes is one the published accept
    list offers. Imported here, not at module scope: render.py has never
    imported lint, and nothing else in lint needs the renderer."""
    key = tuple(str(r) for r in lib_roots)
    if key not in _SLOT_CORE:
        from portrayal import render as _render
        _SLOT_CORE[key] = (_render, _render.Library(list(key)),
                           _render._pluggable_families(), _render._connector_registry(),
                           _render._pluggable_candidates(list(key)))
    return _SLOT_CORE[key]


def lint_component_slot_defaults(path, data, lib_roots):
    """L114: a `default:` sits on a slot and names what that slot accepts.

    A default is the shipped state of the product (B3, docs/pluggables-caps-
    design.md, "The shipped default") and the build seats it in every
    configuration that does not key the slot, so a wrong one is drawn
    everywhere. Two ways to write one wrong:

    ON A PART THAT IS NO SLOT. `default:` on a `parts:` entry whose component
    presents no pluggables family and no registered connector interface - or
    at the top level of a component that presents none - names an occupant
    with nowhere to seat.

    NOT IN THE ACCEPT LIST. The slot's `accepts`, as slot_entry derives it for
    components.json: a cage's family ladder, a connector slot's `mates:`
    candidates. A boot does not mate a bore; a plug of the wrong family does
    not fit the cage.

    `""` ships a slot empty: it still has to be on a slot, and accepts
    nothing it needs checking against."""
    own = data.get("default")
    entries = [q for q in (data.get("parts") or [])
               if isinstance(q, dict) and "default" in q]
    if own is None and not entries:
        return
    render_mod, lib, families, connectors, candidates = _slot_core(lib_roots)

    def check(where, placement, want):
        try:
            entry = render_mod.slot_entry(placement, lib, families, connectors,
                                          candidates)
        except (FileNotFoundError, ValueError, KeyError):
            return                      # a bad ref is L5's to report
        if entry is None:
            err(path, "L114", f"{where}: default {want!r} - {placement['ref']} "
                "presents no slot (no pluggables family and no registered "
                "connector interface), so there is nowhere to seat it")
            return
        if want and want.split(":")[0] not in entry["accepts"]:
            err(path, "L114", f"{where}: default {want!r} is not in this "
                f"{entry['kind']} slot's accepts ({entry['interface']}: "
                f"{', '.join(entry['accepts']) or 'nothing'})")

    for q in entries:
        # `ref`, `id` and `at` are required of a `parts:` entry (the schema
        # says so); an entry missing one is L1's finding, not this rule's
        if q.get("ref") and "at" in q:
            check(f"parts/{q.get('id')}", q, q.get("default"))
    if own is not None:
        ref = (f"{path.parents[2].name}/{data.get('name')}@{path.parent.name[1:]}"
               if len(path.parents) > 2 else None)
        if ref:
            check("default", {"ref": ref, "id": "default", "at": [0, 0]}, own)


def _connectors():
    """spec/schemas/connectors.yaml's `interfaces`, from the renderer that
    already reads it (cached there). Lazily imported for L114's reason: lint
    is not a consumer of render except where it must ask the build's own
    question, and a spanning interface is the build's own question."""
    from portrayal import render as _render
    return _render._connector_registry()


def _composed_mates(contract, resolve):
    """{part id: the composed `mate` point}, in this contract's own frame, for
    every `parts:` entry whose component carries one - through the placement's
    own rotation, by `manifest.seat_point`, which is where the build puts it."""
    out = {}
    for q in contract.get("parts") or []:
        if not q.get("id") or not q.get("at") or not q.get("ref"):
            continue
        core = resolve(q["ref"]) or {}
        cm = (core.get("connection-points") or {}).get("mate")
        if not cm or not core.get("size"):
            continue
        out[q["id"]] = seat_point(q["at"], core["size"], q.get("rotate"), cm["at"])
    return out


SPAN_TOLERANCE = 0.01


def _spanning_part_drawn_across(path, data):
    """L116's fifth arm: A PART THAT MATES A SPANNING INTERFACE IS DRAWN ON THE
    CANONICAL AXIS - the pair it fills runs ACROSS, along +x from its own
    `mate` point (manifest.CANONICAL_SPAN_AXIS).

    THE HOST'S AXIS ARRIVES WITH THE SEAT, and that is why the part's own has
    to be pinned. A duplex connector is one moulding with two ferrules and
    cannot turn itself; the library holds two duplex adapters whose pairs run
    at right angles to each other, and a spanning slot publishes the turn that
    carries this canonical axis onto its own (manifest.spanning_axis). A part
    drawn on some other axis is then wrong on EVERY host rather than right on
    one of them, and no view of a single adapter shows it: the cap looks
    perfectly seated on the adapter it was read off.

    CHECKED AS COVERAGE, not as a shape. Where a duplex connector's own
    ferrules sit is not in its contract - a dust cap is a blank moulding with
    nothing inside it a key could name - so what is held is the property the
    drawing has to have: seated on a CANONICAL host, this part lies over both
    of the points that host's bores stand at. Those points are its own `mate`
    displaced along x by the interface's own pitch, which is the one figure the
    registry already carries, so the rule invents nothing.

    It is a weaker rule than an equality and deliberately so: a part wide
    enough to cover the pair on either axis passes, and it deserves to - it
    does cover both bores. What it catches is the narrow one, which is every
    duplex part in this library drawn the wrong way round.
    """
    iface = data.get("mates")
    entry = (_connectors().get(iface) or {}) if iface else {}
    spans = entry.get("spans")
    if not spans:
        return
    own = (data.get("connection-points") or {}).get("mate")
    size = data.get("size") or {}
    if not own or not own.get("at") or not size.get("w") or not size.get("h"):
        return                          # a part with no mate or no size is L11/L1's
    # THE PITCH ARM'S OWN VACUITY GUARD, for the same reason: `STANDARDS` is
    # empty until main() fills it, so an unloaded registry skips - but one that
    # IS loaded and records no pitch leaves this rule nothing to measure and
    # has to say so rather than go quiet.
    key = entry.get("standard")
    std = STANDARDS.get(key)
    pitch = (std or {}).get("pitch")
    if std is not None and not pitch:
        err(path, "L116", f"mates {iface!r}, which spans "
            f"{spans.get('interface')!r}, but its standard {key!r} records no "
            "`pitch` - there is nothing to line the pair up on")
    if not pitch:
        return
    n = int(spans.get("count") or 2)
    mx, my = float(own["at"][0]), float(own["at"][1])
    for i in range(n):
        x = mx + (i - (n - 1) / 2) * float(pitch)
        if -SPAN_TOLERANCE <= x <= size["w"] + SPAN_TOLERANCE and \
                -SPAN_TOLERANCE <= my <= size["h"] + SPAN_TOLERANCE:
            continue
        err(path, "L116", f"mates {iface!r}, which spans {n} "
            f"{spans.get('interface')!r} at the {pitch} pitch of {key!r}, but "
            f"position {i + 1} of that pair falls at "
            f"{[round(x, 4), round(my, 4)]}, outside its own "
            f"{size['w']} x {size['h']} outline - a spanning connector is "
            "drawn ACROSS, with the pair running in x from its own mate "
            "point, and the host's own axis arrives with the seat")
        return


# WHICH WAY A SPANNED BORE'S KEYWAY FACES WHEN THE BORE IS DRAWN UNROTATED, by
# the interface the bore presents, and which way a spanning connector's latches
# face on the canonical axis. `lc`: std/lc-bore@3 and std/lc-bulkhead-bore@1
# both draw their tongue DOWN (spec/tests/test_lc_seated_orientation.py holds
# each part's outline to it), and every duplex part is drawn with its latches
# UP (generic/lc-duplex-plug@2 turns its halves to get there). An interface
# not named here has no keyway this rule knows, and the arm has nothing to say.
SPANNED_KEYWAY_SIDE = {"lc": (0, 1)}
CANONICAL_LATCH_SIDE = (0, -1)


def _spanning_latch_sides(contract, resolve):
    """(latch side, keyway side) for a spanning host, as unit vectors in the
    contract's own frame, or None where the arm has nothing to measure.

    THE LATCH SIDE is the canonical one turned by the axis the host derives -
    the turn the seat will actually draw a duplex connector at. THE KEYWAY SIDE
    is the spanned bores' own convention turned by their shared `rotate`. The
    keyway side is None when the bores do not share one rotate, which is an
    error of its own: a duplex connector is one moulding and cannot put its two
    latches into keyways facing different ways."""
    connectors = _connectors()
    iface = (contract or {}).get("interface")
    spans = ((connectors.get(iface) or {}).get("spans") or {}) if iface else {}
    side = SPANNED_KEYWAY_SIDE.get(spans.get("interface"))
    if side is None:
        return None
    axis = spanning_axis(contract, resolve, connectors)
    if axis is None:
        return None
    places = {q.get("id"): q for q in contract.get("parts") or []}
    rots = {float((places.get(i) or {}).get("rotate") or 0) % 360
            for i in spanned_slots(contract, resolve, connectors)}

    def snap(v):
        return tuple(int(round(c)) for c in v)
    latch = snap(_turn(CANONICAL_LATCH_SIDE, axis))
    keyway = snap(_turn(side, rots.pop())) if len(rots) == 1 else None
    return latch, keyway


def _spanning_latch_on_keyway(path, data, resolve):
    """L116's latch-side arm: THE AXIS A DUPLEX HOST DERIVES PUTS A DUPLEX
    CONNECTOR'S LATCHES ON ITS BORES' KEYWAY SIDE.

    The axis is derived from the ORDER of the spanned bores (manifest.
    spanning_axis) and the keyway from their ROTATE, and nothing tied the two
    together: compose the pair in the other order and the pitch, the midpoint
    and the depth all still hold while every duplex plug seats with its latches
    on the side opposite the keyway. That is exactly main's pre-#496 FS
    adapter, whose upper bore was composed first - a polarity bug found by
    reading FS's port numbers, which the geometry could have caught on its own.
    """
    got = _spanning_latch_sides(data, resolve)
    if got is None:
        return
    latch, keyway = got
    iface = data.get("interface")
    if keyway is None:
        err(path, "L116", f"presents {iface!r}, but the bores it spans are not "
            "all at one `rotate`, so their keyways face different ways and no "
            "duplex connector - one moulding - can latch into both")
        return
    if latch != keyway:
        names = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}
        err(path, "L116", f"presents {iface!r} with a derived axis that turns a "
            f"duplex connector's latch {names.get(latch, latch)}, but its bores' "
            f"keyways face {names.get(keyway, keyway)} - the order the bores are "
            "composed in runs the pair the wrong way round for the way they are "
            "turned")


def lint_component_spanned_geometry(path, data, lib_roots):
    """L116: a component presenting a SPANNING connector interface really hosts
    what it spans.

    `lc-duplex` spans two `lc` bores (spec/schemas/connectors.yaml), and the
    pitch those bores sit at is the interface itself: 6.25, which
    standards.yaml carries on `lc-duplex-receptacle` at `pitch-confidence:
    verified`, sourced to IEC 61754-20 / TIA-604-10 FOCIS 10. A duplex
    connector is one moulding with two ferrules at that spacing, so an adapter
    whose bores are not on it cannot accept one - it does not present
    `lc-duplex`, however its contract is written (docs/pluggables-caps-
    design.md, "The duplex host").

    Four ways for the claim to be false, and all four are errors because a
    wrong one offers the wrong part:
      - the wrong NUMBER of spanned parts (the registry's `spans.count`);
      - the wrong PITCH between their composed mate points;
      - a `mate` of its own that is not their MIDPOINT, which is where a duplex
        connector's own mate lands and so where the build seats it;
      - a spanned bore standing at a DEPTH other than the one this slot
        presents, which is the depth a duplex connector rests on.

    THE DEPTH ARM IS THE ONE A DRAWING CANNOT SHOW. A duplex cap and a simplex
    cap are the same distance off the panel, because they plug the same hole in
    the same face: the adapter presents `lc-duplex` at the `out` of whatever
    relief feature its own `mate` sits `on:`, and its bores are lifted onto
    that same face by their placements. Let the two disagree and a duplex cap
    floats in front of, or sinks behind, the simplex cap it replaces - by a
    figure no view of the front reveals. Both library adapters were held to
    this by a test naming them; a rule holds the next one too.

    MEASURED ON THE COMPOSED MATE POINTS, not on `at`. A stacked pair and a
    side-by-side pair are the same interface turned, and their placements
    differ in axis, rotation and box; their mate points do not. L81 reads `at`
    and says so in its own comments - it has to tell a rotated column from a
    stacked pair - and this rule needs no such argument.

    A FIFTH ARM ASKS THE MIRROR-IMAGE QUESTION of the connector rather than
    the host - is a spanning part drawn on the canonical axis - and it is
    called from here so one rule number covers one subject: whether a duplex
    connector and the adapter it plugs can be put together at all.

    A SIXTH, THE LATCH SIDE, joins the two: the axis the host derives from its
    bores' order must carry the connector's latches (drawn up) onto the side
    its bores' keyways face (drawn down, turned by their shared rotate) -
    `_spanning_latch_on_keyway`.
    """
    _spanning_part_drawn_across(path, data)
    iface = data.get("interface")
    if not iface:
        return
    spans = ((_connectors().get(iface)) or {}).get("spans")
    if not spans:
        return

    def _res(ref):
        q = resolve_component(ref, lib_roots)
        return load_yaml(q) if q else None

    ids = spanned_slots(data, _res, _connectors())
    want_n = spans.get("count")
    if want_n is not None and len(ids) != want_n:
        err(path, "L116", f"presents {iface!r}, which spans {want_n} "
            f"{spans.get('interface')!r} slot(s), but composes {len(ids)}"
            + (f" ({', '.join(ids)})" if ids else ""))
        return
    mates = _composed_mates(data, _res)
    pts = [mates[i] for i in ids if i in mates]
    if len(pts) != len(ids):
        return                          # a part with no mate point is L58/L1's
    # THE PITCH ARM MUST NOT PASS VACUOUSLY. `STANDARDS` is empty until
    # main() fills it, so a registry that is simply not loaded is skipped -
    # but a standard that IS loaded and carries no `pitch` leaves this rule
    # with nothing to check and must say so rather than go quiet.
    key = (_connectors().get(iface) or {}).get("standard")
    std = STANDARDS.get(key)
    want = (std or {}).get("pitch")
    if std is not None and not want:
        err(path, "L116", f"presents {iface!r}, which spans "
            f"{spans.get('interface')!r}, but its standard {key!r} records no "
            "`pitch` - there is nothing to hold the bores to")
    if want:
        for a, b in zip(ids, ids[1:]):
            got = math.dist(mates[a], mates[b])
            if abs(got - float(want)) > SPAN_TOLERANCE:
                err(path, "L116", f"bores {a!r} and {b!r} mate "
                    f"{round(got, 4)} apart, but {iface!r} is the "
                    f"{want} pitch of {(_connectors().get(iface) or {}).get('standard')} "
                    "- an adapter off the interface pitch accepts no duplex "
                    "connector")
    own = (data.get("connection-points") or {}).get(
        data.get("interface-at") or "mate")
    if not own or not own.get("at"):
        err(path, "L116", f"presents {iface!r} but declares no "
            f"{data.get('interface-at') or 'mate'} connection point, so "
            "nothing says where a connector seats")
        return
    mid = [sum(c) / len(pts) for c in zip(*pts)]
    if any(abs(a - b) > SPAN_TOLERANCE for a, b in zip(own["at"], mid)):
        err(path, "L116", f"presents {iface!r} at {list(own['at'])}, but the "
            f"midpoint of {', '.join(ids)} is {[round(c, 4) for c in mid]} - a "
            "duplex connector seats on the midpoint of the pair it fills")
    # AND AT THE SAME DEPTH. What this slot presents is the `out` of the
    # feature its own point sits `on:`; what a bore stands at is its
    # placement's `lift`. A connector spanning the pair rests on the face the
    # pair is let into, so the two are one number.
    presented = presented_interface(data, _res)[2]
    places = {q.get("id"): q for q in data.get("parts") or []}
    for bid in ids:
        got = float((places.get(bid) or {}).get("lift") or 0.0)
        if abs(got - presented) > SPAN_TOLERANCE:
            err(path, "L116", f"presents {iface!r} at a lift of {presented:g}, "
                f"but its bore {bid!r} is placed at lift {got:g} - a connector "
                "spanning the pair rests on the same face the pair is let "
                "into, so a simplex part in the bore and a duplex part over "
                "both would stand at different depths")
    # AND THE RIGHT WAY ROUND: the axis the order of the bores derives carries
    # a duplex connector's latches onto the side their keyways face.
    _spanning_latch_on_keyway(path, data, _res)


def _spanned_default_overlap(path, where, placement, contract, resolve):
    """L115's component arm for one placing entry: the slot it places ships a
    default AND so does one of the bores that slot spans."""
    ids = spanned_slots(contract, resolve, _connectors())
    if not ids:
        return
    if not slot_default(placement, contract):
        return
    parts = {q.get("id"): q for q in contract.get("parts") or []}
    for bid in ids:
        q = parts.get(bid) or {}
        if slot_default(q, resolve(q.get("ref")) or {}):
            err(path, "L115", f"{where}: {placement['ref']} ships a default on "
                f"its own slot AND on the bore {bid!r} it spans. One duplex "
                "connector fills both bores, so a product ships one level or "
                "the other")


def lint_component_spanned_exclusion(path, data, lib_roots):
    """L115, component side: nothing SHIPS both levels of a spanning slot.

    The device side below catches a configuration that fills both. This
    catches the same contradiction written into the contracts, where no
    configuration could be blamed for it and every drawing would carry it: a
    composer placing a duplex adapter with a `default:` of its own over an
    adapter whose bores already ship caps, or such an adapter shipping a
    default on its own slot as well.
    """
    def _res(ref):
        q = resolve_component(ref, lib_roots)
        return load_yaml(q) if q else None

    # EACH FINDING LANDS ON THE FILE THAT WROTE THE CONTRADICTION. A composer
    # is answerable for the `default:` it puts on its own entry; a placed
    # component's TOP-LEVEL default against its own bores is that component's
    # file, reported below when this rule runs over it, so an entry that
    # declares none of its own is not reported here too.
    for q in data.get("parts") or []:
        if not isinstance(q, dict) or not q.get("ref") or "default" not in q:
            continue
        c = _res(q["ref"])
        if c:
            _spanned_default_overlap(path, f"parts/{q.get('id')}", q, c, _res)
    if data.get("default") and len(path.parents) > 2:
        ref = f"{path.parents[2].name}/{data.get('name')}@{path.parent.name[1:]}"
        _spanned_default_overlap(path, "default", {"ref": ref, "id": "default",
                                                   "default": data["default"]},
                                  data, _res)


def lint_device_spanned_exclusion(path, data, lib_roots):
    """L115, device side: a configuration does not fill a spanning slot AND a
    slot it spans (B3, docs/pluggables-caps-design.md, "The duplex host").

    A duplex adapter holds two levels of slot for one piece of hardware: its
    own, which a duplex cap or a duplex plug fills, and its two bores, which
    take simplex parts. One connector fills the pair, so the levels are
    alternatives, not a stack - and the build raises on both filled
    (`render.refuse_spanned_overlap`). This says the same thing before the
    build runs.

    FILLED MEANS AFTER DEFAULTS RESOLVE, which is why `render`'s own helper
    answers the bores here rather than a second reading of `occupants:`: the
    Smartoptics adapter ships capped bores and the FS one ships a duplex cap,
    so most of these contradictions will be a configuration naming ONE level
    over parts that already ship the other.
    """
    from portrayal import render as _render

    def _res(ref):
        q = resolve_component(ref, lib_roots)
        return load_yaml(q) if q else None

    placements = {q.get("id"): q for _v, view in (data.get("views") or {}).items()
                  for q in view_parts(view or {})["placements"]
                  if q.get("id") and q.get("at") and q.get("ref")}
    for cname, cfg in (data.get("configurations") or {}).items():
        cfg = cfg or {}
        occupants = cfg.get("occupants") or {}
        # Every key that could name a spanning slot: one this configuration
        # fills outright, and the PARENT of any key it fills - a bore's host,
        # which may be filled by what it ships rather than by a key.
        keys = set()
        for k, v in occupants.items():
            if v != "":
                keys.add(k)
            if "/" in k:
                keys.add(k.rsplit("/", 1)[0])
        for key in sorted(keys):
            q = placements.get(key)
            if q is None and "/" in key:
                try:
                    _href, mref, _mpath = nested_key_host(key, data, cfg, _res)
                except ValueError:
                    continue            # L12's finding, not this one's
                module = _res(mref) or {}
                q = next((e for e in module.get("parts") or []
                          if e.get("id") == key.rsplit("/", 1)[-1]), None)
            if q is None or not q.get("ref"):
                continue                # a chained key names an occupant, not a part
            contract = _res(q["ref"])
            if not contract or not spanned_slots(contract, _res, _connectors()):
                continue
            if key in occupants:
                try:
                    filled = occupant_spec(key, occupants[key]) is not None
                except ValueError:
                    continue            # L12's finding
            else:
                filled = bool(slot_default(q, contract))
            if not filled:
                continue
            for bid in _render.filled_spanned_slots(contract, _res, _connectors(),
                                                    key, occupants):
                err(path, "L115", f"configurations/{cname}/occupants: {key!r} "
                    f"holds {q['ref']} filled, and so does its bore "
                    f"{key}/{bid} - one duplex connector fills both bores, so "
                    f"empty one level ({key}/{bid}: \"\", or {key}: \"\")")


def lint_device_placement_interfaces(path, data, lib_roots):
    """L105: a placement that presents several interfaces (#443).

    A CSFP cage carries two BiDi interfaces and declares them -
    `interfaces: [port-1, port-3]` - because the switch's silicon has both
    whether or not a module is seated. Three things can make that wrong, and
    each is a DCIM that lists the wrong ports:

    AN INTERFACE THAT IS ALSO A PLACEMENT OR BAY ID. The ECS4530's combo
    RJ-45s were `port-45`..`port-48` - exactly the ids its twelfth stack's
    CSFP interfaces needed. Both connectors are real and each needs its own
    name, so one of them has to be renamed; the export would otherwise write
    two interfaces under one name.

    ONE INTERFACE PRESENTED BY TWO PLACEMENTS - the same port counted twice.

    INTERFACES ON SOMETHING THAT IS NOT A PORT. A lamp or a bay filler does
    not present a switch interface, whatever its id says.
    """
    for vname, view in (data.get("views") or {}).items():
        comps = (view or {}).get("components") or {}
        placements = comps.get("placements") or []
        bays = comps.get("bays") or []
        ids = {p.get("id") for p in placements if p.get("id")} | {b.get("id") for b in bays if b.get("id")}
        owner = {}
        for p in placements:
            ifs = p.get("interfaces")
            if not ifs:
                continue
            ref = p.get("ref") or ""
            if _contract(ref, lib_roots).get("class") != "port":
                err(path, "L105", f"{vname}: {p.get('id')} presents interfaces {', '.join(ifs)} "
                                  f"but {ref} is not a port")
            for i in ifs:
                if i in ids:
                    err(path, "L105", f"{vname}: {p.get('id')} presents interface {i!r}, which is "
                                      f"also the id of a placement or bay in this view")
                if i in owner:
                    err(path, "L105", f"{vname}: interface {i!r} is presented by both "
                                      f"{owner[i]} and {p.get('id')}")
                owner.setdefault(i, p.get("id"))

def lint_device_cage_media_disagreement(path, data, lib_roots):
    """L104: a port's declared media and its cage's presented interface
    (`manifest.presented_interface`, looked through a wrapper's `parts:`
    exactly as render.py's `cages[]` does) name the SAME pluggable family.

    THE MEDIA IS READ FROM THE PLACEMENT FIRST, THEN ITS GROUP - L18's
    precedence, and render.py's `cage_entries` reads it the same way, so this
    rule reaches exactly the ports whose accept list that derivation governs.
    Reading only the group left a placement-declared media both unchecked
    here and, before the same fix in render.py, unserved there.

    render.py's `cages[].accepts` derivation found this, not a person: a
    QSFP-DD cage offers `generic/qsfp-dd-lc@1`, and a QSFP one offers
    `generic/qsfp-lc@1` (plus, on a QSFP-DD cage, the QSFP generic too,
    through `also-accepts`) - two different lists. A port declaring
    `media: qsfp-dd` while its placement is modelled with `std/qsfp-ganged@1`
    (a QSFP aperture, not a QSFP-DD one) asks for the QSFP-DD optic while
    presenting the QSFP shape, and nothing before this compared the two.

    THE DECLARED MEDIA GOVERNS the accept list (the maintainer's ruling, not derived):
    the media says what the port IS; the aperture says what it looks like,
    and for slotting an optic the former decides. render.py's cage
    derivation already applies that precedence - see `cage_entries` there.
    This rule does not change what gets offered; it flags the corpus fact so
    the modelling question - is the drawing's aperture wrong, or is the
    declared media wrong - stays visible instead of being silently settled by
    a precedence rule nobody sees.

    WARNING, NOT ERROR, the same way L103 is: QSFP-DD and QSFP share a face
    opening and differ mainly in depth, so the DRAWING may well be correct
    and the fix may belong in seven different datasheets, not in this rule.
    Seven separate modelling questions against seven sets of source documents is
    real work that accumulates device by device, which is L40's shape, not
    L102's.
    """
    groups = data.get("groups") or {}

    def _res(ref):
        p = resolve_component(ref, lib_roots)
        return load_yaml(p) if p else None

    for vname, view in sorted((data.get("views") or {}).items()):
        for p in view_parts(view or {})["placements"]:
            contract = _res(p.get("ref"))
            if not contract:
                continue
            interface, _at, _lift = presented_interface(contract, _res)
            if not interface:
                continue
            iface_found = _family_mated_by(interface)
            if iface_found is None:
                continue
            # THE PLACEMENT'S OWN MEDIA FIRST, then its group's - L18's
            # precedence (`:6583`), which render.py's `cage_entries` reads the
            # same way. Reading only the group made this rule blind at exactly
            # the ports that declare their media on the placement instead.
            media = ((p.get("attrs") or {}).get("media")
                     or ((groups.get(p.get("group")) or {}).get("attrs") or {}).get("media"))
            if not media:
                continue
            media_found = _family_owning_rate(media)
            if media_found is None:
                continue
            iface_name, _iface_fam = iface_found
            media_name, _media_fam = media_found
            if iface_name == media_name:
                continue
            # NAME WHERE THE MEDIA WAS READ FROM. Saying "group 'probe'
            # declares media qsfp-dd" of a port that declares it on the
            # placement sends the reader to a group that says nothing.
            where = ("the placement" if (p.get("attrs") or {}).get("media")
                     else f"group {p.get('group')!r}")
            warn(path, "L104",
                 f"{vname}/{p['id']}: {where} declares media "
                 f"{media!r} (the {media_name!r} family) but the placement's "
                 f"ref {p['ref']} presents interface {interface!r} (the "
                 f"{iface_name!r} family) - the declared media governs the "
                 f"accept list render.py's cages[] builds, so this port is "
                 f"offered {media_name!r} optics over a {iface_name!r}-shaped "
                 "aperture. Check the source: either the drawing needs the "
                 f"{media_name!r} cage, or the declared media is wrong")


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
            members.setdefault(g, []).append(
                _group_member(f"{vname}/{p['id']}", p, lib_roots))
    _judge_group_members(path, groups, members, err, warn)


def _group_member(where, p, lib_roots):
    """One port member of a group, as _judge_group_members reads it."""
    own = (p.get("attrs") or {}).get("media")
    return {"where": where, "declared-media": own,
            "media": own or (contract_attrs(p["ref"], lib_roots) or {}).get("media"),
            "declared-speed": (p.get("attrs") or {}).get("speed")}


def _judge_group_members(path, groups, members, e, w):
    """L22 and L23 over one manifest's groups and the port members gathered
    for them - a device's placements, or a component's parts (#511). `e` and
    `w` are the severities: a device reports L22 as an error, a component
    reports both as warnings while the library's cards are migrated."""
    for gname, gdef in groups.items():
        mem = members.get(gname) or []
        if not mem:
            continue
        gattrs = (gdef or {}).get("attrs") or {}
        gm, gs = gattrs.get("media"), gattrs.get("speed")
        # L22 - the promise against the members.
        for m in mem:
            if gm and m["media"] and media_family(m["media"]) != media_family(gm):
                e(path, "L22", f"{m['where']}: group {gname!r} declares media {gm!r}, "
                               f"but this port is {m['media']!r}. A group's attrs are "
                               f"merged into every member, so the drawing would call it "
                               f"{gm!r}")
            elif gm and m["declared-media"] and m["declared-media"] != gm \
                    and m["declared-media"] not in AMBIGUOUS_MEDIA:
                e(path, "L22", f"{m['where']}: group {gname!r} declares media {gm!r}, "
                               f"but this port declares {m['declared-media']!r}. Same "
                               f"cage, different media - one of the two is wrong")
            if gs and m["declared-speed"] and m["declared-speed"] != gs:
                e(path, "L22", f"{m['where']}: group {gname!r} declares speed {gs!r}, "
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
            w(path, "L23", f"groups/{gname}: {len(mem)} ports spanning more than one "
                           f"family ({found}), so the block can declare nothing in "
                           f"attrs and every port must repeat itself. Split it by "
                           f"family, or say in `mixed:` what job they do together")
        elif reason and not spans:
            w(path, "L23", f"groups/{gname}: declares mixed {reason!r}, but all "
                           f"{len(mem)} ports are {', '.join(sorted(medias)) or 'one family'}. "
                           f"`mixed:` states a fact about the hardware - drop it")


def lint_component_groups(path, data, lib_roots):
    """L17, L22, L23 and L37 on a COMPONENT's own `groups:` (#511).

    A card's ports join groups the card declares, and the renderer writes them
    exactly as it writes a device group onto a device placement - so the same
    four promises hold, read the same way:

      L17  a part's `group:` names a group this component declares; and, once a
           component declares any group, every PORT part joins one - a card
           half migrated would draw some of its ports with a role and the rest
           without, which reads as two kinds of port where there is one;
      L22  a group's declared media/speed agrees with the port parts it holds;
      L23  a port group is one family, or says in `mixed:` why it is not;
      L37  a group says what it is FOR, and a declared group has members.

    ALL WARNINGS, where L17 and L22 are errors on a device: 215 components
    carry port parts and almost none declare groups yet, so this is the debt
    stated and counted while they are migrated, not a gate. A component that
    declares no groups is silent - it has not been migrated, and that is
    not news.
    """
    groups = data.get("groups") or {}
    members, joined = {}, set()
    for part in data.get("parts") or []:
        if not isinstance(part, dict) or not part.get("ref"):
            continue
        g = part.get("group")
        is_port = contract_class(part["ref"], lib_roots) == "port"
        where = f"parts/{part.get('id')}"
        if g:
            joined.add(g)
            if g not in groups:
                warn(path, "L17", f"{where}: group {g!r} is not declared under the "
                                  "component's own groups:")
                continue
            if is_port:
                members.setdefault(g, []).append(_group_member(where, part, lib_roots))
        elif groups and is_port:
            warn(path, "L17", f"{where}: a port part in no group, on a component that "
                              f"declares groups ({', '.join(sorted(groups))}). Join it "
                              "to one, so every port on the card says what it is for")
    _judge_group_members(path, groups, members, warn, warn)
    for gid, gdef in groups.items():
        if not (gdef or {}).get("role"):
            warn(path, "L37", f"group {gid} does not say what it is for. Add "
                              "role: traffic|fabric|management|service|indicator|furniture")
        if gid not in joined:
            warn(path, "L37", f"group {gid} is declared and no part joins it. "
                              "Either place a part in it or drop it")


def _speed_finding(path, where, speed):
    """L110 for one declared speed. Nothing declared is not a finding - a port
    that says nothing about its rate is answered by its group or its cage."""
    if speed is None:
        return
    if str(speed) in PORT_SPEEDS:
        return
    err(path, "L110", f"{where}: speed {speed!r} is not in the closed set "
                      f"({' '.join(PORT_SPEEDS) or 'spec/schemas/speeds.yaml loaded nothing'}). "
                      "A speed is the highest native rate the port runs at; copper or "
                      "fibre is `media`, a USB generation is `usb`, a PON flavour is "
                      "`pon`, and a caveat belongs in the placement's `description`")


def lint_device_speed_vocabulary(path, data):
    """L110: every port speed a device declares is spelled from one closed set.

    `speed` flattens to data-speed on every port the renderer draws, so it is
    the attribute a filter selects on - "every 1G port" is one selector only if
    1G is spelled one way. It was spelled four ways (`100m-1g`, `1000base-t`,
    `100/1000base-t`, `10/100/1000`), and the DCIM exporter's table knew only
    two of them, so eight 1G copper ports on the CSR180 and CSR200 exported
    nothing at all (#512). Read on both of the places a device states it: a
    group's attrs, which the renderer merges into every member, and a
    placement's own.
    """
    for gname, gdef in (data.get("groups") or {}).items():
        _speed_finding(path, f"groups/{gname}",
                       attrs_mod.flatten((gdef or {}).get("attrs")).get("speed"))
    for vname, view in (data.get("views") or {}).items():
        for p in view_parts(view or {})["placements"]:
            _speed_finding(path, f"{vname}/{p.get('id')}",
                           attrs_mod.flatten(p.get("attrs")).get("speed"))


# L113's question: which media put a NETWORK INTERFACE behind the connector.
#
# NOT A NEW LIST. It is the two the tree already keeps: every pluggable cage
# L40 and L102 ask about (PLUGGABLE_CAGES, which test_pluggable_ladder.py holds
# to spec/schemas/pluggables.yaml), and every media the DCIM exporter's
# PART_MEDIA table types as an interface rather than `other` - which is how
# plain `rj45` gets in and `rj45-telemetry` stays out. A medium on neither list
# is not asked: `rj45-serial`, `rj45-tod`, `rj48`, `usb-a`, `coax-smb`, a bonded
# `fiber` adapter. So the fix for a timing or console jack that trips this rule
# is to name what it carries in `media`, not to give it a speed it does not have.
INTERFACE_MEDIA = frozenset(
    PLUGGABLE_CAGES
    | {m for (m, _s), t in dcim_export.PART_MEDIA.items() if t != "other"})


def lint_device_port_rate(path, data, lib_roots):
    """L113: a device's network port says what rate it runs at and what its
    group is for (#511).

    A port's effective media - its own attrs over its group's, then the part's
    own - decides whether it is asked. If that media carries an interface
    (INTERFACE_MEDIA), the port must end up with a `speed` (its own or its
    group's) and a group with a `role`. `speed` is what `[data-speed]`
    selects on and what the exporter types an interface from; a port without
    one is invisible to the first and GUESSED by the second - `iface_type`
    falls back to 25G for any SFP, which exported the ASR 9001's two 10G
    cluster ports and three Smartoptics OSC cages as SFP28.

    DEVICE LEVEL ONLY. It reads a view's placements - the ports the device
    places itself. The inner parts of a composed port (`--jack`, `--cage`) are
    a component's `parts:` and never appear here, and the ports on a module
    seated in a bay belong to the module's contract, whose groups are #511's
    component half.

    WARNING AT `modelled`, ERROR AT `verified` - L37's gate, and for L37's
    reason. The library cannot be driven to zero honestly: a vendor that
    publishes no rate for a management jack or a probe port has given nothing
    to write, and inventing one is the defect this rule exists to prevent. A
    device claiming `verified` has to have found the rate or stopped claiming.
    """
    groups = data.get("groups") or {}
    loud = err if data.get("maturity") == "verified" else warn
    for vname, view in sorted((data.get("views") or {}).items()):
        for p in view_parts(view or {})["placements"]:
            ref = p.get("ref")
            if not ref or contract_class(ref, lib_roots) != "port":
                continue
            gdef = groups.get(p.get("group")) or {}
            a = {**attrs_mod.flatten(gdef.get("attrs")), **attrs_mod.flatten(p.get("attrs"))}
            media = a.get("media") or attrs_mod.flatten(contract_attrs(ref, lib_roots)).get("media")
            if media not in INTERFACE_MEDIA:
                continue
            lacks = []
            if not a.get("speed"):
                lacks.append("no `speed`")
            if not gdef.get("role"):
                lacks.append("no group" if not p.get("group") else
                             f"group {p.get('group')!r} has no `role`")
            if lacks:
                loud(path, "L113", f"{vname}/{p.get('id')}: a {media} port with "
                     f"{' and '.join(lacks)}. Give it the rate the source states "
                     "(or its group's), or - if it is a console, timing or alarm "
                     "jack - the media that says so (`rj45-serial`, `rj45-tod`, "
                     "`rj48`); where no document states a rate, leave it and "
                     "record the search in `gaps:`")


def lint_component_speed_vocabulary(path, data):
    """L110 for a component: its own `attrs.speed`, each of its own groups'
    (#511 - the renderer merges a component group's attrs into every part in
    it, exactly as it does a device group's), and each composed part's.

    A contract that declares `speed` among its `fields` is exempt at the top
    level, because there the value is something printed on the part - the DIMM
    sticker's MT/s - and not a port rate. Its groups and parts are still read.
    """
    if "speed" not in (data.get("fields") or {}):
        _speed_finding(path, "attrs", attrs_mod.flatten(data.get("attrs")).get("speed"))
    for gname, gdef in (data.get("groups") or {}).items():
        _speed_finding(path, f"groups/{gname}",
                       attrs_mod.flatten((gdef or {}).get("attrs")).get("speed"))
    for part in data.get("parts") or []:
        if isinstance(part, dict):
            _speed_finding(path, f"parts/{part.get('id')}",
                           attrs_mod.flatten(part.get("attrs")).get("speed"))


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


def _path_box(mark):
    """Bounding box of a `path:` mark, relative to its own `at`.

    Only M/L/Z with absolute coordinates, which is all this library uses and all
    the marks generator emits. Anything with a curve or a relative command is
    skipped rather than guessed at.
    """
    d = str(mark.get("path") or "")
    if re.search(r"[aAcCqQsStTvVhH]", d):
        return None
    nums = [float(t) for t in re.findall(r"-?\d+(?:\.\d+)?", d)]
    if len(nums) < 4 or len(nums) % 2:
        return None
    xs, ys = nums[0::2], nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _mark_centre(mark):
    """Where a silkscreen mark's ink actually sits, as (cx, cy) or None."""
    at = mark.get("at")
    if not at:
        return None
    if mark.get("path"):
        box = _path_box(mark)
        if not box:
            return None
        return at[0] + (box[0] + box[2]) / 2, at[1] + (box[1] + box[3]) / 2
    if mark.get("text") is None:
        return None
    x0, y0, x1, y1 = _text_extent(mark)
    return (x0 + x1) / 2, (y0 + y1) / 2


_ID_VOCAB_CACHE = {}

# L62'S VOCABULARY, KEPT ON DISK BETWEEN PROCESSES (#542).
#
# `_id_corpus` reads every contract and every device manifest in the library,
# and build.sh renders each device in its own process - so that read was paid
# once per device, and it was ~95% of a render (5.9 s of a 6.5 s `render.py`;
# the drawing is 0.1 s). The answer is now written to a file named for a digest
# of the bytes it was computed from, and the next process reads that instead.
#
# KEYED ON CONTENT, NEVER ON MTIMES. A stale vocabulary does not fail loudly:
# it silently hides a real L62 finding (or invents one), and nothing downstream
# can tell. An mtime key can go stale - a checkout that restores an old
# timestamp, a coarse-grained filesystem, two edits inside one tick, a copy
# that preserves times - and every one of those would serve the old answer. A
# digest of every byte `_id_corpus` reads cannot: if any input differs, the
# name differs and the entry is simply never found. The compute reads the SAME
# bytes that were hashed (not a second read through load_yaml's (path, mtime)
# cache), so what is stored under a digest is exactly what those bytes say.
#
# THE CODE IS AN INPUT TOO, SO THE BYTES OF THIS FILE ARE IN THE DIGEST. An
# entry computed by older logic must never answer for newer logic, and a
# hand-bumped version constant is exactly the guard that gets forgotten. The
# WHOLE of lint.py is hashed rather than `_id_corpus_compute`'s source, because
# the answer also depends on helpers and constants elsewhere in the module and a
# whole-file hash cannot miss one. The price is one recompute per lint.py edit.
# The bytes are read ONCE, when this module is imported, so the digest names
# the code this process actually loaded: a long-lived process - the tests'
# warm render server, say - whose lint.py is edited on disk behind it keeps
# computing with the OLD code, and must keep keying its entries as the old
# code too.
#
# _ID_CORPUS_CACHE_FORMAT is for the SERIALISED SHAPE only: bump it when what
# `_id_corpus_cache_store` writes, or what `_id_corpus_cache_load` accepts,
# changes. It is in the digest as well, so a bump turns every old entry into a
# miss.
#
# ANY FAILURE ON THE CACHE PATH FALLS BACK TO COMPUTING: an unwritable or
# missing directory, a corrupt or truncated file, a JSON error, a race. The
# cache is an optimisation and is never allowed to be a reason to fail.
_ID_CORPUS_CACHE_FORMAT = 1
_ID_CORPUS_CACHE_KEEP = 50          # entries kept; the oldest by mtime go first


def _source_sha(path):
    """sha256 of a source file's bytes, or None if it cannot be read - in which
    case the digest raises and the cache is simply not used."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


_ID_CORPUS_CODE = _source_sha(__file__)   # this module as loaded; see above
_ID_CORPUS_TMP_MAX_AGE = 3600       # seconds before a stray temp file is an orphan


def _id_corpus_cache_dir():
    """$PORTRAYAL_CACHE_DIR, else $XDG_CACHE_HOME/portrayal, else
    ~/.cache/portrayal. Never inside the checkout or dist/.

    A RELATIVE value is ignored and the next option is used - the XDG spec says
    so for XDG_CACHE_HOME, and PORTRAYAL_CACHE_DIR gets the same treatment,
    because a relative path resolves against the cwd, which for build.sh and
    the tests is the checkout itself."""
    env = os.environ.get("PORTRAYAL_CACHE_DIR")
    if env and Path(env).is_absolute():
        return Path(env)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg and Path(xdg).is_absolute():
        return Path(xdg) / "portrayal"
    return Path.home() / ".cache" / "portrayal"


def _id_corpus_roots_cacheable(lib_roots):
    """Whether the digest determines the answer for these roots. It does only
    when no two roots overlap. The veto in `_id_corpus_compute` counts DISTINCT
    file paths, and the digest keys on root position and relative path, not on
    absolute paths - so [A, A] and [A, B], with B a byte-identical copy of A,
    hash the same and answer differently (the same two files twice, against
    four). A repeated root, or one inside another, is computed and not cached."""
    try:
        rs = [Path(r).resolve() for r in lib_roots]
    except Exception:
        return False
    for i, a in enumerate(rs):
        for j, b in enumerate(rs):
            if i != j and (a == b or a in b.parents):
                return False
    return True


def _id_corpus_files(lib_roots):
    """Every file `_id_corpus` reads, with its bytes, in the order it reads
    them: (section, root index, path relative to root/section, path, bytes,
    sha256 of the bytes). Bytes and hash are None for a file that vanished
    between the walk and the read - load_yaml answered None for that too, and
    the computation treats it as the empty document it always did."""
    files = []
    for section, pattern in (("components", "contract.yaml"), ("devices", "*.yaml")):
        for n, root in enumerate(lib_roots):
            base = Path(root) / section
            for f in base.rglob(pattern):
                try:
                    data = f.read_bytes()
                except FileNotFoundError:
                    data = None
                sha = hashlib.sha256(data).hexdigest() if data is not None else None
                files.append((section, n, f.relative_to(base).as_posix(), f, data, sha))
    return files


def _id_corpus_section(files, section):
    """(path, bytes, hash) for one section, roots in order - the order the two
    loops in `_id_corpus_compute` always walked them in."""
    return [(f, data, sha) for s, _n, _rel, f, data, sha in files if s == section]


_ID_CORPUS_PARSES = 0              # files parsed by this process, for the trace


def _id_corpus_parse(data):
    """One file's document: the parser load_yaml uses, on the hashed bytes."""
    global _ID_CORPUS_PARSES
    _ID_CORPUS_PARSES += 1
    return yaml.load(data, Loader=_manifest._Loader)


def _id_corpus_trace(outcome, lib_roots, files, parsed0, t0):
    """One JSON line per computation to $PORTRAYAL_ID_CORPUS_TRACE, if set:
    whether the disk cache hit, how many files there were and how many had to
    be parsed. How a slow build or suite shows which processes paid for the
    vocabulary; never a reason to fail."""
    path = os.environ.get("PORTRAYAL_ID_CORPUS_TRACE")
    if not path:
        return
    with contextlib.suppress(Exception):
        line = json.dumps({
            "pid": os.getpid(), "argv0": Path(sys.argv[0]).name if sys.argv else "",
            "roots": [str(r) for r in lib_roots], "outcome": outcome,
            "files": len(files), "parsed": _ID_CORPUS_PARSES - parsed0,
            "secs": round(time.monotonic() - t0, 3)}) + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line.encode())
        finally:
            os.close(fd)


def _id_corpus_doc(data):
    return (_id_corpus_parse(data) if data is not None else None) or {}


# WHAT EACH FILE CONTRIBUTES, MEMOISED BY THE HASH OF ITS BYTES. A cache miss
# used to parse every file from bytes, including the ~860 of the real library
# that nearly every test render shares with a tmp root beside it - where
# before this cache existed, those came free from load_yaml's per-process
# parse. This memo gives that back without giving up the purity the disk
# cache rests on: its key is the content hash the digest already computes, so
# it cannot go stale (a changed file IS a different key), and what it holds is
# exactly what `_id_corpus_compute` reads off a document - nothing about any
# device or rule outcome. `_id_corpus_prime` fills it, which is what the
# tests' warm render server does once so that its forked children parse only
# the files a test wrote.
_ID_CORPUS_FACTS = {}


def _id_corpus_facts(section, data, sha):
    """What one file contributes to the vocabulary, from its bytes:

      components - the values offered as connector words, in order: its
                   `conforms`, then `attrs.media` when its class is `port`;
      devices    - every string placement id, in order, or nothing for a
                   document that is not a device.

    Memoised in _ID_CORPUS_FACTS by (section, sha256 of the bytes)."""
    if data is None:
        return ()
    key = (section, sha)
    hit = _ID_CORPUS_FACTS.get(key)
    if hit is not None:
        return hit
    doc = _id_corpus_doc(data)
    out = []
    if section == "components":
        if doc.get("conforms"):
            out.append(str(doc["conforms"]))
        if doc.get("class") == "port":
            media = (doc.get("attrs") or {}).get("media")
            if media:
                out.append(str(media))
    elif doc.get("kind") in (None, "device"):
        for view in (doc.get("views") or {}).values():
            for q in (((view or {}).get("components") or {}).get("placements") or []):
                i = q.get("id")
                if isinstance(i, str):
                    out.append(i)
    facts = _ID_CORPUS_FACTS[key] = tuple(out)
    return facts


def _id_corpus_prime(lib_roots):
    """Fill the per-file memo for `lib_roots` and nothing else: no answer is
    computed, no in-process or disk entry is written."""
    for section, _n, _rel, _f, data, sha in _id_corpus_files(lib_roots):
        _id_corpus_facts(section, data, sha)


def _id_corpus_digest(files):
    """sha256 over the cache format, the bytes of the source that computes the
    answer (_ID_CORPUS_CODE: lint.py, as imported), and for every library file its root's
    position, its path relative to that root's section and a hash of its bytes
    - sorted, so the directory walk's order does not matter, and without the
    roots' absolute paths, so every checkout of the same commit shares one
    entry. An unreadable source raises, and the caller then computes without
    the cache."""
    code = _ID_CORPUS_CODE
    if code is None:
        raise OSError("lint.py's source could not be read at import")
    rows = []
    for section, n, rel, _f, _data, sha in files:
        rows.append(f"{n}\0{section}\0{rel}\0{sha or 'missing'}\n")
    rows.sort()
    # the parser is part of the computation too: a different PyYAML, or the
    # pure-Python loader where libyaml is missing, could read a document
    # differently, so neither may reuse the other's entries
    parser = f"{yaml.__version__}\0{_manifest._Loader.__name__}"
    top = hashlib.sha256(
        f"portrayal-id-corpus\0{_ID_CORPUS_CACHE_FORMAT}\0code\0{code}\0"
        f"parser\0{parser}\n".encode())
    for r in rows:
        top.update(r.encode("utf-8", "surrogateescape"))
    return top.hexdigest()


def _id_corpus_cache_load(path, digest):
    """The cached (words, preferred, whole), rebuilt as exactly the types
    `_id_corpus_compute` returns - or None if the entry is missing, unreadable,
    or anything other than what `_id_corpus_cache_store` writes for `digest`."""
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
        if (not isinstance(doc, dict) or doc.get("format") != _ID_CORPUS_CACHE_FORMAT
                or doc.get("digest") != digest):
            return None
        raw_words, raw_pref, raw_whole = doc["words"], doc["preferred"], doc["whole"]
        if not (isinstance(raw_words, list) and isinstance(raw_whole, list)
                and isinstance(raw_pref, list)):
            return None
        if not all(type(w) is str for w in raw_words + raw_whole):
            return None
        preferred = {}
        for row in raw_pref:
            if not (isinstance(row, list) and len(row) == 3 and type(row[0]) is str
                    and type(row[1]) is int and type(row[2]) is str):
                return None
            preferred[row[0]] = (row[1], row[2])
        if len(preferred) != len(raw_pref):
            return None
        return set(raw_words), preferred, set(raw_whole)
    except Exception:
        return None


def _id_corpus_cache_store(cache_dir, digest, result):
    """Write the entry atomically - a temp file in the same directory, then
    os.replace - so a reader sees the whole file or none. Two processes racing
    write the same bytes under the same name, and the second replace is
    harmless. Then prune to the newest _ID_CORPUS_CACHE_KEEP entries. Every
    failure is swallowed: not caching is always a correct outcome."""
    words, preferred, whole = result
    payload = json.dumps({
        "format": _ID_CORPUS_CACHE_FORMAT,
        "digest": digest,
        "words": sorted(words),
        # a list of rows rather than an object, so the dict's key order - which
        # is what a fresh computation would have produced - survives the trip
        "preferred": [[k, n, lead] for k, (n, lead) in preferred.items()],
        "whole": sorted(whole),
    }, separators=(",", ":"))
    tmp = None
    try:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=cache_dir, prefix=".id-corpus-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, cache_dir / f"id-corpus-{digest}.json")
        tmp = None
    except Exception:
        return
    finally:
        if tmp is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
    with contextlib.suppress(Exception):
        aged = []
        for e in cache_dir.glob("id-corpus-*.json"):
            with contextlib.suppress(OSError):
                aged.append((e.stat().st_mtime, e.name, e))
        aged.sort(reverse=True)
        for _m, _n, e in aged[_ID_CORPUS_CACHE_KEEP:]:
            with contextlib.suppress(OSError):
                e.unlink()
        # a writer killed between mkstemp and os.replace leaves its temp file;
        # one old enough that no live writer can still own it is an orphan
        cutoff = time.time() - _ID_CORPUS_TMP_MAX_AGE
        for t in cache_dir.glob(".id-corpus-*.tmp"):
            with contextlib.suppress(OSError):
                if t.stat().st_mtime < cutoff:
                    t.unlink()


def _id_corpus(lib_roots):
    """What this library calls things - the two facts L62 needs, read off the
    corpus itself rather than written down here. Returns (connector words, the
    name the corpus prefers for a given id tail).

    THE CONNECTOR WORDS.

    Not a list written here. A hardcoded list would be shaped like the examples
    that prompted the rule - sma, rj45 - and would say nothing about the next
    form factor someone adds. So the vocabulary is whatever the corpus already
    calls a physical standard:

      * every `conforms:` value, which is exactly the field a component uses to
        name the standard it is built to, and
      * every slug-shaped `attrs.media` value on a component whose `class` is
        `port`.

    The class filter is what keeps FUNCTION words out. `common/esd-jack` states
    `media: esd` and `std/c14-inlet` states `media: ac`, and neither is a
    connector: esd is what the jack is FOR and ac is what comes down the cord.
    They are classed `ground` and `inlet`, so they never enter the vocabulary,
    and `esd-jack` and `ac-inlet-panel` stay quiet - which they should, because
    both of those ids name a function.

    Each standard also contributes its leading segment, because that is the
    level an id borrows at: `sfp-plus-3` borrows from `sfp`, `micro-usb` from
    `micro-usb-b`, `qsfp-0` from `qsfp-dd`.
    """
    key = tuple(str(r) for r in lib_roots)
    if key in _ID_VOCAB_CACHE:
        return _ID_VOCAB_CACHE[key]
    t0, parsed0 = time.monotonic(), _ID_CORPUS_PARSES
    files = _id_corpus_files(lib_roots)
    try:
        if not _id_corpus_roots_cacheable(lib_roots):
            raise ValueError("overlapping roots: the digest does not determine the answer")
        digest = _id_corpus_digest(files)
        cache_dir = _id_corpus_cache_dir()
        hit = _id_corpus_cache_load(cache_dir / f"id-corpus-{digest}.json", digest)
    except Exception:          # the cache is an optimisation, never a reason to fail
        digest, hit = None, None
    if hit is not None:
        # touched, so pruning drops the least recently USED entries
        with contextlib.suppress(OSError):
            os.utime(cache_dir / f"id-corpus-{digest}.json")
        _ID_VOCAB_CACHE[key] = hit
        _id_corpus_trace("hit", lib_roots, files, parsed0, t0)
        return hit
    result = _id_corpus_compute(files)
    # a file that vanished mid-walk is a tree being changed under us: answer
    # from what was read, as before, but do not record it for anyone else
    if digest is not None and all(data is not None for *_, data, _sha in files):
        _id_corpus_cache_store(cache_dir, digest, result)
    _ID_VOCAB_CACHE[key] = result
    _id_corpus_trace("miss" if digest is not None else "uncached", lib_roots, files,
                     parsed0, t0)
    return result


def _id_corpus_compute(files):
    """L62's vocabulary from the files `_id_corpus_files` read - the logic
    `_id_corpus` describes. A pure function of those bytes, which is what lets
    the answer be cached under a digest of them."""
    slug = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
    words = set()

    def offer(value):
        v = str(value)
        if slug.match(v):
            words.add(v)
            head = v.split("-")[0]
            if head != v:
                words.add(head)

    for _f, data, sha in _id_corpus_section(files, "components"):
        for value in _id_corpus_facts("components", data, sha):
            offer(value)

    # AND THEN THE CORPUS GETS A VETO. A word that devices already use as a
    # COMPLETE id is a function name in this library whatever else it is: `usb`
    # is the name of the service a USB-A receptacle provides, and it stands
    # alone as an id on dozens of devices. Firing on `usb-1` would be the rule
    # arguing with the convention it was written to state. Three devices, so
    # that one sloppy file cannot silence a word everywhere.
    bare, tails, whole_ids = {}, {}, {}
    for f, data, sha in _id_corpus_section(files, "devices"):
        for i in _id_corpus_facts("devices", data, sha):
            if i in words:
                bare.setdefault(i, set()).add(str(f))
            whole_ids[i] = whole_ids.get(i, 0) + 1
            # every way this id divides into <lead>-<tail>, which is how
            # the preferred name below is looked up
            t = i.split("-")
            for k in range(1, len(t)):
                c = tails.setdefault("-".join(t[k:]), {})
                c["-".join(t[:k])] = c.get("-".join(t[:k]), 0) + 1
    words -= {w for w, where in bare.items() if len(where) >= 3}

    # THE PREFERRED NAME. What does the library already call the thing on the
    # other end of `smb-10mhz-out`? It calls it `clk-10mhz-out`, on three
    # placements, and `clk-10mhz` on twenty-one more - the vote was taken before
    # this rule existed. So for each id tail, the commonest lead that is NOT a
    # connector word is the function name the corpus settled on, and the warning
    # can hand that back instead of leaving an agent to invent one. Two
    # placements minimum: one is a precedent of nothing.
    # A QUALIFIER MUST NOT SPLIT THE VOTE. Counting only the EXACT tail made
    # `1pps` and `1pps-in` two separate questions with two different answers:
    # the library says `clk-1pps` twenty-one times, but the only ids ending
    # `1pps-in` were two on a single device added last week, so that device won
    # its tail unopposed and the rule told every Juniper modeller to write
    # `timing-1pps-in`. A vote in which the newest file always wins its own
    # spelling is not a vote; it is an echo, and it would have split the corpus
    # permanently along whichever vendor was modelled first.
    #
    # So a lead is credited with what it is called in front of this tail AND in
    # front of the tail this one qualifies - `1pps-in` is a directional `1pps`.
    # `clk` then carries 21 against `timing`'s 2 and the suggestion is
    # `clk-1pps-in`, which is both the library's word and this port's direction.
    def votes_for(tail):
        agg, parts = {}, tail.split("-")
        for k in range(len(parts), 0, -1):
            for lead, n in tails.get("-".join(parts[:k]), {}).items():
                if lead not in words:
                    agg[lead] = agg.get(lead, 0) + n
        return agg

    preferred = {}
    for tail in tails:
        best = max(((n, lead) for lead, n in votes_for(tail).items()), default=None)
        if best and best[0] >= 2:
            preferred[tail] = best

    # AND WHAT COUNTS AS A NAME AT ALL. `sfp-leds` leaves `leds` once its
    # connector is taken off, and with nothing voting on that tail the rule used
    # to hand back the bare remainder - so it proposed renaming a lamp pair to
    # `leds`, which names no function, duplicates the group it is already in,
    # and is worse than the id it replaces. A remainder is only offerable if the
    # library uses it as a whole id somewhere, which is what makes it a name
    # rather than a leftover.
    whole = {i for i, n in whole_ids.items() if n >= 2}
    return words, preferred, whole


def _contract(ref, lib_roots):
    """The whole contract behind a ref, or {}. load_yaml caches by path, so the
    repeat asks below cost a dict lookup."""
    try:
        f = resolve_component(ref, lib_roots)
    except ValueError:          # a ref with no @major - L5 reports that itself
        return {}
    return (load_yaml(f) or {}) if f else {}


def _states_connector(ref, placement, lib_roots):
    """Every connector word this placement's own `ref:` already states - from the
    component's name, its `conforms:`, and the media on either the contract or
    the placement. The id can only be duplicating something that is written
    down somewhere else, and this is that somewhere else."""
    stated = set()
    base = ref.split("@")[0].split("/")[-1]
    stated.add(base)
    stated.update(base.split("-"))
    c = _contract(ref, lib_roots)
    for value in (c.get("conforms"), (c.get("attrs") or {}).get("media"),
                  (placement.get("attrs") or {}).get("media")):
        if value:
            stated.add(str(value))
            stated.update(str(value).split("-"))
    return stated


def lint_device_face_bindings(path, data, lib_roots):
    """L63: a configuration binds each face to a view that draws that face.

    The binding is what makes an impossible front/rear pairing unrepresentable -
    a configuration names both faces at once, so a front and a rear that do not
    go together on real hardware cannot both be listed. A binding that names
    nothing is therefore worse than no binding: it reads as though the coupling
    is declared, and the renderer quietly falls back to the view named after the
    face.
    """
    views = data.get("views") or {}
    for cname, cfg in (data.get("configurations") or {}).items():
        for face, vname in ((cfg or {}).get("views") or {}).items():
            if vname not in views:
                err(path, "L63", f"configuration {cname} binds {face} to view "
                                 f"{vname!r}, which does not exist")
                continue
            draws = (views[vname] or {}).get("face") or vname
            if draws != face:
                err(path, "L63", f"configuration {cname} binds {face} to view "
                                 f"{vname!r}, which draws {draws}. A face can "
                                 "wear several panels; it cannot wear another "
                                 "face's")
    # A VARIANT NOTHING BINDS NEVER DRAWS. A warning and not an error - it may
    # be work in progress - but silence would leave a whole panel in the file
    # unreachable, which is the failure this rule exists to make visible.
    bound = {v for cfg in (data.get("configurations") or {}).values()
             for v in ((cfg or {}).get("views") or {}).values()}
    for vname, v in views.items():
        if (v or {}).get("face") and vname not in bound:
            warn(path, "L63", f"view {vname!r} declares face "
                              f"{(v or {}).get('face')} and no configuration "
                              "binds it, so it is never drawn")


# THE RJ45 FAMILY IS TWO BARE PARTS AND TWO LAMPED ONES (docs/rj45-family-design.md).
# Which a placement takes is decided by what the jack is FOR, and the test is the
# one sweep_jack_lamps.py already applied: a console, aux, serial, timing or
# telemetry jack carries no link lamp; everything else that is Ethernet does.
# The long words stand unanchored (a substring match is enough - nothing else
# in an id/role/group legitimately contains "console"). The short tokens -
# Juniper's "con" console abbreviation, "clk" for an external clock, "ptp" for
# a grandmaster, and a bare "tod" not already caught by the old (^|-)tod($|-) -
# are anchored on whitespace or a hyphen so they cannot fire inside an
# unrelated word (e.g. "contact", "oob", "eth-lan").
RJ45_BARE = re.compile(
    r"console|aux|serial|ioioi|telemetry|timing"
    r"|(^|[\s-])(con|tod|clk|bits|pps|sync|ptp|1588|ics"
    r"|t1|e1|ds1|rj48|che1)([\s-]|$)", re.I)
RJ45_LAMPED_REFS = {"common/rj45-eth@1", "common/rj45-ganged-eth@1"}
RJ45_BARE_REFS = {"std/rj45@2", "std/rj45-ganged@2"}
# A carrier that draws nothing and exists to attach one vendor's meanings
# (dell/rj45-port-14g) is the family member it composes, for census purposes;
# and the family's own members compose each other by definition, so a contract
# that IS one of them is not making a jack choice and is not censused.
RJ45_FAMILY_DIRS = {("std", "rj45"), ("std", "rj45-ganged"),
                    ("common", "rj45-eth"), ("common", "rj45-ganged-eth"),
                    ("dell", "rj45-port-14g")}


def rj45_class(ref, lib_roots, depth=0):
    """'lamped', 'bare' or 'retired' for an RJ45-ish ref, following one carrier."""
    if ref in RJ45_LAMPED_REFS:
        return "lamped"
    if ref in RJ45_BARE_REFS:
        return "bare"
    if depth > 2:
        return "retired"
    try:
        cp = resolve_component(ref, lib_roots)
    except ValueError:
        return "retired"
    if not cp:
        return "retired"
    for sub in ((load_yaml(cp) or {}).get("parts") or []):
        sref = str((sub or {}).get("ref") or "")
        if "rj45" in sref:
            return rj45_class(sref, lib_roots, depth + 1)
    return "retired"


def rj45_wants_lamps(q, groups, name=None):
    """True when this RJ45 placement is an Ethernet jack, by id, role, group,
    media - and, inside a component's `parts:`, the contract's own name.

    MEDIA IS PART OF THE TEXT because it is where half the corpus says what the
    jack is: `media: rj45-serial` and `media: rj45-telemetry` classify themselves,
    and reading only id/role/group made eleven Casa and Cisco jacks look Ethernet.
    THE CONTRACT NAME IS PART OF IT for a card whose ports are named `port-*` by
    the vendor's numbering and are not Ethernet at all - `spa-8xcht1-e1` and
    `mic-3d-16che1-t1-ce` are channelized T1/E1 cards whose RJ48c jacks carry DS1.
    The mechanical `port-*` rule swept 48 of those onto the lamped part and
    invented two lamps each (#125 review C1); the card's own name is the only
    place on a `parts:` entry that says otherwise."""
    ga = (groups.get(q.get("group")) or {}).get("attrs") or {}
    attrs = {**ga, **(q.get("attrs") or {})}
    role = str(attrs.get("role") or "")
    media = str(attrs.get("media") or "")
    text = f"{q.get('id')} {role} {q.get('group') or ''} {media} {name or ''}"
    return not RJ45_BARE.search(text)


def _rj45_census(placements, groups, lib_roots, name=None):
    """Count the RJ45 placements in one list that disagree with the family's rule.

    Shared by the device path (a view's `components.placements`) and the component
    path (a contract's `parts:`), because 368 of the library's 762 RJ45 placements
    sit inside component contracts and the census that could not see them is how
    C1 got in (#125 review I5)."""
    unlamped_eth = lamped_bare = retired = 0
    # A jack on a bare ref is not "on a part with no lamps" if this view
    # draws a `class: led` placement `for:` it beside the jack instead of
    # inside it - sweep_rj45.py leaves such a jack bare on purpose
    # (edgecore/as5912-54x mgmt-eth: two lamps drawn beside the bezel, not
    # composed into it), and the census must not re-flag what the sweep
    # deliberately left alone. The same exemption covers a BARE timing jack
    # whose vendor draws lamps for it (juniper/mx204's bits): the family has
    # no bare-with-lamps member, so the lamps stay separate placements.
    lamped_for = set()
    for q in placements:
        ref = str(q.get("ref") or "")
        if not ref:
            continue
        try:
            cp = resolve_component(ref, lib_roots)
        except ValueError:          # malformed ref with no @major - L5 reports that itself
            continue
        if cp and (load_yaml(cp) or {}).get("class") == "led":
            f = q.get("for")
            lamped_for.update(str(x) for x in (f if isinstance(f, list) else [f]) if x is not None)
    for q in placements:
        ref = str(q.get("ref") or "")
        if "rj45" not in ref:
            continue
        cls = rj45_class(ref, lib_roots)
        if cls == "retired":
            retired += 1
            continue
        if rj45_wants_lamps(q, groups, name):
            if cls != "lamped" and str(q.get("id")) not in lamped_for:
                unlamped_eth += 1
        elif cls != "bare":
            lamped_bare += 1
    return unlamped_eth, lamped_bare, retired


RJ45_CENSUS_MSG = ("An Ethernet jack is common/rj45-eth@1 or common/rj45-ganged-eth@1; "
                   "a console or timing jack is std/rj45@2 or std/rj45-ganged@2 "
                   "(docs/rj45-family-design.md; spec/tools/sweeps/sweep_rj45.py)")


def lint_device_rj45_lamps(path, data, lib_roots):
    """L76: the RJ45 census. Nine components once answered 'does this jack have
    lamps' five different ways (#125, #80). A census rule fires on the day it
    lands and shrinks to zero as the sweeps go through; what it stops is the
    sixth way arriving quietly."""
    groups = data.get("groups") or {}
    unlamped_eth = lamped_bare = retired = 0
    for view in (data.get("views") or {}).values():
        placements = (((view or {}).get("components") or {}).get("placements") or [])
        a, b, c = _rj45_census(placements, groups, lib_roots)
        unlamped_eth += a; lamped_bare += b; retired += c
    if unlamped_eth or lamped_bare or retired:
        warn(path, "L76", f"RJ45 family: {unlamped_eth} Ethernet jack(s) on a part with no "
                          f"lamps, {lamped_bare} console/timing jack(s) on a lamped part, "
                          f"{retired} on a retired RJ45 part. " + RJ45_CENSUS_MSG)


def lint_component_rj45_lamps(path, data, lib_roots):
    """L76 over a component contract's `parts:` - the other half of the census.

    A line card's RJ45s are `parts:` entries, not view placements, and until
    #125's final review nothing counted them. Half the library's jacks live here."""
    try:
        d = Path(path).parent.parent
        if (d.parent.name, d.name) in RJ45_FAMILY_DIRS:
            return
    except (ValueError, IndexError):
        pass
    unlamped_eth, lamped_bare, retired = _rj45_census(
        data.get("parts") or [], {}, lib_roots, data.get("name"))
    if unlamped_eth or lamped_bare or retired:
        warn(path, "L76", f"RJ45 family: {data.get('name')} parts: carry {unlamped_eth} "
                          f"Ethernet jack(s) on a part with no lamps, {lamped_bare} "
                          f"console/timing jack(s) on a lamped part, {retired} on a "
                          f"retired RJ45 part. " + RJ45_CENSUS_MSG)


def lint_device_id_convention(path, data, lib_roots):
    """L62: an id that names its connector, and a port lamp spelled a fourth way.

    Written after the same device was modelled twice, by two agents who agreed
    on the chassis to the millimetre and on all nine group names and diverged
    on NAMES: `clk-10mhz-out` against `sma-10mhz-out`. Neither was careless.
    Nothing in the library told either of them which to pick, so the diff
    between two correct models read larger than the disagreement was.

    THE RULE: AN ID NAMES THE FUNCTION, NOT THE CONNECTOR. The connector is
    already in `ref:`, and putting it in the id states one fact twice - so the
    day the part changes, the id lies. Exactly the failure a cutout has when it
    restates an aperture instead of deriving it.

    The corpus voted for this before the rule existed: 2326 `port-N`; timing
    jacks named `clk-10mhz`, `clk-1pps`, `tod`, `gnss-ant`, `bits` for what
    they carry rather than for the SMA or SMB they carry it through; singletons
    at `reset`, `usb`, `console`; lamps at `led-fan`, `led-sys`, `led-psN`.

    TWO THINGS ARE REPORTED AND NOTHING ELSE.

    1. An id whose leading segment repeats a connector word its own ref already
       states, with something else following it - `sma-10mhz-out`, `smb-1pps-in`,
       `sfp-plus-3`. A bare `usb` or `micro-usb-b`-shaped id that is ONLY the
       standard is left alone: it has no function half to keep, and renaming it
       is a different decision from de-duplicating one.

    2. A port lamp not spelled `led-port-N`. The library spells this four ways
       (led-port-N, led-pN, leds-port-N, leds-pN) and the plurality wins.

    Namespace choice - `edgecore/qsfpdd-lane-leds` against
    `common/qsfp-dd-lane-column` - is the other half of that divergence and is
    NOT here. Whether a four-lamp column beside a cage is Edgecore-specific is a
    judgement about the part, and every mechanical proxy for it (used by one
    vendor, so far) is a fact about the corpus today rather than about the part.

    BOTH ARE WARNINGS. The lamp check alone lands on ~1180 existing placements;
    that is a cleanup backlog beside L61's, not a reason to edit the library.
    """
    words, preferred, whole = _id_corpus(lib_roots)
    for vname, view in (data.get("views") or {}).items():
        placements = (((view or {}).get("components") or {}).get("placements") or [])
        taken = {str(x.get("id")) for x in placements if x.get("id")}
        for q in placements:
            pid, ref = str(q.get("id") or ""), str(q.get("ref") or "")
            toks = pid.split("-")

            # 1. the id repeats its own connector
            if ref and len(toks) > 1:
                stated = _states_connector(ref, q, lib_roots)
                for n in (1, 2, 3):
                    lead = "-".join(toks[:n])
                    if n < len(toks) and lead in words and lead in stated:
                        # THE WHOLE CONNECTOR, NOT ITS FIRST WORD. `sfp-plus-3`
                        # matches on `sfp` because that is the media the ganged
                        # cage states, but the qualifier is part of the connector
                        # too - so the id left over is `3` and the name it wants
                        # back is `port-3`, not `plus-3`.
                        while n + 1 < len(toks) and "-".join(toks[:n + 1]) in words:
                            n += 1
                        lead = "-".join(toks[:n])
                        rest = "-".join(toks[n:])
                        # WHAT TO CALL IT INSTEAD, in the corpus's own words: the
                        # commonest function name in front of this same tail
                        # (`clk-` in front of `10mhz-out`, `port-` in front of a
                        # bare numeral), falling back to the tail alone.
                        vote = preferred.get(rest)
                        role = ((q.get("attrs") or {}).get("role")
                                or (_contract(ref, lib_roots).get("attrs") or {}).get("role"))
                        instead = f"{vote[1]}-{rest}" if vote else (
                            rest if rest in whole else None)

                        # A SUGGESTION THAT COLLIDES IS NOT A SUGGESTION. Sixteen
                        # findings proposed a name the device was already using -
                        # `sfp-0` -> `port-0` on a switch whose `port-0` is a
                        # QSFP - and following one merges two placements into one
                        # id, which the schema forbids. The duplication in the id
                        # is still real; what the corpus calls this is simply
                        # taken here, and only a reader of the drawing can say
                        # what distinguishes the two.
                        if instead and instead in taken:
                            warn(path, "L62",
                                 f"{vname}/{pid}: the id opens with {lead!r}, which is the "
                                 f"connector {ref} already states, but {instead!r} - what "
                                 f"the library calls this - IS ALREADY THIS DEVICE'S "
                                 f"{instead}. Two things here need telling apart and the "
                                 f"connector is doing it; name this one for what it does "
                                 f"instead"
                                 + (f" ({role!r} is the role it states)" if role else ""))
                            break

                        # AND A LEFTOVER IS NOT A NAME. With nothing voting on
                        # the tail, the rule used to hand back the bare remainder
                        # - proposing that `sfp-leds` become `leds`, which names
                        # no function and duplicates the group it sits in. Say
                        # the id restates its connector, which is true, and stop
                        # short of inventing the replacement.
                        if instead is None:
                            warn(path, "L62",
                                 f"{vname}/{pid}: the id opens with {lead!r}, which is the "
                                 f"connector {ref} already states. An id names the FUNCTION, "
                                 f"not the connector - and the library has no settled name "
                                 f"for a {rest!r}, so this one has to be read off the drawing"
                                 + (f"; the placement states the role {role!r}"
                                    if role else ""))
                            break

                        why = (f", which is what {vote[0]} other placement(s) in the "
                               f"library call this") if vote else ""
                        alt = (f", or {role!r}, which is the role this placement states"
                               if role and role != instead else "")
                        warn(path, "L62",
                             f"{vname}/{pid}: the id opens with {lead!r}, which is the "
                             f"connector {ref} already states. An id names the FUNCTION, "
                             f"not the connector - use {instead!r}{why}{alt}, and let ref: "
                             f"carry the connector, which is the only place it stays true "
                             f"when the part is changed")
                        break

            # 2. a port lamp spelled some other way
            m = re.match(r"^(led|leds)-(p\d+|port-\d+)(-.*)?$", pid)
            if m and not pid.startswith("led-port-"):
                instead = "led-" + re.sub(r"(?<![a-z0-9])p(\d+)(?![a-z0-9])",
                                          r"port-\1", pid.split("-", 1)[1])
                warn(path, "L62",
                     f"{vname}/{pid}: a port lamp is spelled 'led-port-N' - the "
                     f"library's plurality spelling, against led-pN, leds-port-N and "
                     f"leds-pN. Rename it {instead!r}")


def _aperture_of(ref, lib_roots, depth=0):
    """The opening a part presents, forwarding through a composed cage."""
    ct = contract_for_ref(ref, lib_roots) if "contract_for_ref" in globals() else None
    if ct is None:
        f = libwalk.contract_path(ref, lib_roots)
        if f is None:
            return None
        try:
            ct = load_yaml(f) or {}
        except yaml.YAMLError:
            return None
    if not ct or depth > 3:
        return None
    conf = ct.get("conforms")
    if conf and conf in STANDARDS:
        st = STANDARDS[conf]
        # A PITCH-ONLY ENTRY STATES NO APERTURE. Six registry entries hold a
        # pitch and no `w`/`h` - a panel adapter's OPENING is standardised
        # where its bezel is not - so indexing them here raised KeyError the
        # moment anything declared `conforms:` to one. Falling through to the
        # parts walk is the right answer as well as the safe one: the aperture
        # is then read from whatever this part composes, exactly as it is for
        # a part that names no standard at all.
        if st.get("w") is not None and st.get("h") is not None:
            return (st["w"], st["h"]), (0.0, 0.0)
    found = []
    for part in (ct.get("parts") or []):
        sub = _aperture_of(part.get("ref", ""), lib_roots, depth + 1)
        if sub:
            o = part.get("at") or [0, 0]
            found.append((sub[0], (o[0] + sub[1][0], o[1] + sub[1][1])))
    if len(found) == 1:
        return found[0]
    sz = ct.get("size") or {}
    return ((sz["w"], sz["h"]), (0.0, 0.0)) if sz.get("w") else None


def _air_fraction(box, decor, grid=9):
    """How much of `box` lies over open perforation, reading decor in PAINT ORDER.

    Not an overlap test. A vent field is often the widest rectangle on a face and
    almost everything else is drawn on top of it: the S9600-72XC lays its bottom
    vent from x=44 to x=406 and then paints the QSFP cage panels over it, so two
    port lamps that overlap the vent by area sit on solid green metal and are
    perfectly fine. Asking `does this overlap a vent` reports those; asking
    `what is the topmost thing under this point` does not.

    So sample the item's own footprint, and for each point take the LAST decor
    rectangle that contains it - which is the one a viewer sees. The fraction of
    points whose topmost decor is a vent is the fraction of the item hanging over
    air. A coarse grid is enough: the answers that matter are near 0 and near 1,
    and a 2mm lamp does not need sub-millimetre sampling.
    """
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0 or not decor:
        return 0.0
    air = 0
    for i in range(grid):
        px = x0 + (x1 - x0) * (i + 0.5) / grid
        for j in range(grid):
            py = y0 + (y1 - y0) * (j + 0.5) / grid
            top = None
            for d in decor:
                b = _decor_box(d)
                if b and b[0] <= px <= b[2] and b[1] <= py <= b[3]:
                    # an outline draws a line, not a surface - it hides nothing
                    if d.get("stroke") and not d.get("fill"):
                        continue
                    top = d
            if top is not None and (top.get("pattern") == "vent" or top.get("vent")):
                air += 1
    return air / (grid * grid)


def lint_device_air_aperture(path, data, lib_roots):
    """L64: nothing is bolted to, or printed on, a hole.

    A vent field is not a texture. It is a perforation - the metal is absent -
    and `render.py` says so in the drawing it emits, stamping `data-aperture=
    "air"` on it for anything reading the file rather than looking at it. So a
    legend printed there is printed on nothing, and a jack seated there is
    mounted to nothing.

    EVERY ONE OF THESE WAS FOUND BY A PERSON OPENING A FINISHED DRAWING. On the
    S9600-72XC the 1PPS jack sat wholly inside a 296mm perforated strip, the
    SYNC and SYS lamps inside another, and the model name `S9600-72XC` in the
    middle of a third - a legend on air, which is what the reviewer's screenshot
    showed and what no rule here could see.

    L44 ALREADY LOOKS AT VENTS AND PARTS TOGETHER AND CANNOT CATCH THIS. It
    fires when a patterned field is 80% BURIED, which finds a vent measured
    across a face that is really covered in parts. That is the other direction:
    it says the FIELD is wrong, never that one small thing is sitting on a large
    correct one. A 4.8mm jack on a 296mm vent buries 0.03% of it.

    THE REMEDY IS THE AUTHOR'S, and there are three. The vent is mismeasured and
    stops short of the part - much the commonest. Or the part is in the wrong
    place. Or the metal really is punched through the perforation for it, and
    the drawing has to say so with a cutout, which is why a cutout that contains
    the item silences this.

    Bays are not checked. A bay IS an opening in the metal by construction, and
    a fan bay abutting the vent field that feeds it is the normal way a chassis
    is built rather than a mistake.
    """
    ON_AIR = 0.6          # how much of an item has to hang over air to count

    for vname, view in (data.get("views") or {}).items():
        if not view:
            continue
        decor = ((view.get("panel") or {}).get("decor")) or []
        if not any(d.get("pattern") == "vent" or d.get("vent") for d in decor):
            continue
        cuts = []
        for c in (((view.get("panel") or {}).get("cutouts")) or []):
            b = _decor_box(c)
            if b:
                cuts.append(b)

        def punched(box):
            """The author has declared a hole in the metal here on purpose."""
            return any(box[0] >= c[0] - 0.3 and box[2] <= c[2] + 0.3
                       and box[1] >= c[1] - 0.3 and box[3] <= c[3] + 0.3
                       for c in cuts)

        items = []
        for q in (((view.get("components") or {}).get("placements")) or []):
            sz = contract_size(q.get("ref", ""), lib_roots) if q.get("ref") else None
            if not (q.get("at") and sz):
                continue
            w, h = sz["w"], sz["h"]
            ax, ay = q["at"][0], q["at"][1]
            # A PART IS PUNCHED THROUGH BY ITS APERTURE, NOT ITS BOX. L63 derives
            # a cutout from the aperture a part presents, so a flanged cage's
            # cutout is its opening and never its flange - and asking the cutout
            # to contain the whole cage meant a correctly derived one could not
            # answer this rule. The PBC-2000's two QSFP cages sit in a louvre
            # field through cutouts that are their SFF-8661 openings exactly.
            ap = _aperture_of(q["ref"], lib_roots)
            ap_box = None
            if ap:
                (aw, ah), (ox, oy) = ap
                corners = [(ox, oy), (ox + aw, oy + ah)]
                if q.get("rotate"):
                    th = math.radians(float(q["rotate"]))
                    c, s_ = round(math.cos(th), 12), round(math.sin(th), 12)
                    cx, cy = w / 2.0, h / 2.0
                    corners = [(cx + c * (x - cx) - s_ * (y - cy),
                                cy + s_ * (x - cx) + c * (y - cy)) for x, y in corners]
                xs, ys = [ax + x for x, _ in corners], [ay + y for _, y in corners]
                ap_box = (min(xs), min(ys), max(xs), max(ys))
            if q.get("rotate") in (90, 270, -90):
                w, h = h, w
            items.append(("part", str(q.get("id")), (ax, ay, ax + w, ay + h), ap_box))
        for m in (view.get("silkscreen") or []):
            ext = (_text_extent(m) if m.get("text")
                   else (_path_box(m) if m.get("path") else None))
            if ext:
                items.append(("legend", str(m.get("text") or m.get("id") or "mark"), ext, None))

        for kind, name, box, ap_box in items:
            if punched(box) or (ap_box and punched(ap_box)):
                continue
            frac = _air_fraction(box, decor)
            if frac < ON_AIR:
                continue
            what = ("sits on a vent, which is a hole in the faceplate, not a "
                    "surface it can be mounted to" if kind == "part" else
                    "is printed on a vent, so it is printed on nothing")
            warn(path, "L64",
                 f"{vname}: {kind} {name!r} {what} - {frac * 100:.0f}% of its "
                 f"footprint is over open perforation. Either the vent is "
                 f"measured across metal it does not reach, or this belongs "
                 f"somewhere else; if the metal really is punched through the "
                 f"perforation here, declare the cutout and this goes quiet")


def lint_device_cutout_derivation(path, data, lib_roots):
    """L63: a hole drawn around a part rather than derived from it.

    THREE INDEPENDENT MODELLING RUNS OF ONE DEVICE MADE THIS EXACT MISTAKE, and
    all three passed lint. The rule existed - as a test, `test_cutout_derivation`
    - and a modelling run does not run the test suite, so it sat exactly where
    nobody working on a device would look. An agent on the third run put it
    plainly: it ran lint seven times and never saw the three holes it had drawn
    wrong.

    A cutout RESTATES the aperture its component already declares. Drawn instead
    around what the opening looks like, with a little clearance, it becomes a
    second and disagreeing record of one fact - and the drawing believes
    whichever is wrong. A 2.0mm lamp gets a 2.0mm hole, not a 2.4mm one.
    """
    for vname, view in (data.get("views") or {}).items():
        if not view:
            continue
        panel = (view or {}).get("panel") or {}
        cuts = {c["id"]: c for c in (panel.get("cutouts") or []) if c.get("id")}
        if not cuts:
            continue                       # a face that punches nothing is fine
        for q in ((view.get("components") or {}).get("placements") or []):
            c = cuts.get(q.get("id"))
            if not c or not q.get("at") or not c.get("at") or not c.get("size"):
                continue
            ap = _aperture_of(str(q.get("ref") or ""), lib_roots)
            if not ap:
                continue
            (aw, ah), (ax, ay) = ap
            deg = int(q.get("rotate") or 0) % 360
            if deg in (90, 270):
                aw, ah = ah, aw
            want_at = [round(q["at"][0] + ax, 2), round(q["at"][1] + ay, 2)]
            want_sz = [round(aw, 2), round(ah, 2)]
            dpos = max(abs(want_at[0] - c["at"][0]), abs(want_at[1] - c["at"][1]))
            dsz = max(abs(want_sz[0] - c["size"][0]), abs(want_sz[1] - c["size"][1]))
            if dpos <= 0.02 and dsz <= 0.02:
                continue
            if deg not in (0, 180) or ax or ay:
                continue                   # rotated/offset apertures: L39's business
            warn(path, "L63",
                 f"{vname}/{q['id']}: the cutout is {c['size']} at {c['at']}, and "
                 f"the component {q.get('ref')} declares an opening of {want_sz} "
                 f"at {want_at}. A cutout RESTATES its component's aperture - drawn "
                 f"with clearance it is a second record of one fact, and the drawing "
                 f"believes whichever is wrong. Derive it, do not measure it again.")


def lint_device_alignment(path, data, lib_roots):
    """L61: a legend that is ALMOST centred on the thing it names.

    Every one of these was found by a person opening the drawing and zooming
    in, and every one is arithmetic: a lamp column 1.35mm high on its port
    because a 10.7mm part was offset as though it were 10.0; port numerals
    0.28mm below the gap they sit in, with their arrows 0.55mm below that, so
    the legend row was centred on nothing at all; five status legends 0.21mm
    high on their 2.0mm lamps. None of it is visible at page scale, all of it is
    visible at 4x, and none of it was catchable by any rule here.

    THE RULE ONLY FIRES ON NEAR MISSES. A legend deliberately placed elsewhere -
    a column heading under two rows of jacks, `Reset` beneath its button - is
    not trying to centre on anything, and a rule that nags about those gets
    switched off. So: the mark has to be close enough to be reaching for the
    part (within its extent plus a small margin on the perpendicular axis), and
    then off by enough to see and little enough to be a slip. Dead centre is
    quiet, and so is deliberately somewhere else.
    """
    for s in alignment_slips(data, lib_roots):
        warn(path, "L61",
             f"{s['view']}: {str(s['label'])[:18]!r} is {s['off']:.2f}mm off centre "
             f"{s['axis']} against {'+'.join(str(n) for n in s['names'])} - it sits at "
             f"{s['got']:.2f} and the part's centre is {s['want']:.2f}. Close enough to be "
             f"reaching for it and far enough to see at 4x; either centre it or "
             f"move it somewhere it is plainly not trying to line up")


def alignment_slips(data, lib_roots):
    """Every near-miss L61 reports, as data rather than as a sentence.

    THE RULE AND THE SWEEP THAT FIXES IT MUST NOT BE TWO IMPLEMENTATIONS. A
    corrector that re-derives which axis should line up is a second opinion
    about the same question, and the day the two disagree the sweep moves marks
    the rule never complained about while leaving the ones it did. That is the
    divergence L62 exists to stop, one level up.

    So the decision lives here, once. `lint_device_alignment` turns each slip
    into prose; the sweep reads `axis`, `got` and `want` and shifts the item by
    the difference. Each slip carries the list its item came from and the index
    within it, which is what lets a caller find the line in the file - the mark
    itself has no identity a text search could rely on.
    """
    SLIP = (0.08, 2.0)    # off by at least this, and at most this, to be a slip
    BAND = 2.5            # how far across the axis still counts as the same row
    BALANCED = 0.15       # how near the set's midpoint has to be to be centred

    every = list(alignment_targets(data, lib_roots))
    for a in every:
        if not a["axis"] or not (SLIP[0] <= a["off"] <= SLIP[1]):
            continue

        # A LEGEND ON TWO LINES IS ONE LEGEND, and it is centred as a BLOCK.
        # `GNSS` over `ANT` straddles its jack, 1.29mm above and 1.31mm below,
        # and measuring each line on its own reported the same correct label
        # twice as wrong. Across the corpus that was 296 of 1288 warnings - very
        # nearly a quarter of this rule's whole backlog, every one of them a
        # legend a person would have to open, measure and dismiss.
        #
        # So when several marks OF THE SAME KIND name one target from the same
        # row, what has to sit on the target's centre is their midpoint. A set
        # that straddles evenly is finished; one that does not is still
        # reported, and each member still carries its own offset - the S8901's
        # arrow lamps sit 1.38 and 2.22 out, a midpoint 0.42 off centre, and
        # they stay reported because that pair really is lopsided.
        key = "tcy" if a["axis"] == "vertically" else "tcx"
        got = "cy" if a["axis"] == "vertically" else "cx"
        perp = "cx" if a["axis"] == "vertically" else "cy"
        peers = [t for t in every
                 if t["view"] == a["view"] and t["kind"] == a["kind"]
                 and abs(t[key] - a["want"]) <= 0.001
                 and abs(t[perp] - a[perp]) < BAND]
        if len(peers) >= 2:
            mid = sum(p[got] for p in peers) / len(peers)
            if abs(mid - a["want"]) <= BALANCED:
                continue
        yield a


def alignment_targets(data, lib_roots):
    """Every item that names something to line up with, slipping or not.

    L61 only reports NEAR misses, and a caller that needs to know what else is
    reaching for the same part cannot get it from the reported ones alone. On
    the S8901 each port carries a PAIR of arrow lamps straddling its centre,
    2.22mm out one way and 1.38mm the other; only the second is inside the
    window, so a reader of slips alone sees a lone lamp 1.38mm off its port and
    centres it - straight into the partner it could not see.

    So the geometry is computed once, for every item, and `alignment_slips`
    keeps the near misses. `axis` is None for an item that is not lined up
    against anything on either axis; `off` is 0.0 there and means nothing.
    """
    NEAR = 3.0            # how far off-axis still counts as 'beside' the part

    for vname, view in (data.get("views") or {}).items():
        if not view:
            continue
        boxes = {}
        for q in ((view.get("components") or {}).get("placements") or []):
            sz = contract_size(q.get("ref", ""), lib_roots) if q.get("ref") else None
            if q.get("at") and sz:
                boxes[q["id"]] = (q["at"][0], q["at"][1],
                                  q["at"][0] + sz["w"], q["at"][1] + sz["h"])

        def target_box(for_):
            """The box a `for:` names - the union when it names several, which is
            how a mark that sits BETWEEN two ports declares what it belongs to."""
            names = for_ if isinstance(for_, list) else [for_]
            got = [boxes[n] for n in names if isinstance(n, str) and n in boxes]
            if not got:
                return None
            return (min(b[0] for b in got), min(b[1] for b in got),
                    max(b[2] for b in got), max(b[3] for b in got))

        # marks, and placements that name another placement (a lamp on its port)
        items = [("silkscreen", i, m, _mark_centre(m))
                 for i, m in enumerate(view.get("silkscreen") or [])]
        for i, q in enumerate(((view.get("components") or {}).get("placements") or [])):
            b = boxes.get(q.get("id"))
            if q.get("for") and b:
                items.append(("placement", i, q, ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)))

        for kind, index, m, centre in items:
            if not centre or not m.get("for"):
                continue
            tb = target_box(m["for"])
            if not tb:
                continue
            if kind == "placement" and m.get("id") in (
                    m["for"] if isinstance(m["for"], list) else [m["for"]]):
                continue
            tcx, tcy = (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2
            cx, cy = centre
            label = m.get("text") or m.get("id") or "mark"

            # WHICH AXIS IS THE ONE THAT SHOULD LINE UP depends on where the mark
            # sits, and getting it backwards makes the rule silent rather than
            # wrong - the first version of this checked a lamp sitting BESIDE its
            # port for horizontal alignment, which is the axis it is deliberately
            # offset on, so it never fired on the defect it was written for.
            #
            #   beside the part  (x clear, y overlapping)  -> the Y centres match
            #   above or below   (y clear, x overlapping)  -> the X centres match
            #   between several  (inside the union of what it names, outside each)
            #                                              -> both, against the union
            near_x = tb[0] - NEAR <= cx <= tb[2] + NEAR
            near_y = tb[1] - NEAR <= cy <= tb[3] + NEAR
            in_x = tb[0] <= cx <= tb[2]
            in_y = tb[1] <= cy <= tb[3]
            names = m["for"] if isinstance(m["for"], list) else [m["for"]]

            if near_y and not in_x:                    # beside
                off, axis, got, want = abs(cy - tcy), "vertically", cy, tcy
            elif near_x and not in_y:                  # above or below
                off, axis, got, want = abs(cx - tcx), "horizontally", cx, tcx
            elif len(names) > 1 and in_x and in_y and not any(
                    b[0] <= cx <= b[2] and b[1] <= cy <= b[3]
                    for b in (boxes[n] for n in names if n in boxes)):
                # a legend printed BETWEEN the parts it names - the numerals and
                # arrows in the gap between two rows of ports. Its target is the
                # middle of what it spans, which is the one thing nothing else
                # in this file states.
                dy, dx = abs(cy - tcy), abs(cx - tcx)
                off, axis, got, want = ((dy, "vertically", cy, tcy) if dy >= dx
                                        else (dx, "horizontally", cx, tcx))
            else:
                off, axis, got, want = 0.0, None, cx, tcx
            yield {"view": vname, "kind": kind, "index": index, "item": m,
                   "label": label, "names": names, "axis": axis,
                   "off": off, "got": got, "want": want, "cx": cx, "cy": cy,
                   "tcx": tcx, "tcy": tcy}


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

    NEITHER IS A MODULE THAT SAYS `power-absent: not-applicable`, which this
    rule used to count and should never have. The schema defines the two values
    by what they mean to exactly this arithmetic: `not-published` is "a hole in
    the total", and `not-applicable` is that "a chassis total is COMPLETE
    without a number here, rather than a floor". Counting the second one made
    the rule contradict the vocabulary it was reading - 23 of its 165 warnings
    were modules whose absence was already settled, among them the three generic
    `common/fan-module` shapes, where a wattage would be a fiction dressed as a
    fact because the drawing stands for many real fans at once (#212).

    `not-published` stays counted, because there the figure really is missing.
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
        if sattrs.get("power-absent") == "not-applicable":
            continue                       # settled, not missing - see the docstring
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
    # EVERY SCHEMA ERROR, NOT THE FIRST. `return` inside the loop reported one
    # and stopped, so a manifest with four schema faults took four runs to fix -
    # each one a full lint to find the next. The return still happens, because
    # the checks below read a shape the schema has just said is wrong; it happens
    # after the whole file has been reported rather than after one line of it.
    # `lint_overlay` a few thousand lines down has always done it this way.
    schema_errors = list(validator.iter_errors(data))
    for e in schema_errors:
        err(path, "L1", f"{'/'.join(str(p) for p in e.path)}: {e.message}")
    if schema_errors:
        return data

    def resolve(ref):
        return libwalk.contract_path(ref, lib_roots) is not None

    lint_device_attrs(path, data)
    lint_device_module_power(path, data, lib_roots)
    lint_device_double_count(path, data, lib_roots)
    lint_device_bay_fit(path, data, lib_roots)
    lint_device_midplane_depth(path, data, lib_roots)
    lint_device_plan(path, data, lib_roots)
    lint_device_label_geometry(path, data)
    lint_device_alignment(path, data, lib_roots)
    lint_device_cutout_derivation(path, data, lib_roots)
    lint_device_air_aperture(path, data, lib_roots)
    lint_device_id_convention(path, data, lib_roots)
    lint_device_rj45_lamps(path, data, lib_roots)
    lint_device_face_bindings(path, data, lib_roots)
    declared_groups = set((data.get("groups") or {}).keys())
    for gname, gdef in (data.get("groups") or {}).items():
        check_states(path, f"groups/{gname}", (gdef or {}).get("states"),
                     (gdef or {}).get("attrs"))
    lint_device_groups(path, data, lib_roots)
    lint_device_speed_vocabulary(path, data)
    lint_device_port_rate(path, data, lib_roots)
    lint_device_port_optics(path, data, lib_roots)
    lint_device_pluggable_media(path, data)
    lint_device_cage_media_disagreement(path, data, lib_roots)
    lint_device_placement_interfaces(path, data, lib_roots)
    lint_device_stack_orientation(path, data, lib_roots)
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
        through = {(b.get("rear") or {}).get("cutout")
                   for ov in (data.get("views") or {}).values()
                   for b in view_parts(ov)["bays"]
                   if (b.get("rear") or {}).get("view") == vname}
        lint_device_cutouts(path, vname, view, lib_roots, through - {None})
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
        #
        # AND A HOLE THROUGH A PART PAINTS NOTHING. The PBC-2000's bezel is one
        # plate across the face with two windows cut through it, and the CON,
        # MGMT and CTRL legends are printed on the faceplate inside one of them.
        # A box that carries holes (see component_openings) spares a mark lying
        # wholly in one; the parts a component composes carry none, because a
        # lamp drawn across a window still covers what is behind it.
        boxes = []
        for p in vp["placements"]:
            if not p.get("at"):
                continue                      # a mate-to occupant carries no position
            sz = (contract_size(p["ref"], lib_roots) or {})
            if not (sz.get("w") and sz.get("h")):
                continue
            px, py, pw, ph = p["at"][0], p["at"][1], sz["w"], sz["h"]
            painted = paint_boxes(p["ref"], p.get("skin", "default"), lib_roots)
            holes = placed_openings(p, lib_roots)
            parts = composed_part_boxes(p["ref"], lib_roots) if holes else None
            if painted is None:
                if parts is None:
                    boxes.append((px, py, pw, ph, p["id"], []))
                    continue
                # the skin is unreadable but the holes are not: the whole box
                # with its windows, and each composed part solid
                boxes.append((px, py, pw, ph, p["id"], holes))
                painted, skin_n = parts, 0
            else:
                # paint_boxes puts the composed parts last
                skin_n = len(painted) - len(parts or [])
            flip = str(p.get("rotate", 0)) == "180"
            for i, (x0, y0, x1, y1) in enumerate(painted):
                if flip:                      # a half turn about the box centre
                    x0, x1 = pw - x1, pw - x0
                    y0, y1 = ph - y1, ph - y0
                x0, y0 = max(x0, 0.0), max(y0, 0.0)   # the contracted box is the limit
                x1, y1 = min(x1, pw), min(y1, ph)
                if x1 > x0 and y1 > y0:
                    # only the node the windows are cut in carries them: its box
                    # contains a whole window, where anything drawn IN one is
                    # smaller than it and still covers what is behind it
                    bx0, by0, bx1, by1 = px + x0, py + y0, px + x1, py + y1
                    cut = i < skin_n and any(
                        min(q[0] for q in h) >= bx0 - 0.01 and max(q[0] for q in h) <= bx1 + 0.01
                        and min(q[1] for q in h) >= by0 - 0.01 and max(q[1] for q in h) <= by1 + 0.01
                        for h in holes)
                    boxes.append((bx0, by0, bx1 - bx0, by1 - by0, p["id"],
                                  holes if cut else []))
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
            boxes.append((b["at"][0], b["at"][1], bw, bh, b["id"], []))
        for m in vp["silkscreen"]:
            if not m.get("at"):
                continue
            ext = _text_extent(m) if m.get("text") else (
                _path_extent(m["path"], m["at"]) if m.get("path") else None)
            if not ext:
                continue
            mx0, my0, mx1, my1 = ext
            for bx, by, bw, bh, bid, holes in boxes:
                ox = min(mx1, bx + bw) - max(mx0, bx)
                oy = min(my1, by + bh) - max(my0, by)
                if ox > SILK_TOL and oy > SILK_TOL:
                    if holes:
                        # what the box covers of the mark, less the tolerance
                        # the rule already grants at each edge, lies in a window
                        inner = (max(mx0, bx) + SILK_TOL, max(my0, by) + SILK_TOL,
                                 min(mx1, bx + bw) - SILK_TOL, min(my1, by + bh) - SILK_TOL)
                        area = (inner[2] - inner[0]) * (inner[3] - inner[1])
                        if area > 0 and open_area(inner, holes) >= area - 1e-6:
                            continue
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
                    "role: traffic|fabric|management|service|indicator|furniture - a PSU "
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
            joined = " ".join(
                str(v.get("note") if isinstance(v, dict) else v) for v in prov.values()).lower()
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
            """Every provenance entry that says the figure was estimated.

            TWO SHAPES, BECAUSE THE LIBRARY HOLDS TWO. A device's provenance is
            `{key: {confidence, note}}` after #167; a component's is still
            `{key: string}`, and this function is handed both - the verified
            check walks a device AND every component it places.

            AND IT READS THE PROSE TOO, not only the field. It used to be
            `str(v).startswith("estimated")` against strings, which saw 42 of the
            122 entries that say estimated: the other 80 say it in the middle of
            a paragraph - "the layout is estimated", "ESTIMATED shape, from
            photographs". Nothing is at `verified` yet, so tightening this
            breaks nothing today and means the first device that claims it gets
            an honest answer rather than a prefix match.
            """
            out = []
            for k, v in (doc.get("provenance") or {}).items():
                if isinstance(v, dict):
                    if v.get("confidence") == "estimated":
                        out.append(k)
                        continue
                    text = str(v.get("note") or "")
                else:
                    text = str(v)
                if re.search(r"\bestimat", text, re.I):
                    out.append(k)
            return sorted(out)
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

    lint_device_configuration_bays(path, data, lib_roots)
    return data


def lint_device_configuration_bays(path, data, lib_roots):
    """L8: a configuration seats what its bays accept.

    A NESTED KEY IS WALKED: `riser-1/slot-1` is the device's riser-1 bay, then
    a bay called slot-1 on one of the modules riser-1 accepts, and the ref must
    be in THAT bay's accepts. Which module is seated is not known here - the
    configuration may say - so any accepted module's slot counts.
    """
    bay_accepts = {}
    for view in (data.get("views") or {}).values():
        for b in view_parts(view)["bays"]:
            bay_accepts[b["id"]] = b.get("accepts") or []

    def nested_accepts(key):
        head, *rest = key.split("/")
        accepts = bay_accepts.get(head)
        if accepts is None:
            return None
        for seg in rest:
            found = None
            for mref in accepts:
                cp = resolve_component(mref, lib_roots)
                c = (load_yaml(cp) or {}) if cp else {}
                b = (c.get("bays") or {}).get(seg)
                if isinstance(b, dict):
                    found = (found or []) + list(b.get("accepts") or [])
            if found is None:
                return None
            accepts = found
        return accepts
    for cname, cfg in (data.get("configurations") or {}).items():
        for bid, ref in (cfg.get("bays") or {}).items():
            if "/" in bid:
                acc = nested_accepts(bid)
                if acc is None:
                    err(path, "L8", f"config {cname}: unknown nested bay {bid}")
                elif ref and ref not in acc:
                    err(path, "L8", f"config {cname}: {bid} does not accept {ref}")
                continue
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


def print_matrix(matrix, schemas):
    """One table, every device, level and flags.

    This is what turns lint output from a pass/fail into a dashboard. The
    portfolio's shape - which models can be put in a rack elevation, which can
    go to 3D, which can be exported - was previously only knowable by opening
    thirteen files, so nobody knew it.

    Nothing here is declared. Every column is computed from the manifest, so it
    cannot be optimistic and cannot go stale.
    """
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


def lint_device_plan(path, data, lib_roots):
    """L72: a bay's `plan:` or `rear:` lands in a view that exists, in a well
    (or, for `rear:`, a cutout with a depth) that is there, and its occupants
    have that face to land.

    The projection is drawn from what the bay's occupants declare, so a bay
    that says `plan:` while none of what it accepts carries `plan.ref` draws
    nothing and says nothing - which is the silent failure this reports.
    """
    views = data.get("views") or {}
    for vname, view in views.items():
        for b, face in ((b, f) for b in view_parts(view)["bays"] for f in ("plan", "rear")):
            pl = b.get(face)
            if not pl:
                continue
            tv = views.get(pl.get("view"))
            if tv is None:
                err(path, "L72", f"{vname}: {b['id']} projects into view {pl.get('view')!r}, "
                                 "which this device does not have")
                continue
            tp = view_parts(tv)
            there = {q.get("id") for q in (*tp["placements"], *tp["bays"])}
            # A REAR PROJECTION IS SEEN THROUGH A HOLE, and a hole with no depth
            # is only paint: render.py refuses it, so say so here first.
            if face == "rear":
                cuts = {c.get("id"): c for c in ((tv.get("panel") or {}).get("cutouts") or [])}
                cut = cuts.get(pl.get("cutout"))
                if cut is None:
                    err(path, "L72", f"{vname}: {b['id']} is seen from behind through cutout "
                                     f"{pl.get('cutout')!r}, which is not in {pl['view']}")
                elif not cut.get("depth"):
                    err(path, "L72", f"{vname}: {b['id']} is seen through cutout {cut['id']}, "
                                     "which has no `depth` - a painted hole cannot show a back set in")
            if pl.get("in") and pl["in"] not in there:
                err(path, "L72", f"{vname}: {b['id']} projects `in:` {pl['in']}, which is "
                                 f"not in {pl['view']}")
            for u in (pl.get("under") or []):
                if u not in there:
                    err(path, "L72", f"{vname}: {b['id']} projects `under:` {u}, which is "
                                     f"not in {pl['view']} - it would paint in the wrong order")
            have = []
            for ref in (b.get("accepts") or []):
                cp = resolve_component(ref, lib_roots)
                c = (load_yaml(cp) or {}) if cp else {}
                pref = face_ref(c, face)
                if pref:
                    if not resolve_component(pref, lib_roots):
                        err(path, "L72", f"{vname}: {ref} names {face} {pref}, which is not in the library")
                    have.append(ref)
            if not have:
                warn(path, "L72", f"{vname}: {b['id']} projects into {pl['view']} but none of "
                                  f"what it accepts carries `faces.{face}` - nothing will be drawn")


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


def _null_attr_keys(attrs, prefix=""):
    """Dotted keys under this `attrs:` map whose value is null.

    Recursive because a device's top-level attrs is filed by section, so the
    null sits at `power.power-inlet` rather than at the first level.
    """
    for key, value in attrs.items():
        if value is None:
            yield f"{prefix}{key}"
        elif isinstance(value, dict):
            yield from _null_attr_keys(value, f"{prefix}{key}.")


def _attrs_maps(node, owner=None):
    """Every (owner, attrs map) below here, owner being what carries it.

    Generic rather than a list of the six places a schema puts an `attrs:`,
    because the point of the rule is that nothing types these maps - a seventh
    place would be as unguarded as the six, and would join this walk for free.
    """
    if isinstance(node, list):
        for item in node:
            yield from _attrs_maps(item, owner)
        return
    if not isinstance(node, dict):
        return
    here = node.get("id") or owner
    for key, value in node.items():
        if key == "attrs" and isinstance(value, dict):
            yield here, value
        elif isinstance(value, dict):
            # A MAPPING KEY NAMES ITS VALUE where the value has no id of its
            # own: `groups: {xe: {...}}` is the group called xe. Structural
            # keys - `components`, `views` - name nothing, but they are only
            # ever a fallback, and the dotted attr key carries the rest.
            yield from _attrs_maps(value, value.get("id") or key)
        elif isinstance(value, list):
            yield from _attrs_maps(value, here)


def lint_attrs_null(path, data):
    """L100 - an attr with no value is a missing colon.

    YAML flow style hides this completely. In a component's `parts:` list,

        attrs: {media: sfp-plus, function: reserved, unused}

    the last entry has no colon, so it is not part of the entry before it: it is
    a THIRD key, `unused`, with a null value. Every `attrs:` in spec/schemas is
    typed `{"type": "object"}` and nothing else - free-form is the point, these
    become `data-*` on the instance - so the schema had nothing to say, and the
    run went red much later and somewhere else. `presented_interface` returned a
    two-tuple for the malformed part and L11 unpacked it into three names, which
    reads as a fault in the LINTER rather than a typo in the contract.

    AN ATTR THAT IS NULL CARRIES NOTHING. It flattens to no data attribute, no
    export reads it, no renderer draws it; there is no reading of it that is not
    this mistake, so it is an error rather than a warning.

    The sibling maps that are NOT walked here are the ones a schema already
    types: a device's `bay-attrs` and `component-attrs` take string or number,
    and a bay itself declares no `attrs` at all in either schema, so a null in
    those places is an L1 before it is ever an L100.
    """
    if not isinstance(data, dict):
        return
    for owner, attrs in _attrs_maps(data):
        for key in _null_attr_keys(attrs):
            last = key.rsplit(".", 1)[-1]
            where = f"{owner}: " if owner else ""
            err(path, "L100",
                f"{where}attrs.{key} has no value. An attr that is null carries "
                f"nothing - the usual cause is a MISSING COLON: in YAML flow "
                f"style `{{..., {last}}}` is a key of its own with a null value, "
                f"not part of the entry before it. Write `{last}: <value>`, or "
                f"delete the key")


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
    # THE CATALOGUE NEEDS NO LIBRARY. A contributor who has just read `[L61]`
    # wants the rule, not a lint run, so the two flags below are answered before
    # the schema and library arguments are required of anyone.
    ap.add_argument("--list-rules", action="store_true",
                    help="print every rule code with its scope and what it checks, then exit")
    ap.add_argument("--markdown", action="store_true",
                    help="with --list-rules: the table docs/lint-rules.md is generated from")
    ap.add_argument("--schemas")
    ap.add_argument("--library", action="append")
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
    # WARNINGS ARE A PASS BY DEFAULT, AND A CALLER CAN SAY OTHERWISE. The census
    # rules (L24, L40, L68 and the rest) fire on the day they land and are meant
    # to shrink, so a run with warnings exits 0 and the gate stays usable. But
    # exit 0 also meant a script could not tell a clean run from a warning run
    # without parsing the output (#109). `--strict` makes that a status: exit 2
    # on any warning, for a caller who wants "no warnings" to be checkable.
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any warning was raised (default: warnings pass)")
    # THE BACKLOG IS NOT THE NEWS. See the baseline note above `load_baseline`.
    ap.add_argument("--new-only", action="store_true",
                    help="print only warnings this tree has and library/lint-baseline.json "
                         "does not - what THIS change added, rather than the whole backlog")
    ap.add_argument("--update-baseline", action="store_true",
                    help="rewrite library/lint-baseline.json from this run, and exit")
    args = ap.parse_args()
    if args.list_rules:
        sys.stdout.write(rules_text(markdown=args.markdown) + ("" if args.markdown else "\n"))
        return 0
    if not args.schemas or not args.library:
        ap.error("--schemas and --library are required (or use --list-rules)")
    schemas = Path(args.schemas)
    std_file = schemas / "standards.yaml"
    if std_file.exists():
        STANDARDS.update(load_yaml(std_file)["standards"])
    if (schemas / "power-roles.yaml").exists():
        global DRAW_CLASSES, SUPPLY_CLASSES, PASSIVE_CLASSES
        DRAW_CLASSES, SUPPLY_CLASSES, PASSIVE_CLASSES = _load_power_roles(schemas)
    # THE SPEED SET FOLLOWS --schemas TOO, like the power roles: an alternate
    # tree is linted against its own vocabulary, not this checkout's.
    if (schemas / "speeds.yaml").exists():
        global PORT_SPEEDS
        PORT_SPEEDS = _load_port_speeds(schemas)
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
                lint_attrs_null(f, d)
                _skin_checks(f, d)
                lint_component_parts(f, d, args.library)
                lint_component_collisions(f, d, args.library)
                lint_component_bays_drawn(f, d, args.library)
                lint_component_skin_printing(f, d, args.library)
                lint_component_states_render(f, d, args.library)
                lint_component_mating(f, d, args.library)
                lint_component_aperture(f, d, args.library)
                lint_component_power(f, d)
                lint_component_dc_capacity(f, d)
                lint_component_inlet(f, d, args.library)
                lint_component_cage_rate(f, d)
                lint_component_speed_vocabulary(f, d)
                lint_component_size_confidence(f, d)
                lint_component_display(f, d)
                lint_component_generic(f, d)
                lint_component_size_sourced(f, d)
                lint_component_role(f, d)
                lint_component_forwarded_mate(f, d, args.library)
                lint_component_seat_point(f, d)
                lint_component_stack_orientation(f, d, args.library)
                lint_component_slot_defaults(f, d, args.library)
                lint_component_spanned_geometry(f, d, args.library)
                lint_component_spanned_exclusion(f, d, args.library)
                lint_component_relief_confidence(f, d, args.library)
                lint_component_body_boxes(f, d)
                lint_component_faces_once(f, d)
                # L83 IS HANDED THE PART'S OWN REF, so it can catch a contract
                # naming itself as its own face - a copy-paste away, and
                # invisible without it. The path carries both halves: namespace
                # in the grandparent directory, major in the `v<N>` one. Same
                # derivation components_index.py:55-57 uses, so the string L83
                # compares against is the one the rest of the library writes.
                lint_component_faces_resolve(
                    f, d, args.library,
                    f"{f.parents[2].name}/{d.get('name')}@{f.parent.name[1:]}")
                lint_component_superseded_by(f, d, args.library)
                lint_component_pluggable_rate(f, d)
                lint_component_optical_endpoints(f, d, args.library)
                lint_component_optical_faces(f, d)
                lint_component_optical_face_capacity(f, d, args.library)
                lint_component_optical_polish(f, d)
                lint_component_optical_rear_kind(f, d)
                lint_component_optical_front_order(f, d)
                lint_component_optical_conflicts(f, d)
                lint_component_optical_coverage(f, d, args.library)
                lint_component_optical_polarity(f, d, args.library)
                lint_component_optical_position_nodes(f, d, args.library)
                lint_component_composed_pitch(f, d, args.library)
                lint_component_sink_context(f, d)
                lint_component_facets(f, d, args.library)
                lint_component_fields(f, d)
                lint_component_lamp_colour(f, d)
                lint_component_slots(f, d)
                lint_component_rj45_lamps(f, d, args.library)
                lint_component_groups(f, d, args.library)
                lint_quoted_prose(f, d)
            n += 1
        for f in sorted(root.glob("devices/**/device.yaml")):
            if args.device and not any(sel in str(f) for sel in args.device):
                continue
            lint_duplicate_keys(f)
            d = lint_device(f, dev_v, args.library); n += 1
            if d is not None and d.get("kind") == "device":
                lint_attrs_null(f, d)
                lint_device_gap_scope(f, d)
                lint_device_configuration_kind(f, d)
                lint_device_top_level_skus(f, d)
                lint_device_empty_declaration(f, d)
                lint_device_power_redundancy(f, d)
                lint_device_fan_redundancy(f, d)
                lint_device_declared_silence(f, d)
                lint_device_control_plane_redundancy(f, d)
                waive = ((d.get("lint") or {}).get("waive")) or {}
                if waive:
                    WAIVED[str(Path(f).resolve())] = dict(waive)
                lint_device_key_order(f, d)
                lint_device_airflow_home(f, d)
                lint_device_provenance_confidence(f, d)
                lint_quoted_prose(f, d)
                lint_device_component_attrs_resolve(f, d)
                lint_device_spanned_exclusion(f, d, args.library)
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
    # L53 IS LIBRARY-WIDE and compares against the per-device locks, so a
    # --device run cannot do it: `devicelock.check` walks every device, and a
    # partial check would report the unexamined ones as unchanged.
    if not args.device:
        lint_library_comparable_facts([Path(r) for r in args.library], matrix)
        lint_library_aliases(matrix)
        for root in [Path(r) for r in args.library]:
            lint_vendor_registry(root)
            lint_unplaced_majors(root)
            lint_pluggable_family_interfaces(root)
            if not list(libwalk.iter_devices([root])):
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
                # THE DEVICE'S OWN LOCK, which is the file the reader has to
                # edit. It used to name `library/devices.lock.json` - one path
                # for all 89 findings, and the one file a contributor never
                # opens by hand (#182).
                (err if dev_maturity.get(slug_) == "verified" else warn)(
                    devicelock.lock_path(root, slug_), "L53", msg_)

    if args.device:
        print(f"LINT: {len(matrix)} device(s) matching {args.device} - "
              "PARTIAL RUN, portfolio matrix and cross-device checks skipped. "
              "Run without --device before committing")
    else:
        print_matrix(matrix, schemas)

    base = None if args.device else load_baseline(Path(args.library[0]))
    # WAIVED WARNINGS ARE SEPARATED, NOT HIDDEN. A rule a device has argued with
    # still fires and is still counted; what changes is that it stops competing
    # for attention with the ones nobody has looked at. The reason is printed
    # beside it, so the argument is in the output rather than only in the file.
    waived = [w for w in WARNINGS if _is_waived(w)]
    if waived:
        WARNINGS[:] = [w for w in WARNINGS if not _is_waived(w)]
    # AFTER THE WAIVER SPLIT, so a warning a device has argued with is not
    # recorded as backlog and then reported as newly fixed on every later run.
    if args.update_baseline:
        counts = _warning_counts(WARNINGS, args.library[0])
        out = Path(args.library[0]) / BASELINE_NAME
        out.write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
        total = sum(n for r in counts.values() for n in r.values())
        print(f"LINT: baseline written - {_count(total, 'warning')} across "
              f"{_count(len(counts), 'file')} -> {out}")
        return 0
    shown = WARNINGS
    if args.new_only:
        if base is None:
            print("LINT: --new-only needs library/lint-baseline.json; run --update-baseline")
            return 2
        new_counts, _gone = baseline_delta(WARNINGS, base, args.library[0])
        keep, seen = [], {}
        for w in WARNINGS:
            if "[" not in w:
                continue
            f = _rel(w.split(":")[0].strip(), args.library[0])
            code = w.split("[")[1].split("]")[0]
            want = (new_counts.get(f) or {}).get(code, 0)
            k = seen.get((f, code), 0)
            if k < want:
                keep.append(w)
                seen[(f, code)] = k + 1
        shown = keep
    if shown:
        by_code = {}
        for w in shown:
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
    # THE LINE A REVIEWER READS. Without it the tail says 1393 and a reader has
    # no way to know whether this branch put one of them there.
    if base is not None and WARNINGS:
        new_counts, gone = baseline_delta(WARNINGS, base, args.library[0])
        n_new = sum(v for r in new_counts.values() for v in r.values())
        n_gone = sum(v for r in gone.values() for v in r.values())
        if n_new or n_gone:
            bits = []
            if n_new:
                bits.append(f"{_count(n_new, 'warning')} NEW since the baseline")
            if n_gone:
                bits.append(f"{n_gone} fixed")
            print(f"LINT: {', '.join(bits)} "
                  "(`--new-only` prints just the new ones; `--update-baseline` re-records)")
            for f_, rules in sorted(new_counts.items()):
                for code, k in sorted(rules.items()):
                    print(f"      +{k:<3d} [{code}] {f_}")
        else:
            print("LINT: no change against the baseline - every warning here was "
                  "already in library/lint-baseline.json")
    if waived:
        print(f"LINT: {_count(len(waived), 'warning')} waived by the device that raised "
              "them, with a reason:")
        seen = set()
        for w in waived:
            f_ = w.split(":")[0].strip()
            code = w.split("[")[1].split("]")[0]
            if (f_, code) in seen:
                continue
            seen.add((f_, code))
            n_ = sum(1 for x in waived
                     if x.split(":")[0].strip() == f_ and f"[{code}]" in x)
            print(f"      {n_:4d}  [{code}] {f_}")
            print(f"            {(_is_waived(w) or '')[:150]}")
    if args.strict and WARNINGS:
        print(f"LINT: failed --strict ({n} files, {_count(len(WARNINGS), 'warning')} "
              f"in {_count(len(_rules(WARNINGS)), 'rule')})")
        sys.exit(2)
    print(summary_line(n, WARNINGS))


# --------------------------------------------------------------- baseline ---
#
# WHAT A NEWCOMER SEES ON THEIR FIRST RUN, which is the half of #180 that is
# about people rather than about rules. A clean tree reports 1393 warnings in 24
# rules; L61 alone is 645. Somebody who clones the repository, changes one
# device and runs the gate cannot tell the known backlog from the thing they
# just broke, and the only way to find out has been to run lint before and
# after and diff the two by hand.
#
# COUNTS PER FILE PER RULE, not warning text. A message carries coordinates and
# measurements - "is 0.92mm off centre ... it sits at 51.42" - so keying on the
# sentence would churn the baseline on every re-measurement and hide the new
# warning in the noise of the moved ones. A count is stable under rewording and
# still says the thing that matters: this file has more of this rule than it
# used to.
#
# IT IS NOT A WAIVER AND MUST NOT READ AS ONE. Nothing here is forgiven; the
# full count still prints and the summary line still carries it. The baseline
# only separates "already true" from "true because of this change", which is
# the question a reviewer is actually asking.

BASELINE_NAME = "lint-baseline.json"


# device path -> {rule: reason}, filled as each manifest is read
WAIVED = {}


def _is_waived(w):
    """A warning this device has argued with, by rule code.

    Keyed on the resolved path, for the reason `_rel` gives: the message carries
    whatever spelling the caller passed, and a waiver that only works when lint
    is run from the repository root is a waiver that silently stops working.
    """
    if "[" not in w:
        return None
    try:
        f = str(Path(w.split(":")[0].strip()).resolve())
    except OSError:
        f = w.split(":")[0].strip()
    code = w.split("[")[1].split("]")[0]
    return (WAIVED.get(f) or {}).get(code)


def _rel(f, root):
    """A warning's path as the baseline records it: relative to the library.

    RUNNING LINT FROM ELSEWHERE MUST NOT REPORT THE WHOLE BACKLOG AS NEW. The
    message carries whatever path the caller passed - `library/devices/...` from
    the repository root, an absolute one from a test or another checkout - so a
    baseline keyed on it is keyed on the invocation. Relative to the library root
    both spellings are `devices/...`.
    """
    try:
        return str(Path(f).resolve().relative_to(Path(root).resolve()))
    except (ValueError, OSError):
        return str(f)


def _warning_counts(warnings, root):
    """{file relative to the library: {rule: n}} from the warning list."""
    out = {}
    for w in warnings:
        if "[" not in w:
            continue
        f = _rel(w.split(":")[0].strip(), root)
        code = w.split("[")[1].split("]")[0]
        out.setdefault(f, {}).setdefault(code, 0)
        out[f][code] += 1
    return out


def load_baseline(root):
    p = Path(root) / BASELINE_NAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def baseline_delta(warnings, base, root="library"):
    """(new, gone) as {file: {rule: n}} - what this tree has that the baseline
    did not, and what it no longer has."""
    now = _warning_counts(warnings, root)
    new, gone = {}, {}
    for f, rules in now.items():
        for code, n in rules.items():
            was = (base.get(f) or {}).get(code, 0)
            if n > was:
                new.setdefault(f, {})[code] = n - was
    for f, rules in base.items():
        for code, n in rules.items():
            has = (now.get(f) or {}).get(code, 0)
            if has < n:
                gone.setdefault(f, {})[code] = n - has
    return new, gone


def _rules(warnings):
    return {w.split("[")[1].split("]")[0] for w in warnings if "[" in w}


def _count(n, noun):
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def summary_line(n_files, warnings):
    """The last line, and it is a verdict. `LINT: ok (600 files)` printed under
    24 warning blocks read as clean to anyone who looked at the tail - and a PR
    body did, writing "lint clean at 600 files" over a run carrying 95 warnings
    (#109). A warning run still passes: the census rules exist to be counted
    and to shrink. But the count is on the last line now, so the tail cannot
    say something the rest of the output does not."""
    if not warnings:
        return f"LINT: ok ({_count(n_files, 'file')})"
    return (f"LINT: ok ({_count(n_files, 'file')}, {_count(len(warnings), 'warning')} "
            f"in {_count(len(_rules(warnings)), 'rule')})")


if __name__ == "__main__":
    main()
