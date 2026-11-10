"""nokia/fglt-d, fgut-a and nglt-c stand their sawtooth behind a plate with a window
pocket that says how thick the plate is (`pocket: {depth, wall}`,
docs/tilted-facets-design.md), as nokia/fglt-b and fglt-a do.

Each pocket used to run past its last window to let the lowest cage clear a full-depth
wall, and the mouth then cut over printed art (the hazard triangles of the FGLT-D and
FGUT-A) or past the end of the recess (NGLT-C). It now stops at the drawn windows and the
cage runs back under the plate's edge. Read from the compiled component drawing, which is
what the 3D build reads."""
import math
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

import onebuild

ROOT = pathlib.Path(__file__).resolve().parents[2]
SVG = "{http://www.w3.org/2000/svg}"

# card -> (last tooth, floor depth, wall as the contract states it, the teeth's crests touch the wall)
CARDS = {
    "fglt-d": (16, 22.95, 13.5, True),
    "fgut-a": (16, 22.77, 13.0, True),
    "nglt-c": (4, 22.38, 12.0, False),
}


def contract_of(card):
    return yaml.safe_load((ROOT / f"library/components/nokia/{card}/v1/contract.yaml").read_text())


def pocket_of(contract):
    return next(f for f in contract["relief"]["features"] if f["node"] == "well")


@pytest.fixture(scope="module")
def drawings():
    index = onebuild.components_index() / "components"
    return {c: ET.parse(index / f"nokia--{c}--v1--default.svg").getroot() for c in CARDS}


def node(root, card, name):
    return next(e for e in root.iter() if e.get("id") == f"{card}--{name}")


def box(el):
    r = el if el.tag == SVG + "rect" else next(el.iter(SVG + "rect"))
    return tuple(float(r.get(k)) for k in ("x", "y", "width", "height"))


@pytest.mark.parametrize("card", CARDS)
def test_the_built_pocket_carries_the_plates_back_face(drawings, card):
    _, depth, wall, _ = CARDS[card]
    well = node(drawings[card], card, "well")
    assert float(well.get("data-depth")) == pytest.approx(depth, abs=0.001)
    assert float(well.get("data-wall-depth")) == pytest.approx(wall, abs=0.01)
    assert pocket_of(contract_of(card))["pocket"] == {"depth": depth, "wall": wall}


@pytest.mark.parametrize("card", CARDS)
def test_the_pocket_box_ends_where_the_last_window_does(drawings, card):
    last = CARDS[card][0]
    c = contract_of(card)
    x, y, w, h = box(node(drawings[card], card, "well"))
    face = box(node(drawings[card], card, f"face-{last}"))
    assert (x, w) == (face[0], face[2])
    assert y + h == pytest.approx(face[1] + face[3], abs=0.01)
    assert c["elements"]["well"]["size"][1] == pytest.approx(h, abs=0.01)


def test_the_fglt_d_pocket_no_longer_reaches_its_hazard_triangles(drawings):
    root = drawings["fglt-d"]
    _, y, _, h = box(node(root, "fglt-d", "well"))
    for name in ("hazard-esd", "hazard-hot"):
        poly = next(node(root, "fglt-d", name).iter(SVG + "polygon"))
        top = min(float(p.split(",")[1]) for p in poly.get("points").split())
        assert y + h <= top - 3.0, f"the pocket mouth cuts {name}"


def test_the_fgut_a_pocket_no_longer_reaches_its_hazard_triangles(drawings):
    root = drawings["fgut-a"]
    _, y, _, h = box(node(root, "fgut-a", "well"))
    marks = node(root, "fgut-a", "silkscreen")
    tops = [float(m.group(1)) for p in marks.iter(SVG + "path")
            for m in [re.match(r"M [\d.]+ ([\d.]+) L [\d.]+ [\d.]+ L [\d.]+ [\d.]+ Z", p.get("d", ""))] if m]
    assert len(tops) == 2, "an ESD triangle and a hot-surface triangle"
    assert y + h <= min(tops) - 2.0, "the pocket mouth cuts a hazard triangle"


@pytest.mark.parametrize("card", CARDS)
def test_the_wedge_below_the_last_window_is_not_a_facet(card):
    last = CARDS[card][0]
    sunk = {f["node"] for f in contract_of(card)["relief"]["features"] if f.get("facet")}
    assert f"return-{last}" not in sunk
    assert {f"face-{n}" for n in range(1, last + 1)} <= sunk
    assert {f"return-{n}" for n in range(0, last)} & set(contract_of(card)["elements"]) <= sunk


@pytest.mark.parametrize("card", [c for c, v in CARDS.items() if v[3]])
def test_the_wall_is_no_deeper_than_the_teeth_crests(card):
    """Where the card's own figure shows the tooth tips touching the plate's back, a wall
    deeper than a crest would stand a wall across the teeth."""
    c = contract_of(card)
    wall = pocket_of(c)["pocket"]["wall"]
    for f in c["relief"]["features"]:
        if not f.get("facet"):
            continue
        el = c["elements"][f["node"]]
        crest = f["lift"] + el["size"][1] * math.tan(math.radians(f["facet"]["deg"]))
        assert crest <= 0.001 and -crest >= wall - 0.05, (f["node"], crest, wall)


@pytest.mark.parametrize("card", CARDS)
def test_the_wall_is_an_estimate_and_says_where_it_comes_from(card):
    p = pocket_of(contract_of(card))
    assert p["confidence"] == "estimated"
    source = " ".join(p["source"].split())
    assert "wall" in source and str(CARDS[card][2]) in source
    if card == "nglt-c":
        assert "borrowed" in source and "no page prints" in source
