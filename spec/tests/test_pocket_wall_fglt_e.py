"""nokia/fglt-e stands its sawtooth behind a plate with a window pocket that says how thick
the plate is (`pocket: {depth, wall}`, docs/tilted-facets-design.md), as nokia/fglt-a,
fglt-b, fglt-d, fgut-a and nglt-c do.

Its pocket used to run past the last window to let the lowest cage clear a full-depth
wall, and the mouth then cut over the tips of the ESD and hot-surface triangles. It now
stops at the drawn window and the cage runs back under the plate's edge. Read from the
compiled component drawing, which is what the 3D build reads."""
import math
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

import onebuild

ROOT = pathlib.Path(__file__).resolve().parents[2]
SVG = "{http://www.w3.org/2000/svg}"

CARD = "fglt-e"
LAST = 16
DEPTH = 22.1
WALL = 12.0


def contract():
    return yaml.safe_load((ROOT / f"library/components/nokia/{CARD}/v1/contract.yaml").read_text())


def pocket():
    return next(f for f in contract()["relief"]["features"] if f["node"] == "well")


@pytest.fixture(scope="module")
def drawing():
    index = onebuild.components_index() / "components"
    return ET.parse(index / f"nokia--{CARD}--v1--default.svg").getroot()


def node(root, name):
    return next(e for e in root.iter() if e.get("id") == f"{CARD}--{name}")


def box(el):
    r = el if el.tag == SVG + "rect" else next(el.iter(SVG + "rect"))
    return tuple(float(r.get(k)) for k in ("x", "y", "width", "height"))


def test_the_built_pocket_carries_the_plates_back_face(drawing):
    well = node(drawing, "well")
    assert float(well.get("data-depth")) == pytest.approx(DEPTH, abs=0.001)
    assert float(well.get("data-wall-depth")) == pytest.approx(WALL, abs=0.01)
    assert pocket()["pocket"] == {"depth": DEPTH, "wall": WALL}


def test_the_pocket_box_ends_where_the_last_window_does(drawing):
    x, y, w, h = box(node(drawing, "well"))
    face = box(node(drawing, f"face-{LAST}"))
    assert (x, w) == (face[0], face[2])
    assert y + h == pytest.approx(face[1] + face[3], abs=0.01)
    assert contract()["elements"]["well"]["size"][1] == pytest.approx(h, abs=0.01)


def test_the_pocket_no_longer_reaches_its_hazard_triangles(drawing):
    _, y, _, h = box(node(drawing, "well"))
    for name in ("hazard-esd", "hazard-hot"):
        poly = next(node(drawing, name).iter(SVG + "polygon"))
        top = min(float(p.split(",")[1]) for p in poly.get("points").split())
        assert y + h <= top - 3.0, f"the pocket mouth cuts {name}"


def test_the_wedge_below_the_last_window_is_not_a_facet():
    c = contract()
    sunk = {f["node"] for f in c["relief"]["features"] if f.get("facet")}
    assert f"return-{LAST}" not in sunk
    assert {f"face-{n}" for n in range(1, LAST + 1)} <= sunk
    assert {f"return-{n}" for n in range(1, LAST)} <= sunk


def test_the_wall_is_no_deeper_than_the_teeth_crests():
    """The card's figure shows the tooth tips touching the plate's back, so a wall deeper
    than a crest would stand a wall across the teeth."""
    c = contract()
    for f in c["relief"]["features"]:
        if not f.get("facet"):
            continue
        el = c["elements"][f["node"]]
        crest = f["lift"] + el["size"][1] * math.tan(math.radians(f["facet"]["deg"]))
        assert crest <= 0.001 and -crest >= WALL - 0.05, (f["node"], crest, WALL)


def test_the_wall_is_an_estimate_and_says_where_it_comes_from():
    p = pocket()
    assert p["confidence"] == "estimated"
    source = " ".join(p["source"].split())
    assert "wall" in source and str(WALL) in source and "Figure 150" in source
