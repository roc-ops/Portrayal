"""The Lantronix SLC 8000 base chassis is in the library: six faces and its fixed parts.

The base build is the chassis without I/O modules, so the rear declares its three module bays, each stating the class of
module it takes, and the base build seats nothing in them. The front carries a display, a keypad, a console jack, two USB ports and a modem jack. Its
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
CONNECTORS = ROOT / "spec" / "schemas" / "connectors.yaml"

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


def rear_bays(device):
    return device["views"]["rear"]["components"].get("bays") or []


def test_the_rear_declares_three_bays_that_state_the_module_class_and_seat_nothing(device):
    bays = rear_bays(device)
    assert [b["id"] for b in bays] == ["io-bay-1", "io-bay-2", "io-bay-3"]
    assert {b["interface"] for b in bays} == {"slc-io-module"}
    assert not [b for b in bays if b.get("accepts") or b.get("default")]
    assert {b["group"] for b in bays} == {"io-bays"}
    assert [b["rel-pos"] for b in bays] == [1, 2, 3]
    assert device["groups"]["io-bays"]["role"] == "traffic"


def test_the_bays_stand_where_the_rear_windows_were_and_no_decor_window_remains(device):
    bays = rear_bays(device)
    assert [b["at"][0] for b in bays] == [22.5, 137.0, 251.5]
    assert {tuple(b["at"][1:]) for b in bays} == {(0.5,)}
    assert {(b["size"]["w"], b["size"]["h"]) for b in bays} == {(112.5, 43.4)}
    assert not [d for d in device["views"]["rear"]["panel"]["decor"] if d["kind"] == "window"]


def test_the_module_class_is_a_registered_key_that_cites_the_guide():
    registry = yaml.safe_load(CONNECTORS.read_text())["interfaces"]
    note = registry["slc-io-module"]["note"]
    assert "900-704-RBD-SLC-UG" in note and "Table 3-8" in note


def test_the_module_gap_says_what_is_drawn_and_keeps_the_module_rules_as_words(device):
    gap = {g["what"]: g for g in device["gaps"]}["io-modules"]
    text = " ".join(gap["note"].split()).lower()
    assert "declared" in text or "stating the class of module it takes" in text
    assert "are not modelled" in text
    for rule in ("8-port", "bay 1 only", "bay 2 or 3, never bay 1", "in order"):
        assert rule in text, rule


def test_the_base_build_leaves_every_bay_empty(device):
    assert device["configurations"]["base"]["bays"] == {"io-bay-1": "", "io-bay-2": "", "io-bay-3": ""}


@pytest.mark.parametrize("export", ["netbox", "nautobot"])
def test_the_device_type_lists_the_three_bays_and_gives_them_no_port(export):
    path = LIB / "exports" / export / "device-types" / "Lantronix" / "SLC 8000.yaml"
    doc = yaml.safe_load(path.read_text())
    assert [b["name"] for b in doc["module-bays"]] == ["io-bay-1", "io-bay-2", "io-bay-3"]
    assert [b["position"] for b in doc["module-bays"]] == ["io-bay-1", "io-bay-2", "io-bay-3"]
    assert all(b["description"].startswith("Takes ") for b in doc["module-bays"])
    assert [i["name"] for i in doc["interfaces"]] == ["Ethernet 1", "Ethernet 2"]


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
