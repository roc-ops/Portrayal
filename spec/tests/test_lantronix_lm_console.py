"""The Lantronix LM83X and LM80 console servers, and the three LM83X expansion modules.

What each document gives is held as a fact of the library: the outline from the product
brief, the three bays that tile the chassis width, the module sizes from the option card
brief, and the ports each face shows. The tests read the sources and contracts, never a
build.
"""
from pathlib import Path

import pytest
import yaml

LIB = Path(__file__).resolve().parents[2] / "library"

# part, width, depth (mm) as the LM Series option cards and expansion modules brief prints them
MODULES = {
    "lm83x-8sa": (92.9, 128.6),
    "lm83x-8ea": (92.9, 129.2),
    "lm83x-lcda": (92.9, 130.8),
}
VIEWS = {"front", "rear", "top", "bottom", "left", "right"}


def _device(name):
    return yaml.safe_load((LIB / "devices" / "lantronix" / name / "device.yaml").read_text())


def _module(name):
    return yaml.safe_load(
        (LIB / "components" / "lantronix" / name / "v1" / "contract.yaml").read_text())


def _placements(device, view="front"):
    comps = device["views"][view].get("components", {})
    return comps.get("placements", []) + comps.get("bays", [])


def _in_group(device, group, view="front"):
    return [p for p in _placements(device, view) if p.get("group") == group]


@pytest.mark.parametrize("name,size", [
    ("lm83x", (445.0, 43.2, 264.0)),
    ("lm80", (254.0, 43.0, 163.0)),
])
def test_the_chassis_is_the_size_the_product_brief_prints(name, size):
    chassis = _device(name)["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == size


@pytest.mark.parametrize("name", ["lm83x", "lm80"])
def test_a_device_has_six_views_and_each_is_sized(name):
    views = _device(name)["views"]
    assert set(views) == VIEWS
    assert all({"w", "h"} <= set(v["size"]) for v in views.values())


def test_the_lm83x_mounts_in_a_rack_and_the_lm80_does_not_claim_to():
    lm83x, lm80 = _device("lm83x")["chassis"], _device("lm80")["chassis"]
    assert lm83x["ru"] == 1 and lm83x.get("mount", "rack") == "rack"
    assert "ru" not in lm80 and lm80["mount"] == "desktop"


@pytest.mark.parametrize("part,size", sorted(MODULES.items()))
def test_a_module_is_the_size_the_option_card_brief_prints(part, size):
    contract = _module(part)
    assert contract["kind"] == "module"
    assert (contract["size"]["w"], contract["size"]["d"]) == size


def test_the_three_bays_tile_the_width_of_one_module():
    bays = _device("lm83x")["views"]["front"]["components"]["bays"]
    assert len(bays) == 3
    width = MODULES["lm83x-8sa"][0]
    assert all(b["size"]["w"] == width for b in bays)
    xs = sorted(b["at"][0] for b in bays)
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [width, width]
    assert round(xs[-1] + width, 1) == _device("lm83x")["views"]["front"]["size"]["w"]


def test_every_bay_takes_every_module_and_the_other_parts_have_a_bay_of_their_own():
    bays = _device("lm83x")["views"]["front"]["components"]["bays"]
    wanted = {f"lantronix/{m}@1" for m in MODULES}
    assert all(set(b["accepts"]) == wanted for b in bays)


def test_the_lm83x_base_unit_shows_eight_serial_ports_and_the_ports_beside_them():
    lm83x = _device("lm83x")
    assert len(_in_group(lm83x, "serial")) == 8
    assert len(_in_group(lm83x, "network")) == 2
    for group in ("console", "sfp", "usb", "antenna"):
        assert _in_group(lm83x, group), group


def test_the_lm80_shows_the_same_ports_as_the_lm83x_base_unit_and_no_bay():
    lm80, lm83x = _device("lm80"), _device("lm83x")
    assert "bays" not in lm80["views"]["front"].get("components", {})
    for group in ("serial", "network", "console", "sfp", "usb", "antenna"):
        assert len(_in_group(lm80, group)) == len(_in_group(lm83x, group)), group


def test_the_lm83x_rear_shows_two_ac_inlets():
    inlets = [p for p in _placements(_device("lm83x"), "rear") if "c14" in p["ref"]]
    assert len(inlets) == 2


def test_the_lm80_rear_is_stated_empty_because_no_document_shows_it():
    rear = _device("lm80")["views"]["rear"]
    assert rear.get("empty") and not _placements(_device("lm80"), "rear")


@pytest.mark.parametrize("part,group,count", [
    ("lm83x-8sa", "serial", 8),
    ("lm83x-8ea", "ethernet", 8),
])
def test_a_port_module_carries_eight_ports_in_one_group(part, group, count):
    contract = _module(part)
    assert contract["groups"][group]["role"] in {"traffic", "management"}
    ports = [p for p in contract["parts"] if p.get("group") == group]
    assert len(ports) == count


def test_the_ethernet_module_is_gigabit_and_the_serial_module_is_not_ethernet():
    ethernet, serial = _module("lm83x-8ea"), _module("lm83x-8sa")
    assert ethernet["groups"]["ethernet"]["attrs"]["speed"] == "1g"
    assert serial["groups"]["serial"]["attrs"]["media"] == "rj45-serial"


def test_the_option_cards_are_not_modelled_because_their_slot_has_no_registered_key():
    cards = LIB / "components" / "lantronix"
    assert not [p for p in cards.iterdir() if p.name.startswith("88-")]


def test_a_configuration_names_modules_only_for_bays_that_exist():
    device = _device("lm83x")
    bay_ids = {b["id"] for b in device["views"]["front"]["components"]["bays"]}
    wanted = {f"lantronix/{m}@1" for m in MODULES}
    for config in device["configurations"].values():
        for bay, ref in config.get("bays", {}).items():
            assert bay in bay_ids
            assert ref == "" or ref in wanted
