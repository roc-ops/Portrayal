"""The Lantronix SLC 8000 front draws its memory card slot.

The User Guide shows the slot on the front panel between the keypad and the two USB ports, with the legend MEMORY CARD
printed above it, and shows it empty: the card is the user's own. The slot is the registered full-size card slot part and
the front names no card.

These read the library and the registry and render nothing; they read no library/dist.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "lantronix" / "slc-8000" / "device.yaml"
CONNECTORS = ROOT / "spec" / "schemas" / "connectors.yaml"


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


@pytest.fixture(scope="module")
def front(device):
    return device["views"]["front"]


def placed(front):
    return {p["id"]: p for p in front["components"]["placements"]}


def contract(name):
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / "v1" / "contract.yaml").read_text())


def test_the_front_places_the_registered_card_slot(front):
    slot = placed(front)["card-slot"]
    assert slot["ref"] == "vertiv/sd-card-slot@1"
    assert contract("vertiv/sd-card-slot")["interface"] == "sd-card"
    assert "sd-card" in yaml.safe_load(CONNECTORS.read_text())["interfaces"]


def test_the_slot_sits_between_the_keypad_and_the_usb_ports_inside_the_face(front):
    p = placed(front)
    w, h = contract("vertiv/sd-card-slot")["size"]["w"], contract("vertiv/sd-card-slot")["size"]["h"]
    x, y = p["card-slot"]["at"]
    assert p["keypad"]["at"][0] < x
    assert x + w < p["usb-1"]["at"][0], "the slot ends before the first USB port begins"
    assert 0 <= y and y + h <= front["size"]["h"]


def test_the_slot_is_a_group_member_and_has_its_legend(device, front):
    slot = placed(front)["card-slot"]
    group = device["groups"][slot["group"]]
    assert group["term"] == "Slot"
    legend = [s for s in front["silkscreen"] if s.get("for") == "card-slot"]
    assert [s["text"] for s in legend] == ["MEMORY CARD"], "the legend is printed as the guide shows it"


def test_the_slot_gap_is_gone_and_the_other_gaps_stay_stated(device):
    whats = [g["what"] for g in device["gaps"]]
    assert "sd-card-slot" not in whats
    assert device["gaps"]


def test_the_front_note_says_where_the_slot_was_read_and_that_no_card_is_shown(device):
    note = device["provenance"]["front"]["note"].lower()
    assert "memory card" in note and "figure 2-13" in note
    assert "empty" in note
