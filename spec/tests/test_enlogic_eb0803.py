"""The Enlogic EB0803 PDU and the parts it brings.

What is true of the library: the maker is registered, the device places the outlets
its data sheet counts in three breakered banks, the three new parts exist with their
sources, and the one input is a fixed cord that exports a NEMA L21-30P power port.
Reads the contracts and the device source; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _contract(part):
    return yaml.safe_load((LIB / "components" / "enlogic" / part / "v1" / "contract.yaml").read_text())


def _device():
    return yaml.safe_load((LIB / "devices" / "enlogic" / "eb0803" / "device.yaml").read_text())


def _placements(view):
    return _device()["views"][view]["components"]["placements"]


def test_the_maker_is_registered():
    vendors = yaml.safe_load((ROOT / "spec" / "schemas" / "vendors.yaml").read_text())["vendors"]
    assert vendors["enlogic"]["display"] == "Enlogic"
    assert vendors["enlogic"]["source"]


def test_the_chassis_is_the_drawn_strip():
    device = _device()
    chassis = device["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (52, 1490, 53)
    assert chassis["mount"] == "rack-side"
    assert device["manufacturer"] == "Enlogic" and device["model"] == "EB0803"


def test_every_face_is_stated():
    views = _device()["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}


def test_the_outlets_are_the_ones_the_data_sheet_counts():
    outlets = [p for p in _placements("front") if p["id"].startswith("outlet-")]
    assert Counter(p["ref"] for p in outlets) == {
        "std/c13-outlet@1": 24,
        "std/c19-outlet@1": 3,
        "std/nema-5-20r@1": 3,
    }


def test_each_bank_is_ten_outlets_behind_its_breaker():
    outlets = [p for p in _placements("front") if p["id"].startswith("outlet-")]
    breakers = {p["id"]: p for p in _placements("front") if p["ref"] == "enlogic/eb-breaker-20a-2p@1"}
    assert sorted(breakers) == ["breaker-b1", "breaker-b2", "breaker-b3"]
    for n, lines in ((1, ["L1", "L2"]), (2, ["L2", "L3"]), (3, ["L3", "L1"])):
        bank = [p for p in outlets if p["group"] == f"outlets-b{n}"]
        assert Counter(p["ref"] for p in bank) == {
            "std/c13-outlet@1": 8, "std/c19-outlet@1": 1, "std/nema-5-20r@1": 1}
        assert all(p["through"] == f"breaker-b{n}" and p["fed-by"] == "input" for p in bank)
        assert breakers[f"breaker-b{n}"]["lines"] == lines
        assert breakers[f"breaker-b{n}"]["attrs"]["bank"] == f"B{n}"


def test_the_banks_repeat_at_the_drawn_pitch():
    breakers = sorted(p["at"][1] for p in _placements("front") if p["ref"] == "enlogic/eb-breaker-20a-2p@1")
    assert abs((breakers[1] - breakers[0]) - 461.18) < 0.05
    assert abs((breakers[2] - breakers[1]) - 461.18) < 0.05


def test_the_cord_is_the_one_input():
    inputs = [p for p in _placements("top") if p["id"] == "input"]
    assert [p["ref"] for p in inputs] == ["enlogic/pdu-cord-l21-30p@1"]
    assert _contract("pdu-cord-l21-30p")["attrs"]["plug"] == "nema-l21-30p"
    power = _device()["attrs"]["power"]
    assert power["input-cord"] == "fixed" and power["input-plug"] == "nema-l21-30p"
    assert power["input-phase"] == "three" and power["input-wiring"] == "wye"


def test_the_two_buttons_are_the_dimensioned_span_apart():
    buttons = [p for p in _placements("rear") if p["id"].startswith("button-")]
    assert len(buttons) == 2
    assert abs(abs(buttons[0]["at"][1] - buttons[1]["at"][1]) - 1244.0) < 0.1
    assert _contract("pdu-mounting-button")["mates"] == "pdu-button"


def test_the_breaker_says_where_its_figures_come_from():
    contract = _contract("eb-breaker-20a-2p")
    assert contract["class"] == "breaker" and contract["attrs"]["poles"] == 2
    assert {"bank-color", "bank", "lines", "branch"} <= set(contract["fields"])
    assert "DISAGREE" in contract["provenance"]["size"]


def test_what_no_source_dimensions_is_declared_an_estimate():
    cord = _contract("pdu-cord-l21-30p")
    assert cord["size-confidence"]["h"] == "estimated"
    assert "estimated" in cord["provenance"]["size"]


def test_the_device_says_only_what_a_document_says():
    device = _device()
    assert "weight-kg" not in device["attrs"]["physical"]
    gaps = {g["what"] for g in device["gaps"]}
    assert {"input-voltage", "weight", "colour"} <= gaps
