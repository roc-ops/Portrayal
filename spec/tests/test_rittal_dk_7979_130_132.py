"""The Rittal DK 7979.130 and DK 7979.132 PDUs.

What is true of the library: each device places the outlets its maker's table
counts, in the three phase groups its circuit diagram draws, on the parts the
library already holds; its front is tiled end to end by the cells of the
dimensioned drawing; and the two attachments on its back stand the dimensioned
span apart. Reads the device sources only; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

C13, C19 = "std/c13-outlet@1", "std/c19-outlet@1"
LENGTH = 695
# model -> (outlets of the table, outlets in one phase group)
DEVICES = {
    "dk-7979-130": (Counter({C19: 9}), Counter({C19: 3})),
    "dk-7979-132": (Counter({C13: 6, C19: 6}), Counter({C13: 2, C19: 2})),
}


def _device(name):
    return yaml.safe_load((LIB / "devices" / "rittal" / name / "device.yaml").read_text())


def _placements(name, view):
    return _device(name)["views"][view]["components"]["placements"]


def _outlets(name):
    return [p for p in _placements(name, "front") if p["id"].startswith("outlet-")]


@pytest.mark.parametrize("name", DEVICES)
def test_the_chassis_is_the_drawn_strip(name):
    chassis = _device(name)["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (44, LENGTH, 72.1)
    assert chassis["mount"] == "rack-side"


@pytest.mark.parametrize("name", DEVICES)
def test_every_face_is_stated(name):
    views = _device(name)["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for face in ("top", "bottom", "left", "right"):
        assert views[face].get("empty"), f"{face} states neither parts nor why it is empty"
    assert views["front"]["size"] == {"w": 44, "h": LENGTH}


@pytest.mark.parametrize("name", DEVICES)
def test_the_outlets_are_the_ones_the_maker_counts(name):
    assert Counter(p["ref"] for p in _outlets(name)) == DEVICES[name][0]


@pytest.mark.parametrize("name", DEVICES)
def test_each_phase_group_is_the_circuit_diagrams_group(name):
    outlets = _outlets(name)
    for n, line in enumerate(("L1", "L2", "L3"), start=1):
        group = [p for p in outlets if p["group"] == f"outlets-l{n}"]
        assert Counter(p["ref"] for p in group) == DEVICES[name][1]
        assert all(p["lines"] == [line, "N"] and p["fed-by"] == "input" for p in group)


@pytest.mark.parametrize("name", DEVICES)
def test_the_cord_is_the_one_input(name):
    inputs = [p for p in _placements(name, "front") if p["id"] == "input"]
    assert [p["ref"] for p in inputs] == ["rittal/pdu-cord-cee-16a@1"]
    power = _device(name)["attrs"]["power"]
    assert power["input-cord"] == "fixed"
    assert power["input-phase"] == "three" and power["input-current-a"] == 16
    assert "plug-rating-a" not in power


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_is_tiled_end_to_end_by_the_cells(name):
    decor = _device(name)["views"]["front"]["panel"]["decor"]
    cells = sorted(decor, key=lambda d: d["at"][1])
    edge = 0.0
    for cell in cells:
        assert abs(cell["at"][1] - edge) < 0.15, f"{cell['id']} leaves a gap or overlaps"
        edge = cell["at"][1] + cell["size"][1]
    assert abs(edge - LENGTH) < 0.15


@pytest.mark.parametrize("name", DEVICES)
def test_each_outlet_lies_inside_the_plate_of_its_phase(name):
    decor = {d["id"]: d for d in _device(name)["views"]["front"]["panel"]["decor"]}
    for p in _outlets(name):
        plate = decor["plate-l" + p["group"][-1]]
        top, bottom = plate["at"][1], plate["at"][1] + plate["size"][1]
        assert top < p["at"][1] and p["at"][1] + 22 < bottom, f"{p['id']} is outside its plate"


@pytest.mark.parametrize("name", DEVICES)
def test_the_two_buttons_are_the_dimensioned_span_apart(name):
    buttons = [p for p in _placements(name, "rear") if p["id"].startswith("button-")]
    assert len(buttons) == 2
    assert abs(abs(buttons[0]["at"][1] - buttons[1]["at"][1]) - 622.3) < 0.1


@pytest.mark.parametrize("name", DEVICES)
def test_the_device_says_only_what_a_document_says(name):
    device = _device(name)
    assert device["attrs"]["power"]["capacity-kw"] == 11
    assert device["attrs"]["management"]["metering-scope"] == "none"
    assert device["attrs"]["lifecycle"]["eol"] == "none-announced"
    for key in ("colour", "numbering"):
        assert any(g["what"] == key for g in device["gaps"]), f"the {key} gap is not stated"
