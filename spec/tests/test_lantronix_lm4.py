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
    assert lm4["groups"]["serial"]["attrs"]["media"] == "rj45-serial"
    assert lm4["groups"]["console"]["attrs"]["media"] == "rj45-serial"
    assert all("media" not in p.get("attrs", {}) for p in _in_group(lm4, "network"))


def test_the_two_and_four_port_part_numbers_are_listed():
    configs = _lm4()["configurations"]
    numbers = {n for c in configs.values() for n in c["part-numbers"]}
    assert {"LM4-4S", "LM4-2S"} <= numbers


def test_the_second_status_lamp_is_named_for_the_pulse_mark_under_it():
    lamps = [p["id"] for p in sorted(_in_group(_lm4(), "status-leds"), key=lambda p: p["rel-pos"])]
    assert lamps == ["led-power", "led-pulse", "led-alert"]


def test_the_dc_input_gap_says_no_interface_is_known_so_no_part_is_placed():
    gap = next(g for g in _lm4()["gaps"] if g["what"] == "dc-input")
    note = gap["note"].replace("\n", " ")
    assert "No interface is known, so no part is" in note
    assert "A connector is a part, so it is not drawn as decor" in note


def _decor(device):
    return {d["id"]: d for d in device["views"]["front"]["panel"]["decor"]}


def test_the_network_jack_is_turned_so_its_latch_notch_is_at_the_top():
    net = next(p for p in _front(_lm4()) if p["id"] == "net-1")
    assert net["rotate"] == 180


def test_the_button_and_the_four_corner_screws_are_round_by_a_corner_radius_of_half_their_side():
    decor = _decor(_lm4())
    button = decor["button"]
    assert button["size"] == [7.0, 7.0] and button["rx"] == 3.5
    for name in ("screw-tl", "screw-tr", "screw-bl", "screw-br"):
        screw = decor[name]
        assert screw["size"][0] == screw["size"][1] and screw["rx"] == screw["size"][0] / 2


def test_the_heatsink_has_six_fins_each_1_3_mm_wide():
    fins = [d for i, d in _decor(_lm4()).items() if i.startswith("heatsink-slat-")]
    assert len(fins) == 6
    assert all(f["size"][0] == 1.3 for f in fins)


def test_the_console_and_usb_ports_and_the_serial_jacks_each_sit_on_one_pale_housing_block():
    decor = _decor(_lm4())
    colour = "#e5d9cf"
    assert decor["housing-console-usb"]["fill"] == decor["housing-serial"]["fill"] == colour
    box = decor["housing-console-usb"]
    for p in _in_group(_lm4(), "console") + _in_group(_lm4(), "usb"):
        assert box["at"][0] <= p["at"][0] and p["at"][0] + 12.0 <= box["at"][0] + box["size"][0] + 1.0
    serial = decor["housing-serial"]
    for p in _in_group(_lm4(), "serial"):
        assert serial["at"][0] <= p["at"][0] <= serial["at"][0] + serial["size"][0]


def test_the_drawn_usb_tongue_is_said_to_be_pale_where_the_photograph_is_dark():
    note = _lm4()["provenance"]["body"]["note"].replace("\n", " ")
    assert "The drawn tongue is pale where the photograph's is dark" in note
    assert "no circle shape" not in note


def test_the_two_port_export_says_its_four_jacks_are_not_the_makers_count():
    configs = _lm4()["configurations"]
    assert "not the maker's count" in configs["ac-2s"]["export-description"]
    assert "not the maker's count" in configs["ac-2s"]["description"].replace("\n", " ")
    assert "export-description" not in configs["ac-4s"]


def test_the_lid_and_flank_gap_does_not_say_the_format_cannot_draw_them():
    gap = next(g for g in _lm4()["gaps"] if g["what"] == "envelope-faces-undetailed")
    note = gap["note"].replace("\n", " ")
    assert "Its size gives no position" not in note
    assert "a choice of this drawing and not a limit of the format" in note


def test_the_dc_input_is_a_stated_gap_and_not_drawn_as_decoration():
    lm4 = _lm4()
    assert any(g["what"] == "dc-input" for g in lm4["gaps"])
    decor = lm4["views"]["front"]["panel"]["decor"]
    assert not [d for d in decor if "dc" in d["id"] or d.get("kind") == "connector"]
