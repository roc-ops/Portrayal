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
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from portrayal.manifest import load_yaml

from portrayal.faces import DIRECTIONS, face_ref  # noqa: E402
from portrayal.render import (SVG_NS, STATE_CSS, Library, instance_group,  # noqa: E402
                    seq_css_name, state_rule)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "components").mkdir(parents=True, exist_ok=True)
    lib = Library(args.library)
    index = []
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
                "parts": [{k: p[k] for k in ("ref", "id", "at", "attrs") if k in p}
                          for p in data.get("parts") or []],
                # SPLIT OFF BELOW, not dropped. Both are carried on the entry so
                # everything downstream of here (relief-confidence, the defect
                # register) still reads one object; _split() lifts them out into
                # components-detail.json just before the index is written.
                "_detail": {"provenance": data.get("provenance") or {},
                            "relief": data.get("relief") or {}},
            }
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
                svg.set("width", f"{w}mm"); svg.set("height", f"{h}mm")
                svg.set("viewBox", f"0 0 {w} {h}")
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
