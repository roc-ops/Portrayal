"""nokia/fglt-a stands its sawtooth behind a plate with a window pocket that says
how thick the plate is (`pocket: {depth, wall}`, docs/tilted-facets-design.md).

The pocket used to run 11 mm past the last window to let the lowest cage clear a
full-depth wall, and that cut the top of the barcode label. It now stops at the
drawn windows and the cage runs back under the plate's edge. Read from the
compiled component drawing, which is what the 3D build reads."""
import math
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

import onebuild

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "library/components/nokia/fglt-a/v1/contract.yaml"
SVG = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def drawing():
    f = onebuild.components_index() / "components/nokia--fglt-a--v1--default.svg"
    return ET.parse(f).getroot()


@pytest.fixture(scope="module")
def contract():
    return yaml.safe_load(CONTRACT.read_text())


def node(root, name):
    return next(e for e in root.iter() if e.get("id") == f"fglt-a--{name}")


def box(el):
    r = el if el.tag == SVG + "rect" else next(el.iter(SVG + "rect"))
    return tuple(float(r.get(k)) for k in ("x", "y", "width", "height"))


def test_the_built_pocket_carries_the_plates_back_face(drawing):
    well = node(drawing, "well")
    assert well.get("data-depth") == "28.38"
    assert float(well.get("data-wall-depth")) == pytest.approx(12.0, abs=0.01)


def test_the_pocket_box_is_the_drawn_windows(drawing, contract):
    x, y, w, h = box(node(drawing, "well"))
    # window 8 ends where its tooth does, at 355.6; the first window starts at 43
    face8 = box(node(drawing, "face-8"))
    assert y == pytest.approx(43.0)
    assert y + h == pytest.approx(face8[1] + face8[3], abs=0.01) == pytest.approx(355.6, abs=0.01)
    assert (x, w) == (2.5, 20.5)
    assert contract["elements"]["well"]["size"][1] == pytest.approx(h, abs=0.01)


def test_the_pocket_no_longer_reaches_the_barcode_label(drawing):
    _, y, _, h = box(node(drawing, "well"))
    label_top = box(node(drawing, "barcode-label"))[1]
    assert y + h <= label_top - 4.0, "the pocket mouth cuts the barcode label"


def test_the_wall_is_no_deeper_than_the_teeth_crests(contract):
    """The plate's back face is where the tooth tips touch it: a wall deeper than
    the crest would stand a wall across the teeth."""
    wall = next(f for f in contract["relief"]["features"] if f["node"] == "well")["pocket"]["wall"]
    for f in contract["relief"]["features"]:
        if not f.get("facet"):
            continue
        el = contract["elements"][f["node"]]
        crest = f["lift"] + el["size"][1] * math.tan(math.radians(f["facet"]["deg"]))
        assert crest <= 0.001 and -crest >= wall - 0.05, (f["node"], crest, wall)
