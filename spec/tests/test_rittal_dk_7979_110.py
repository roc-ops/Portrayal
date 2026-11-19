"""The Rittal DK 7979.110 single-phase PDU and its fixed cord.

What is true of the library: the device places the twelve IEC C13 and the one
IEC C19 its maker's table counts, in the three blocks its circuit diagram
draws, on the parts the library already holds; its single-phase input is a
fixed cord with a 16 A CEE plug of three wires, a part of its own beside the
three-phase cord; its front is tiled end to end by the cells of the
dimensioned drawing; and the two attachments on its back stand the
dimensioned span apart. Reads the device and component sources and the
exporter's tables; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export, dcim_registers

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

C13, C19 = "std/c13-outlet@1", "std/c19-outlet@1"
CORD = "rittal/pdu-cord-cee-16a-1p@1"
LENGTH = 695


def _device():
    return yaml.safe_load((LIB / "devices" / "rittal" / "dk-7979-110" / "device.yaml").read_text())


def _contract():
    path = LIB / "components" / "rittal" / "pdu-cord-cee-16a-1p" / "v1" / "contract.yaml"
    return yaml.safe_load(path.read_text())


def _placements(view):
    return _device()["views"][view]["components"]["placements"]


def _outlets():
    return [p for p in _placements("front") if p["id"].startswith("outlet-")]


def test_the_chassis_is_the_drawn_strip():
    chassis = _device()["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (44, LENGTH, 72.1)
    assert chassis["mount"] == "rack-side"


def test_every_face_is_stated():
    views = _device()["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for face in ("top", "bottom", "left", "right"):
        assert views[face].get("empty"), f"{face} states neither parts nor why it is empty"
    assert views["front"]["size"] == {"w": 44, "h": LENGTH}


def test_the_outlets_are_the_ones_the_maker_counts():
    assert Counter(p["ref"] for p in _outlets()) == Counter({C13: 12, C19: 1})


def test_the_circuit_diagrams_three_blocks_are_the_groups():
    outlets = _outlets()
    blocks = Counter(p["group"] for p in outlets)
    assert sorted(blocks.values()) == [1, 6, 6]
    for group in blocks:
        kinds = {p["ref"] for p in outlets if p["group"] == group}
        assert len(kinds) == 1, f"{group} mixes outlet types"
    assert all(p["fed-by"] == "input" for p in outlets)
    assert all("lines" not in p for p in outlets), "a single-phase unit has no phase to name"


def test_the_outlets_count_from_the_foot_in_the_drawn_order():
    ys = [p["at"][1] for p in _outlets()]
    # the cord is at the foot, the highest y; outlet 1 is nearest it
    assert ys == sorted(ys, reverse=True)
    assert [p["ref"] for p in _outlets()] == [C13] * 12 + [C19]


def test_the_cord_is_the_one_input():
    inputs = [p for p in _placements("front") if p["id"] == "input"]
    assert [p["ref"] for p in inputs] == [CORD]
    power = _device()["attrs"]["power"]
    assert power["input-cord"] == "fixed"
    assert power["input-phase"] == "single" and power["input-current-a"] == 16
    assert "input-wiring" not in power and "plug-rating-a" not in power


def test_the_cord_part_is_the_single_phase_plug():
    contract = _contract()
    assert contract["class"] == "inlet" and contract["version"] == "1.0.0"
    attrs = contract["attrs"]
    assert attrs["cord-wires"] == 3 and attrs["cord-length-m"] == 3
    assert attrs["plug"] == "cee-16a-1p-n-pe"
    assert "unmated" in contract


def test_the_exporter_knows_the_cord_as_an_other_power_port_with_a_label():
    assert dcim_export.PART_POWER["rittal/pdu-cord-cee-16a-1p"] == "other"
    assert "16 A" in dcim_registers.POWER_LABEL["rittal/pdu-cord-cee-16a-1p"]
    assert "1P" in dcim_registers.POWER_LABEL["rittal/pdu-cord-cee-16a-1p"]


def test_the_front_is_tiled_end_to_end_by_the_cells():
    decor = _device()["views"]["front"]["panel"]["decor"]
    edge = 0.0
    for cell in sorted(decor, key=lambda d: d["at"][1]):
        assert abs(cell["at"][1] - edge) < 0.15, f"{cell['id']} leaves a gap or overlaps"
        edge = cell["at"][1] + cell["size"][1]
    assert abs(edge - LENGTH) < 0.15


def test_each_outlet_lies_inside_one_cell_of_its_own_group():
    decor = _device()["views"]["front"]["panel"]["decor"]
    plates = [d for d in decor if d["kind"] == "phase-plate"]
    assert len(plates) == 3
    for p in _outlets():
        height = 27.7 if p["ref"] == C19 else 22
        inside = [d for d in plates if d["at"][1] < p["at"][1]
                  and p["at"][1] + height < d["at"][1] + d["size"][1]]
        assert len(inside) == 1, f"{p['id']} is not inside exactly one plate"


def test_the_two_buttons_are_the_dimensioned_span_apart():
    buttons = [p for p in _placements("rear") if p["id"].startswith("button-")]
    assert len(buttons) == 2
    assert abs(abs(buttons[0]["at"][1] - buttons[1]["at"][1]) - 622.3) < 0.1


def test_the_device_says_only_what_a_document_says():
    device = _device()
    assert device["attrs"]["power"]["capacity-kw"] == 3.7
    assert device["attrs"]["management"]["metering-scope"] == "none"
    assert device["attrs"]["lifecycle"]["eol"] == "none-announced"
    for key in ("colour", "numbering", "group-plates"):
        assert any(g["what"] == key for g in device["gaps"]), f"the {key} gap is not stated"
