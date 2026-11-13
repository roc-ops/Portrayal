"""The Panduit P42G20G (G6 intelligent PDU) and P24B32M (basic, half-height, two-sided PDU).

Each test reads the device source and the contracts it names. None reads a build.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "panduit"
COMPONENTS = ROOT / "library" / "components" / "panduit"


def _device(name: str) -> dict:
    path = DEVICES / name / "device.yaml"
    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    return yaml.safe_load(path.read_text())


def _refs(node, found=None):
    """Every `ref:` string under a node, in document order."""
    found = [] if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "ref" and isinstance(value, str):
                found.append(value)
            else:
                _refs(value, found)
    elif isinstance(node, list):
        for item in node:
            _refs(item, found)
    return found


def _count(device: dict, ref: str, view: str | None = None) -> int:
    node = device["views"][view] if view else device["views"]
    return _refs(node).count(ref)


def _contract(name: str) -> dict:
    path = COMPONENTS / name / "v1" / "contract.yaml"
    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    return yaml.safe_load(path.read_text())


# ---- P42G20G -------------------------------------------------------------------------

def test_p42g20g_body_is_the_drawn_strip():
    chassis = _device("p42g20g")["chassis"]
    assert chassis["height"] == 1780
    assert (chassis["width"], chassis["depth"]) == (56, 75)
    assert chassis["weight-kg"] == 11.5
    assert chassis["mount"] == "rack-side"


def test_p42g20g_places_the_two_kinds_of_combination_socket():
    device = _device("p42g20g")
    assert _count(device, "panduit/g5-outlet-c13-c15@1", "front") == 21
    assert _count(device, "panduit/g5-outlet-c13-c15-c19@1", "front") == 21


def test_p42g20g_has_six_breakers_and_two_buttons_and_a_cord():
    device = _device("p42g20g")
    assert _count(device, "panduit/g5-breaker-20a@1", "front") == 6
    assert _count(device, "panduit/g5-mounting-button@1", "rear") == 2
    assert _count(device, "panduit/g5-cord-60309-3pe-9h@1") == 1


def test_p42g20g_controller_bay_takes_the_g6_controller():
    device = _device("p42g20g")
    bays = device["views"]["front"]["components"]["bays"]
    assert [bay["default"] for bay in bays] == ["panduit/g6-controller@1"]
    assert bays[0]["accepts"] == ["panduit/g6-controller@1"]


def test_g6_controller_draws_the_jacks_its_drawing_labels():
    contract = _contract("g6-controller")
    refs = _refs(contract["parts"])
    assert refs.count("std/rj45@2") == 5
    assert refs.count("std/usb-a@1") == 1
    text = yaml.safe_dump(contract)
    for label in ("Serial", "Ethernet/PDU In", "PDU Out", "Sensor-1", "Sensor-2"):
        assert label in text, f"the contract does not carry the printed label {label!r}"


def test_g6_controller_is_its_own_part():
    contract = _contract("g6-controller")
    assert contract["name"] == "g6-controller"
    assert contract["version"] == "1.0.0"


# ---- P24B32M -------------------------------------------------------------------------

def test_p24b32m_body_is_the_drawn_strip():
    chassis = _device("p24b32m")["chassis"]
    assert chassis["height"] == 915
    assert chassis["depth"] == 112
    assert chassis["weight-kg"] == 9.6
    assert chassis["mount"] == "rack-side"


def test_p24b32m_places_eighteen_c13_and_six_c19():
    device = _device("p24b32m")
    assert _count(device, "std/c13-outlet@1", "front") == 18
    assert _count(device, "std/c19-outlet@1", "front") == 6


def test_p24b32m_breakers_and_ground_are_on_the_rear_and_not_the_front():
    device = _device("p24b32m")
    assert _count(device, "panduit/g5-breaker-20a@1", "rear") == 6
    assert _count(device, "panduit/g5-breaker-20a@1", "front") == 0
    assert _count(device, "common/ground-screw@1", "rear") == 1


def test_p24b32m_has_two_buttons_and_the_60a_cord():
    device = _device("p24b32m")
    assert _count(device, "panduit/g5-mounting-button@1") == 2
    assert _count(device, "panduit/g5-cord-60309-3pe-9h@1") == 1


def test_p24b32m_states_no_metering_and_no_switching():
    management = _device("p24b32m")["attrs"]["management"]
    assert management["metering-scope"] == "none"
    assert management["outlet-switching"] is False


@pytest.mark.parametrize("name", ["p42g20g", "p24b32m"])
def test_each_device_names_its_estimates_and_gaps(name):
    device = _device(name)
    assert device["maturity"] == "modelled"
    gap_names = {gap["what"] for gap in device["gaps"]}
    assert {"photographs", "outlet-pitch"} <= gap_names
