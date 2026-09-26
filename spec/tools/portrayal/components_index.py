#!/usr/bin/env python3
"""Publish every library component COMPILED (skin + composed parts flattened)
to dist/components/ with a JSON index for the demo component browser.

TWO index files come out of here, not one:

  components.json          what a viewer reads to draw a part - identity, size,
                           skins, files, body, attrs, elements. Fetched on every
                           demo page load, so it carries nothing else.
  components-detail.json   `provenance` and `relief` per ref, in full. Nothing
                           is dropped; it is one deliberate fetch away.
"""
import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from portrayal.manifest import load_yaml

from portrayal.faces import DIRECTIONS, face_ref  # noqa: E402
from portrayal.render import (SVG_NS, STATE_CSS, Library, instance_group,  # noqa: E402
                    seq_css_name, state_rule, component_cages,
                    _pluggable_families, _pluggable_candidates,
                    _connector_registry)
from portrayal import libwalk  # noqa: E402
from portrayal import optical, optical_ports  # noqa: E402
from portrayal import facets as _facets  # noqa: E402


def preview_box(data, lib, skin="default", skin_dir=None, _seen=()):
    """THE STANDALONE PREVIEW HOLDS THE HEAD. A part that declares `head:`
    overhangs its face box on purpose (docs/pluggables-heads-design.md 4.2):
    the copper SFP head stands 2.50 above and 2.15 below it, and the QSFP
    generics' composed pull tab 1.07 above and 0.325 each side. The module
    preview under dist/components had the part's own `size` as its root
    viewBox, so it clipped all of it. For such a part the box is the union of
    the size box, the head box, the art box of every one of its OWN relief
    features' skin nodes (a cable end's strap ring can stand above its head),
    and every composed part's box, in the part's own coordinates, so its origin
    and every coordinate inside are unchanged.

    A COMPOSED PART CONTRIBUTES ITS OWN PREVIEW BOX, not its bare size: the
    same union, recursively, placed as render.py places it (its `at`, turned
    about its size centre as `rotate` says, mirrored as `mirror` says, and
    foreshortened as `on` says, the order facets.projected_box states). A
    part with no preview box of its own contributes its size box, exactly as
    before. So a vendor wrapper, which composes its generic whole and declares
    no `head:` itself, holds the generic's overhangs too.

    None for a part that neither declares `head:` nor composes a part with a
    preview box. It, and a part whose union is its size box, keep `0 0 w h`
    byte for byte. The kit's 3D module view reads the preview's viewBox as its
    face, so it crops back to the size box (kit/relief.js toSizeBox).

    `skin_dir` is the part's own skins folder; without it the own-feature
    boxes are not read (a composed part's comes from lib.resolve)."""
    size = data["size"]
    sw, sh = float(size["w"]), float(size["h"])
    boxes = [(0.0, 0.0, sw, sh)]
    head = data.get("head")
    if head:
        hx, hy = head.get("at") or (0.0, 0.0)
        boxes.append((float(hx), float(hy), float(hx) + float(head["size"]["w"]),
                      float(hy) + float(head["size"]["h"])))
        boxes.extend(_feature_boxes(data, skin, skin_dir))
    composed = False
    for part in data.get("parts") or []:
        if part["ref"] in _seen:
            raise ValueError(f"preview_box: {part['ref']} composes itself")
        pc, pdir = lib.resolve(part["ref"])
        inner = preview_box(pc, lib, part.get("skin", "default"), pdir,
                            _seen + (part["ref"],))
        composed = composed or inner is not None
        facet = _facets.facet_of(data, part["on"]) if part.get("on") else None
        boxes.append(_placed_box(part["at"], pc["size"], inner, part.get("rotate"),
                                 part.get("mirror"), facet))
    if not head and not composed:
        return None
    return (round(min(b[0] for b in boxes), 6), round(min(b[1] for b in boxes), 6),
            round(max(b[2] for b in boxes), 6), round(max(b[3] for b in boxes), 6))


def _placed_box(at, size, inner, rotate, mirror, facet):
    """The box a composed part occupies in its parent's frame. With no preview
    box of its own this is facets.projected_box, the rule render.py draws by.
    With one, its corners go through the same chain render.py writes -
    translate(at) scale(facet) rotate(deg, w/2, h/2) [translate(w,0) scale(-1,1)]
    - innermost first."""
    w, h = float(size["w"]), float(size["h"])
    if inner is None:
        return _facets.projected_box(at, w, h, rotate, facet)
    x0, y0, x1, y1 = inner
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if mirror:
        pts = [(w - x, y) for x, y in pts]
    if rotate:
        t = math.radians(float(rotate))
        c, s = round(math.cos(t), 12), round(math.sin(t), 12)
        cx, cy = w / 2, h / 2
        pts = [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c)
               for x, y in pts]
    if facet:
        k = _facets.cos_of(facet)
        if _facets.axis_of(facet) == "y":
            pts = [(x, y * k) for x, y in pts]
        else:
            pts = [(x * k, y) for x, y in pts]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (at[0] + min(xs), at[1] + min(ys), at[0] + max(xs), at[1] + max(ys))


def _feature_boxes(data, skin, skin_dir):
    """The art box of each of the part's own relief features' skin nodes, read
    off the skin: a rect's x/y/width/height, a circle's centre and radius. Any
    other node (a path, a group) is left to the head and size boxes. A node
    under a `transform` is refused rather than measured in the wrong frame."""
    feats = (data.get("relief") or {}).get("features") or []
    if not feats or skin_dir is None:
        return []
    f = Path(skin_dir) / f"{skin}.svg"
    declared = data.get("skins") or []
    if not f.exists() and skin == "default" and len(declared) == 1:
        f = Path(skin_dir) / f"{declared[0]}.svg"     # render.py's one-skin rule
    if not f.exists():
        return []
    root = ET.parse(f).getroot()
    parents = {c: p for p in root.iter() for c in p}
    byid = {e.get("id"): e for e in root.iter() if e.get("id")}
    out = []
    for feat in feats:
        el = byid.get(feat.get("node"))
        if el is None:
            continue
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("rect", "circle"):
            continue
        n = el
        while n is not None:
            if n.get("transform"):
                raise ValueError(f"preview_box: {data.get('name')} node {feat['node']!r} "
                                 f"sits under a transform; its box is not measured")
            n = parents.get(n)
        if tag == "rect":
            x, y = float(el.get("x") or 0), float(el.get("y") or 0)
            out.append((x, y, x + float(el.get("width")), y + float(el.get("height"))))
        else:
            cx, cy, r = (float(el.get(k) or 0) for k in ("cx", "cy", "r"))
            out.append((cx - r, cy - r, cx + r, cy + r))
    return out


def fibre_ends(data, load_ref):
    """`{endpoint: {"to": far endpoint(s), "label": front number or None}}`.

    A two-ended path names one far end each way, each side falling back to
    the other's label when its own is None (a rear endpoint has none). A
    SPLIT DOES NOT FALL BACK THE SAME WAY: `optical.endpoints` is the one
    place this library reads a path's `to` as either a string or a ratio
    list (smartoptics/ppm-ocu-50-50, ppm-ocu-97-3 - a coupler's one input
    reaching two legs), and the source of a split keeps only its OWN label
    or None; a common port never borrows a branch's number, but a branch
    with no number of its own (there isn't one in this library, but nothing
    stops one) borrows the common port's, because that is the one number the
    explorer can show for it. Dropping this shape read as `optical.ends: {}`
    on a real, DCIM-exported part - wrong, not merely incomplete.

    A LIST `from` IS NOT A SHAPE THIS SCHEMA HAS: `optical.endpoints` reads
    `path["from"]` as a single string unconditionally, and L79 (`lint.py`)
    checks a path's source the same way - a fan-IN combiner has no syntax
    here, so one is treated as an unresolved endpoint and skipped, the same
    as any other value `split_endpoint` cannot parse.
    """
    ends = {}
    for p in data["optical"]["paths"]:
        if not isinstance(p.get("from"), str) or not p.get("to"):
            continue
        eps = [ep for ep, _ratio in optical.endpoints(p)]
        if len(eps) < 2 or not all(isinstance(ep, str) for ep in eps):
            continue
        src, dests = eps[0], eps[1:]
        label = {ep: optical_ports.front_label(data, ep, load_ref) for ep in eps}
        if len(dests) == 1:
            b = dests[0]
            ends[src] = {"to": b, "label": label[src] if label[src] is not None else label[b]}
            ends[b] = {"to": src, "label": label[b] if label[b] is not None else label[src]}
        else:
            ends[src] = {"to": dests, "label": label[src]}
            for b in dests:
                ends[b] = {"to": src, "label": label[b] if label[b] is not None else label[src]}
    return ends


def _confidence_counts(data):
    """{token: n} over a component's relief features, with the unmarked counted.

    Deliberately counts FEATURES rather than distinct numbers. Nineteen cards
    carrying one borrowed 4.2 is nineteen features and one reading, and the two
    are different facts - the per-feature `source` is what tells them apart, so
    a consumer that needs the second must read it rather than infer it here.
    """
    counts = {}
    for f in ((data.get("relief") or {}).get("features") or []):
        counts[f.get("confidence") or "unstated"] = \
            counts.get(f.get("confidence") or "unstated", 0) + 1
    return counts


def named_as_faces(roots):
    """Every part some module draws as one of its FACES - a cassette's back -
    which component_cages publishes whole (its `face` note): nothing places a
    face, so a slot it forwarded would be published nowhere."""
    return {r for root in roots
            for cf in Path(root).glob("components/*/*/v*/contract.yaml")
            for k in DIRECTIONS
            if (r := face_ref(load_yaml(cf) or {}, k))}


def seated_in_bays(roots):
    """Every part some BAY can hold - named in a bay's `accepts` or `default`,
    or seated in one by a configuration - on a device or on a card.

    A MODULE IN A BAY IS NEVER A PLACED SLOT, which is the build's own rule
    (manifest.slot_in_slot_at). A card that happens to compose exactly one
    interface-bearing part - casa/smm-8x10g@1's console, the IRIG-B card's
    RS-422 jack - does not forward it: the build seats a plug at
    `front-6/console` like any other card port. component_cages could not see
    that from the contract alone and hid the jack as a wrapper's aperture, so
    the kit had no slot where the build had one (#610). This is the set it is
    told instead, gathered the way named_as_faces gathers faces.
    """
    found = set()

    def walk(o, key=None):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, k)
        elif isinstance(o, list):
            for v in o:
                if key == "bays" and isinstance(v, dict):
                    found.update(r for r in v.get("accepts") or [] if isinstance(r, str))
                    if isinstance(v.get("default"), str):
                        found.add(v["default"])
                walk(v, key)

    for f in libwalk.iter_devices(roots) + libwalk.iter_components(roots):
        doc = load_yaml(f) or {}
        walk(doc)
        for cfg in (doc.get("configurations") or {}).values():
            found.update(r for r in ((cfg or {}).get("bays") or {}).values()
                         if isinstance(r, str))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "components").mkdir(parents=True, exist_ok=True)
    lib = Library(args.library)
    # READ ONCE, from the library itself, as render.py reads them per device -
    # never from a device's rendered configs.json: __main__.py runs this
    # indexer alongside the renderers, so nothing they write exists yet.
    families = _pluggable_families()
    connectors = _connector_registry()
    candidates = _pluggable_candidates(args.library)
    load_ref = lambda ref: libwalk.load_contract(ref, args.library)  # noqa: E731
    index = []
    faces_named = named_as_faces(args.library)
    in_bays = seated_in_bays(args.library)
    for root in args.library:
        for cf in sorted(Path(root).glob("components/*/*/v*/contract.yaml")):
            data = load_yaml(cf)
            ns = cf.parents[2].name
            major = cf.parent.name
            ref = f"{ns}/{data['name']}@{major[1:]}"
            entry = {
                "ns": ns, "name": data["name"], "major": major,
                "version": data["version"], "kind": data.get("kind"),
                "class": data.get("class"), "conforms": data.get("conforms"),
                # HOW IT MOVES, which is a different question from what it is and
                # the one a consumer needs to decide layering or ejection. It was
                # written into the contracts and onto the SVG as data-behaviour,
                # and then not carried here - so anything reading this index saw
                # `None` on every part and could only fall back to `class`, which
                # is exactly the fallback the field exists to replace.
                "behaviour": data.get("behaviour"),
                "size": data["size"], "description": data.get("description", ""),
                # WHERE EACH DIMENSION CAME FROM, per dimension, and it is here for the
                # same reason relief-confidence is: without it a value that is IMPOSSIBLE
                # is indistinguishable from one nobody has measured. `known-wrong` is the
                # token that says so, and a consumer should be able to find every one of
                # them without reading 273 files of prose.
                "size-confidence": data.get("size-confidence") or {},
                "size-notes": data.get("size-notes", ""),
                "attrs": data.get("attrs") or {},
                # what a form can change on it - see the schema's `fields`
                "fields": data.get("fields") or {},
                "skins": data.get("skins", ["default"]),
                "elements": sorted((data.get("elements") or {}).keys()),
                # additive: the geometry behind those names, and the relief that
                # acts on them, so a consumer can check a part against a drawing
                # without re-reading the contract
                "element-boxes": {k: {"at": v.get("at"), "size": v.get("size")}
                                  for k, v in (data.get("elements") or {}).items()
                                  if isinstance(v, dict)},
                # A RELIEF MAGNITUDE'S CONFIDENCE, COUNTED, so a consumer does not
                # have to walk the features to find out how much of a part's 3D is
                # sourced. The raw block above already carries the per-feature
                # `confidence`; this is the roll-up, and `unstated` is the point of
                # it - a part whose features say nothing about where their numbers
                # came from looks exactly like one whose numbers were measured, and
                # that is how a vendor modelled entirely from estimates comes to
                # look more complete than one that honestly declared nothing.
                "relief-confidence": _confidence_counts(data),
                # WHAT A NESTED BAY ACCEPTS, which lived only in the contract on
                # disk. 39 components declare bays and 84 bays in total - the
                # A9K modular line cards and SIPs, the Dell 14G risers, the
                # Smartoptics shelf cards - and a consumer holding this index
                # could see that a carrier had been drawn with openings and had
                # no way to learn what goes in one, so no picker could be
                # offered for any of them.
                # NORMALISED TO THE SHAPE A DEVICE BAY ALREADY HAS: a contract
                # writes `size: [55.4, 19.5]` and a device bay carries
                # `size: {w, h}`, and one shape means one code path in the
                # consumer rather than two that have to agree.
                "bays": {bid: {"at": b.get("at"),
                               "size": dict(zip(("w", "h"), b.get("size") or []))
                               if isinstance(b.get("size"), list) else b.get("size"),
                               "accepts": b.get("accepts") or [],
                               **({"default": b["default"]} if "default" in b else {})}
                         for bid, b in sorted((data.get("bays") or {}).items())
                         if isinstance(b, dict)},
                # REF AND ID, not the ref alone. A consumer that has to say
                # what a card's ports ARE needs the id - `d0` is a downstream
                # port and `u0` an upstream one, and the ref they share says
                # only that both are MCX. Publishing refs alone made the DCIM
                # export lose all eighteen interfaces off a 6+12 I/O card the
                # moment it started reading this index instead of the contract.
                # ATTRS TOO, because a placement is more specific than its ref:
                # the same SFP cage is 1G or 10G depending on `attrs.media` and
                # `attrs.speed` on the PART, and without them ten Casa SMM ports
                # exported as 1000base-x when they are 10gbase-x. AND `at`,
                # which used to stay absent on the theory that nothing outside
                # the renderer needs a part's position - wrong: `optical_ports.
                # _front_parts` orders a module's front connectors "across the
                # face by `at.x`", by its own docstring, and reads this index,
                # not the contract. Without `at` here every part's position
                # read as the same default and the sort fell through to
                # comparing the id STRING - silently correct only for ids
                # already in face order (`lc1`..`lc6`), and silently wrong past
                # nine of them (`"lc10" < "lc4"`). Carried here now, omitted
                # when the contract has none, matching `id`/`attrs`.
                # AND `group`, beside the card's own `groups:` below (#511): a
                # card's port says what it is FOR through the card's group, and
                # the DCIM module export reads this index, not the contract - so
                # a group published nowhere here would type every card port as
                # if it had none, and mark no management port mgmt_only.
                # AND `interfaces` (#443), for the same reader: a FELT-B cage
                # that numbers two ports exported one while it stopped here.
                "parts": [{k: p[k] for k in ("ref", "id", "at", "attrs", "group", "interfaces") if k in p}
                          for p in data.get("parts") or []],
                # SPLIT OFF BELOW, not dropped. Both are carried on the entry so
                # everything downstream of here (relief-confidence, the defect
                # register) still reads one object; _split() lifts them out into
                # components-detail.json just before the index is written.
                "_detail": {"provenance": data.get("provenance") or {},
                            "relief": data.get("relief") or {}},
            }
            # ITS OWN CAGES, in its own frame (#484): one per part that
            # presents a pluggable interface or a connector interface (B3,
            # `kind: cage|connector`), by the same core as a device
            # view's `cages[]` (render.slot_entry), with the same keys. A card
            # swapped into a bay at runtime brings them with it; no
            # configuration of the chassis can say where a card's cages are
            # when it is not the card that configuration seats. `occupant` is
            # dropped - a contract seats nothing - and `occupant-attrs` is the
            # card group's side for a cage in one of the card's own `groups:`
            # (#511), empty otherwise. Omitted when there are none.
            cages = component_cages(data, lib, families, candidates, connectors,
                                    face=ref in faces_named, module=ref in in_bays)
            if cages:
                entry["cages"] = cages
            # THE CARD'S OWN PORT GROUPS (#511), in the device `groups:` shape.
            # Omitted when the contract declares none, like `cages`.
            if data.get("groups"):
                entry["groups"] = data["groups"]
            # THE HEAD (docs/pluggables-heads-design.md 4.2), verbatim from the
            # contract: the box a pluggable occupies outside its cage, which a
            # downstream tool that never builds 3D still needs. Omitted when
            # the contract declares none, like `groups`.
            if data.get("head"):
                entry["head"] = data["head"]
            # WHERE IT MATES, in its own frame - the contract's own `mate.at`,
            # never a forwarded one: an occupant mates with its own point
            # (L11). A consumer seating it in a cage solves its `at` from this
            # and the cage's published `mate` (render.seat_at). Omitted when
            # the contract has no mate point.
            cmate = (data.get("connection-points") or {}).get("mate")
            if cmate and cmate.get("at") is not None:
                entry["mate"] = list(cmate["at"])
            files = {}
            for skin in entry["skins"]:
                if not (cf.parent / "skins" / f"{skin}.svg").exists():
                    continue
                w, h = data["size"]["w"], data["size"]["h"]
                svg = ET.Element(f"{{{SVG_NS}}}svg")
                box = preview_box(data, lib, skin, cf.parent / "skins")
                if box is None or box == (0.0, 0.0, float(w), float(h)):
                    svg.set("width", f"{w}mm"); svg.set("height", f"{h}mm")
                    svg.set("viewBox", f"0 0 {w} {h}")
                else:
                    x0, y0, x1, y1 = box
                    vw, vh = round(x1 - x0, 6), round(y1 - y0, 6)
                    svg.set("width", f"{vw:g}mm"); svg.set("height", f"{vh:g}mm")
                    svg.set("viewBox", f"{x0:g} {y0:g} {vw:g} {vh:g}")
                style = ET.SubElement(svg, f"{{{SVG_NS}}}style")
                palette = {}
                g, _ = instance_group(lib, ref, data["name"], [0, 0], None, None,
                                      None, None, skin_name=skin, palette=palette,
                                      resolved={})
                # state_rule, NOT a second copy of it. This built the rule by
                # hand and named the palette value `color`, but state_style()
                # returns (color, alt, mode) - so every component-scoped rule
                # read `--led-color: ('#39b54a', None, 'solid')`, which is not a
                # colour, and no lamp in a standalone component skin ever changed
                # when its state class was set. The device drawings were right
                # the whole time because render.py unpacks the tuple; this file
                # is what the viewer fetches when you swap a module into a bay, so
                # swapped card was the one case a user could actually click.
                extra = "".join(
                    state_rule(f"g[data-ref^='{comp}@'] .state-{name}",
                               f"g[data-ref^='{comp}@'] .state-{name}", *style,
                               seq_name=seq_css_name(comp, name))
                    for (comp, name), style in sorted(palette.items()))
                style.text = STATE_CSS + extra
                svg.append(g)
                ET.indent(svg, space="  ")
                fname = f"{ns}--{data['name']}--{major}--{skin}.svg"
                (out / "components" / fname).write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    + ET.tostring(svg, encoding="unicode") + "\n")
                files[skin] = f"components/{fname}"
            entry["files"] = files
            if data.get("body"):
                sides = {}
                for side in ("left", "right", "top", "bottom", "rear"):
                    sp2 = cf.parent / "skins" / f"body-{side}.svg"
                    if sp2.exists():
                        fname = f"{ns}--{data['name']}--{major}--body-{side}.svg"
                        (out / "components" / fname).write_text(sp2.read_text())
                        sides[side] = f"components/{fname}"
                # A MODULE WITH A REAR FACE HAS ITS BACK DRAWN ALREADY. When no
                # `body-rear.svg` says otherwise, the body's back is that face's
                # compiled drawing, so a pulled cassette carries its MTP out
                # with it instead of leaving a blank box. Same file the device
                # build projects through an open back.
                rref = face_ref(data, "rear")
                if "rear" not in sides and rref:
                    rns, rest = rref.split("/", 1)
                    rname, rmaj = rest.split("@")
                    sides["rear"] = f"components/{rns}--{rname}--v{rmaj}--default.svg"
                entry["body"] = {**data["body"], "sides": sides}
            # A PART'S OTHER DRAWINGS, flattened to refs. The viewer resolves
            # them against this same index, so the nested `{ref: ...}` form
            # would cost bytes on every page load and buy nothing. Omitted
            # entirely when a part has none, which is all but thirteen of them.
            fc = {k: r for k in DIRECTIONS
                  if (r := face_ref(data, k))}
            if fc:
                entry["faces"] = fc
            # THE FIBRE GRAPH, VERBATIM. The exporter reads this file and never
            # the library - `dcim_export.py --dist` opens nothing under
            # library/components - so a contract's `optical` is invisible to the
            # projection until it is published here. Carried whole rather than
            # summarised: `positions` is what a connector contributes, and
            # `paths`, `media`, `polarity` and `unused` are what a module's
            # projection is built from, so a reduced form would only have to be
            # widened again by the first consumer that wanted the rest.
            if data.get("optical"):
                entry["optical"] = data["optical"]
                # THE FIBRE ENDS, NUMBERED ONCE. The explorer labels a fibre by
                # its far end and its vendor front number; the number is
                # optical_ports.front_label's rule and nobody else's, so it is
                # written here beside the paths rather than re-derived in the
                # kit.
                if data["optical"].get("paths"):
                    entry["optical"] = {**data["optical"], "ends": fibre_ends(data, load_ref)}
            index.append(entry)
    totals = {}
    for e in index:
        for k, n in e["relief-confidence"].items():
            totals[k] = totals.get(k, 0) + n
    # every dimension anybody has recorded a confidence for, and - separately and by
    # name - every one currently known to be wrong. The second list is short on purpose
    # and should stay short; it is the library's own defect register for geometry.
    size_totals, known_wrong = {}, []
    for e in index:
        for dim, conf in (e["size-confidence"] or {}).items():
            size_totals[conf] = size_totals.get(conf, 0) + 1
            if conf == "known-wrong":
                known_wrong.append(f"{e['ns']}/{e['name']}@{e['major'][1:]} {dim}")
    # THE INDEX IS TWO FILES, and the reason is what a 3D viewer pays to load it.
    # `provenance` and `relief` are 88% of the bytes here and neither is read by
    # the device viewer, the Explorer or the component browser, which between them
    # fetch this file on every page load. Splitting is NOT deleting: both keys keep
    # every byte they had, keyed by the same ref, one fetch away for anything that
    # actually wants them (library/demo/part.html is the one page that does).
    detail = {}
    for e in index:
        ref = f"{e['ns']}/{e['name']}@{e['major'][1:]}"
        detail[ref] = e.pop("_detail")
    (out / "components.json").write_text(json.dumps(
        {"components": index, "relief-confidence": totals,
         "size-confidence": size_totals,
         "known-wrong": sorted(known_wrong)}, indent=1, sort_keys=True))
    (out / "components-detail.json").write_text(json.dumps(
        {"components": detail}, indent=1, sort_keys=True))
    print(f"compiled {len(index)} components -> {out}/components.json"
          f" (+ components-detail.json)")


if __name__ == "__main__":
    main()
