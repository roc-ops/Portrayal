"""The Rittal DK 7979.175 PDU and the parts it brings.

What is true of the library: the device places the outlets its maker's table
and drawing count, the three new connector parts are registered and mated, and
whatever the sources do not dimension is declared an estimate. Reads the
contracts and the device source; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _contract(ns, part):
    return yaml.safe_load((LIB / "components" / ns / part / "v1" / "contract.yaml").read_text())


def _device():
    return yaml.safe_load((LIB / "devices" / "rittal" / "dk-7979-175" / "device.yaml").read_text())


def _placements(view):
    return _device()["views"][view]["components"]["placements"]


def test_the_chassis_is_the_drawn_strip():
    chassis = _device()["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (44, 1094, 72.1)
    assert chassis["mount"] == "rack-side"


def test_every_face_is_stated():
    views = _device()["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for name in ("top", "bottom", "left", "right"):
        assert views[name].get("empty"), f"{name} states neither parts nor why it is empty"


def test_the_outlets_are_the_ones_the_maker_counts():
    outlets = [p for p in _placements("front") if p["id"].startswith("outlet-")]
    assert Counter(p["ref"] for p in outlets) == {
        "std/c13-outlet@1": 18,
        "std/c19-outlet@1": 3,
        "rittal/cee-7-3-outlet@1": 6,
    }


def test_each_phase_group_is_six_c13_one_c19_and_two_sockets():
    outlets = [p for p in _placements("front") if p["id"].startswith("outlet-")]
    for n, line in enumerate(("L1", "L2", "L3"), start=1):
        group = [p for p in outlets if p["group"] == f"outlets-l{n}"]
        assert Counter(p["ref"] for p in group) == {
            "std/c13-outlet@1": 6,
            "std/c19-outlet@1": 1,
            "rittal/cee-7-3-outlet@1": 2,
        }
        assert all(p["lines"] == [line, "N"] and p["fed-by"] == "input" for p in group)


def test_the_cord_is_the_one_input():
    inputs = [p for p in _placements("front") if p["id"] == "input"]
    assert [p["ref"] for p in inputs] == ["rittal/pdu-cord-cee-16a@1"]
    assert _device()["attrs"]["power"]["input-cord"] == "fixed"


def test_the_two_buttons_are_the_dimensioned_span_apart():
    buttons = [p for p in _placements("rear") if p["id"].startswith("button-")]
    assert len(buttons) == 2
    assert abs(abs(buttons[0]["at"][1] - buttons[1]["at"][1]) - 933.45) < 0.1


def test_the_socket_has_its_key_and_its_mate():
    key = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]["cee-7-3"]
    assert "standard" not in key, "no standard sheet is held, so the key cites none"
    assert _contract("rittal", "cee-7-3-outlet")["interface"] == "cee-7-3"
    assert _contract("generic", "cee-7-7-plug")["mates"] == "cee-7-3"


def test_the_button_mates_the_slot_key():
    contract = _contract("rittal", "pdu-mounting-button")
    assert contract["class"] == "mount" and contract["mates"] == "pdu-button"


def test_what_no_source_dimensions_is_declared_an_estimate():
    outlet = _contract("rittal", "cee-7-3-outlet")
    assert set(outlet["size-confidence"].values()) == {"estimated"}
    plug = _contract("generic", "cee-7-7-plug")
    assert set(plug["size-confidence"].values()) == {"estimated"}
    assert "estimate" in plug["provenance"]["size"]
    assert "rating-a" not in outlet["attrs"]


def test_the_device_says_only_what_a_document_says():
    power = _device()["attrs"]["power"]
    assert "plug-rating-a" not in power
    assert power["input-phase"] == "three" and power["input-current-a"] == 16
