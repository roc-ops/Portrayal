"""A node that stands proud is moved to the FRONT of the drawing, over its own art.

render.py raises a relief node to the end of the instance group whenever the
component composes parts:

    if contract.get("parts") and any(feat.get(k) is not None
                                     for k in ("out", "cyl", "bar", "uhandle", "dome")) ...:
        g.remove(node); g.append(node)

which is right for what it was written for - a bezel plate has to paint over the
cages seated in it - and wrong for anything the node's own skin draws INSIDE it.
Those siblings were painted before it in the skin's order, the raise puts the
node in front of them, and they are gone. The base plate is already excluded;
nothing excludes a raised block in the middle of a face.

WHAT IT COST. common/mpo-flange-adapter@1's housing stands 3.5 off a cassette
back and the MT end face - the keyed opening, the plug, the ferrule, twelve
fibres and two guide pins - is drawn inside it. The adapter composes two screws,
so the housing was raised, and every MTP port on every FHD cassette back became a
blank slab. In 3D too: a cavity's floor is cut from its own group RENDERED
STANDALONE, so the same order buried the same art there. The fix is the pattern
common/lc-duplex-v-adapter@4 already uses for its bores - the opening is an
`evenodd` HOLE in the raised shape, so what is behind shows through however late
it paints.

This reads the SKIN, not the compiled drawing, because it is the skin's author
who can act on it. Boxes come from lint's own `_paint_box`, so "covers" means
paint rather than bounding rectangle: an unfilled stroke buries nothing.
"""
import pathlib
import xml.etree.ElementTree as ET

import yaml
from portrayal.lint import _SVG_NS, _paint_box, _subpaths

ROOT = pathlib.Path(__file__).resolve().parents[2]

RAISERS = ("out", "cyl", "bar", "uhandle", "dome")
NONDRAWING = ("title", "defs", "style", "desc", "metadata")

# KNOWN, NAMED, AND NOT WAIVED AWAY. Both are the same defect in a supply's
# handle, and both are cheap to fix and expensive to land: the two components sit
# in 17 devices between them, so correcting their art bumps every one of those
# device versions and their locks. They are recorded here rather than left to a
# sweep nobody runs - see roc-ops/Portrayal#498.
EXEMPT = {
    ("ufispace/psu-302-ac@1", "handle", "handle-grip"):
        "the U-handle is raised over the darker grip pill drawn inside it",
    ("edgecore/eps112-psu-ac@1", "handle", "handle-screws"):
        "the U-handle is raised over the two screws drawn on it",
}


def _box(el):
    """The paint box of a top-level skin child, unioning a group's children."""
    if el.tag.replace(_SVG_NS, "") == "g":
        if el.get("transform"):
            return "unsure"
        boxes = []
        for child in el.iter():
            if child is el or child.tag.replace(_SVG_NS, "") == "g":
                continue
            b = _paint_box(child)
            if b == "unsure":
                return "unsure"
            if b:
                boxes.append(b)
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
    return _paint_box(el)


def _holes(el):
    """Boxes of an evenodd path's inner subpaths - art there is not buried."""
    if el.tag.replace(_SVG_NS, "") != "path" or el.get("fill-rule") != "evenodd":
        return []
    return [(min(p[0] for p in ring), min(p[1] for p in ring),
             max(p[0] for p in ring), max(p[1] for p in ring))
            for ring in _subpaths(el.get("d") or "")[1:]]


def _inside(inner, outer, eps=0.01):
    return (inner[0] >= outer[0] - eps and inner[1] >= outer[1] - eps
            and inner[2] <= outer[2] + eps and inner[3] <= outer[3] + eps)


def _burials():
    """(ref, raised id, buried id) for every raised node that covers a sibling."""
    found, compared = [], 0
    for cf in sorted((ROOT / "library" / "components").rglob("contract.yaml")):
        data = yaml.safe_load(cf.read_text())
        if not data.get("parts"):
            continue                       # render.py only raises when parts exist
        raised = [f["node"] for f in (data.get("relief") or {}).get("features") or []
                  if any(f.get(k) is not None for k in RAISERS)]
        if not raised:
            continue
        ref = f"{cf.parts[-4]}/{data['name']}@{cf.parts[-2][1:]}"
        for skin in data.get("skins") or ["default"]:
            sp = cf.parent / "skins" / f"{skin}.svg"
            if not sp.exists():
                continue
            try:
                kids = [c for c in ET.parse(sp).getroot()
                        if c.tag.replace(_SVG_NS, "") not in NONDRAWING]
            except ET.ParseError:
                continue
            for i, el in enumerate(kids):
                # the base plate is the skin's first drawing child and render.py
                # never raises it, for exactly this reason
                if i == 0 or el.get("id") not in raised:
                    continue
                box = _box(el)
                if box in (None, "unsure"):
                    continue
                holes = _holes(el)
                for j, other in enumerate(kids):
                    # another raised node is moved too, so it is not buried by this
                    if j == i or other.get("id") in raised:
                        continue
                    ob = _box(other)
                    if ob in (None, "unsure"):
                        continue
                    compared += 1
                    if _inside(ob, box) and not any(_inside(ob, h) for h in holes):
                        found.append((ref, el.get("id"), other.get("id")))
    return found, compared


def test_no_raised_node_buries_art_drawn_inside_it():
    found, compared = _burials()
    assert compared > 2000, (
        f"only {compared} sibling pairs were measured, so this sweep is not "
        "reading the library it was written for - has `relief.features` or the "
        "skin layout changed?")
    unexpected = [f for f in found if f not in EXEMPT]
    assert not unexpected, (
        "a raised node is moved in front of art its own skin draws inside it, "
        "which deletes that art in 2D and from the cavity floors in 3D:\n  "
        + "\n  ".join(f"{ref}: {over} buries {under}" for ref, over, under in unexpected))


def test_every_exemption_is_still_a_real_one():
    """An exemption that no longer describes anything is a lie the next reader
    inherits - and the whole point of naming these two is that they get fixed."""
    found = set(_burials()[0])
    stale = sorted(k for k in EXEMPT if k not in found)
    assert not stale, ("these exemptions no longer match anything - the art was "
                       f"fixed, so delete them: {stale}")
