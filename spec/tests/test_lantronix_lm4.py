"""The Lantronix LM4 console server.

What the product brief prints is held as a fact of the library: the outline, the port counts and
the connector type of each port. The tests read the device file, never a build.
"""
from pathlib import Path

import yaml

LIB = Path(__file__).resolve().parents[2] / "library"
VIEWS = {"front", "rear", "top", "bottom", "left", "right"}


def _lm4():
    return yaml.safe_load((LIB / "devices" / "lantronix" / "lm4" / "device.yaml").read_text())


def _front(device):
    comps = device["views"]["front"].get("components", {})
    return comps.get("placements", []) + comps.get("bays", [])


def _in_group(device, group):
    return [p for p in _front(device) if p.get("group") == group]


def test_the_chassis_is_the_size_the_product_brief_prints():
    chassis = _lm4()["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (158.75, 44.45, 158.75)


def test_the_device_has_six_views_and_each_is_sized():
    views = _lm4()["views"]
    assert set(views) == VIEWS
    assert all({"w", "h"} <= set(v["size"]) for v in views.values())


def test_the_front_shows_the_ports_the_brief_lists():
    lm4 = _lm4()
    assert len(_in_group(lm4, "serial")) == 4
    assert len(_in_group(lm4, "network")) == 1
    assert len(_in_group(lm4, "sfp")) == 1
    assert len(_in_group(lm4, "console")) == 1
    usb = _in_group(lm4, "usb")
    assert len(usb) == 2 and all(p["ref"] == "std/usb-a@1" for p in usb)


def test_the_serial_and_console_jacks_are_serial_media_and_the_network_jack_is_not():
    lm4 = _lm4()
    for p in _in_group(lm4, "serial") + _in_group(lm4, "console"):
        assert p["attrs"]["media"] == "rj45-serial"
    assert all("media" not in p.get("attrs", {}) for p in _in_group(lm4, "network"))


def test_the_two_and_four_port_part_numbers_are_listed():
    configs = _lm4()["configurations"]
    numbers = {n for c in configs.values() for n in c["part-numbers"]}
    assert {"LM4-4S", "LM4-2S"} <= numbers


def test_the_dc_input_is_a_stated_gap_and_not_drawn_as_decoration():
    lm4 = _lm4()
    assert any(g["what"] == "dc-input" for g in lm4["gaps"])
    decor = lm4["views"]["front"]["panel"]["decor"]
    assert not [d for d in decor if "dc" in d["id"] or d.get("kind") == "connector"]
