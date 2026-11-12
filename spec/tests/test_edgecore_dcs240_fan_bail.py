"""The DCS240 fan tray's pull handle is a bail, and its relief says so.

The quick start guide's Fan Tray Replacement figure (page 1) draws the tray three-quarter with the handle swung out: a moulded
U-loop on two pivots that you hook a finger under, not a straight grip. The rear elevation flattens it to the bar the part drew.
So edgecore/dcs240-fan carries `uhandle` rather than `bar` + `lift`, as the library's other fan trays whose figures show a bail do.
How far the loop stands off the face is dimensioned nowhere, so the figure is an estimate and the contract says whose.

These read the real library contract only. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PART = ROOT / "library" / "components" / "edgecore" / "dcs240-fan" / "v1" / "contract.yaml"


def words(text):
    return " ".join(str(text).split())


@pytest.fixture(scope="module")
def contract():
    return yaml.safe_load(PART.read_text())


@pytest.fixture(scope="module")
def handle(contract):
    nodes = [f for f in contract["relief"]["features"] if f["node"] == "handle"]
    assert len(nodes) == 1
    return nodes[0]


def test_the_handle_is_a_bail_and_not_a_bar(handle):
    assert "uhandle" in handle
    assert "bar" not in handle and "lift" not in handle


def test_the_standoff_is_an_estimate_and_says_so(handle):
    assert handle["confidence"] == "estimated"
    source = words(handle["source"])
    assert "Fan Tray Replacement" in source
    assert "not dimensioned" in source or "no document" in source


def test_the_loop_has_legs(contract, handle):
    # uhandle's leg is (far - r) - dia: under about 1.5 tube diameters the bends are the whole handle.
    dia = handle.get("dia", contract["elements"]["handle"]["size"][1])
    assert handle["uhandle"] >= 1.5 * dia


def test_the_drawn_face_is_unchanged(contract):
    # the figure settles the shape of the grip, not where the elevation puts it
    assert contract["elements"]["handle"] == {"at": [4.9, 18.4], "size": [38.75, 3.2], "class": "latch"}
    assert contract["size"] == {"w": 48.5, "h": 40.0}


def test_the_provenance_records_the_figure(contract):
    note = words(contract["provenance"]["the-handle-is-a-bail"])
    assert "page 1" in note
    assert "Fan Tray Replacement" in note
