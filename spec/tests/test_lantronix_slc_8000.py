"""The Lantronix SLC 8000 base chassis is in the library: six faces, its fixed parts, and three declared I/O bays.

The device is the chassis as it ships, without I/O modules, so the rear declares its three module bays by the interface they
present and draws nothing in them. The front carries a display, a keypad, a console jack, two USB ports and a modem jack. Its
parts are Lantronix's own: the display and the keypad. Each figure the documents do not give is declared an estimate in the
contract that carries it.

These read the library and the registry and render nothing; they read no library/dist.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "lantronix" / "slc-8000" / "device.yaml"

NEW_PARTS = ["lantronix/slc-lcd", "lantronix/slc-keypad"]


def contract(name):
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / "v1" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(device, view):
    return {p["id"]: p for p in device["views"][view]["components"].get("placements", [])}


def test_the_chassis_is_the_one_u_body_the_documents_dimension(device):
    c = device["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (438.15, 44.45, 304.8, 1)
    for face, size in {"front": (438.15, 44.45), "rear": (438.15, 44.45), "top": (438.15, 304.8),
                       "bottom": (438.15, 304.8), "left": (304.8, 44.45), "right": (304.8, 44.45)}.items():
        assert (device["views"][face]["size"]["w"], device["views"][face]["size"]["h"]) == size, face


def test_the_rear_declares_three_io_bays_that_name_an_interface(device):
    bays = device["views"]["rear"]["components"]["bays"]
    assert [b["id"] for b in bays] == ["io-1", "io-2", "io-3"]
    for b in bays:
        assert b["interface"] == "lantronix-slc-io"
    xs = [b["at"][0] for b in bays]
    assert xs == sorted(xs)


def test_the_io_bay_interface_is_registered():
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    assert "lantronix-slc-io" in reg


def test_the_front_carries_what_the_documents_list(device):
    front = placements(device, "front")
    assert {"display", "keypad", "usb-1", "usb-2", "console", "modem"} <= set(front)
    assert front["display"]["ref"] == "lantronix/slc-lcd@1"
    assert front["keypad"]["ref"] == "lantronix/slc-keypad@1"
    assert front["usb-1"]["ref"] == front["usb-2"]["ref"] == "std/usb-a@1"
    assert front["console"]["attrs"]["role"] == "console"


def test_the_rear_carries_two_network_jacks_and_an_ac_inlet(device):
    rear = placements(device, "rear")
    assert rear["net-1"]["ref"] == rear["net-2"]["ref"] == "common/rj45-eth@1"
    assert rear["inlet"]["ref"] == "std/c14-inlet@1"


def test_the_keypad_has_the_five_keys_the_quick_start_names():
    assert sorted(contract("lantronix/slc-keypad")["elements"]) == ["down", "enter", "left", "right", "up"]


@pytest.mark.parametrize("name", NEW_PARTS)
def test_each_new_part_says_which_of_its_figures_are_estimates(name):
    d = contract(name)
    assert d["size-confidence"] and "estimated" in d["size-confidence"].values()
    text = " ".join(str(v) for v in d["provenance"].values()).lower()
    assert "estimated" in text


def test_every_new_part_has_a_skin_for_each_name_in_its_contract():
    for name in NEW_PARTS:
        ns, part = name.split("/")
        d = contract(name)
        for skin in d["skins"]:
            assert (LIB / "components" / ns / part / "v1" / "skins" / f"{skin}.svg").is_file(), (name, skin)


def test_the_device_says_what_its_figures_rest_on(device):
    notes = " ".join(v["note"] for v in device["provenance"].values()).lower()
    assert "photo" in notes and "estimated" in notes
    assert device["gaps"], "a chassis drawn from angled photographs states what it could not read"
