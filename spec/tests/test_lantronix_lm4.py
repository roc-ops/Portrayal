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


def test_the_lid_and_flank_gap_says_what_is_drawn_and_that_it_is_estimated():
    gap = next(g for g in _lm4()["gaps"] if g["what"] == "envelope-faces-undetailed")
    note = gap["note"].replace("\n", " ")
    assert "Its size gives no position" not in note
    assert "draws six ridges in seven slots and the left flank three screws" in note
    assert "estimated" in note


MARKS = {"mark-prompt", "mark-dc", "mark-power", "mark-pulse", "mark-warning", "mark-network", "mark-antenna-arcs",
         "mark-antenna-stem", "mark-antenna-dot", "mark-link", "mark-arrows-shaft", "mark-arrows-head", "mark-10101"}


def _silk(device):
    return device["views"]["front"]["silkscreen"]


def _notes(device):
    notes = [p["note"] for p in device["provenance"].values()] + [g["note"] for g in device["gaps"]]
    return " ".join(" ".join(notes).split())


def test_the_marks_and_icons_are_drawn_as_silkscreen_paths_and_the_prompt_icon_is_no_longer_text():
    silk = _silk(_lm4())
    paths = {s["id"]: s for s in silk if "path" in s}
    assert set(paths) == MARKS
    assert all(s["path"].strip() and s["fill"].startswith("#") for s in paths.values())
    assert not [s for s in silk if s.get("text") == ">_"]
    assert paths["mark-prompt"]["for"] == "console" and paths["mark-10101"]["for"] == ["serial-1", "serial-2", "serial-3", "serial-4"]


def test_the_two_dots_and_the_larger_hole_are_round_dark_decor():
    decor = _decor(_lm4())
    for name, side in (("hole-lamps", 2.75), ("dot-e1-e2", 1.75), ("dot-e2-right", 1.7)):
        assert decor[name]["size"] == [side, side] and decor[name]["rx"] == side / 2


def _left_right_lit(placement):
    """The `on` colour of the lamp on the left and on the right; rotate 180 swaps the part's two windows."""
    on = {el: next(s["color"] for s in states if isinstance(s, dict) and s["name"] == "on") for el, states in placement["states"].items()}
    return (on["led-b"], on["led-a"]) if placement.get("rotate") == 180 else (on["led-a"], on["led-b"])


def _rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def test_the_console_and_serial_jacks_state_a_lit_green_lamp_on_the_left_and_a_lit_yellow_on_the_right():
    lm4 = _lm4()
    jacks = _in_group(lm4, "serial") + _in_group(lm4, "console")
    assert len(jacks) == 5 and all("states" in p for p in jacks)
    for p in jacks:
        left, right = (_rgb(c) for c in _left_right_lit(p))
        assert left[1] > left[0] + 20 and left[1] > left[2] + 20, p["id"]
        assert right[0] > right[2] + 80 and right[1] > right[2] + 80, p["id"]
    assert not [p for p in _in_group(lm4, "status-leds") if "states" in p]


def test_the_lid_has_six_slats_in_seven_slots_and_the_left_flank_three_round_screws():
    views = _lm4()["views"]
    top = {d["id"]: d for d in views["top"]["panel"]["decor"]}
    slats = [d for i, d in top.items() if i.startswith("lid-slat-")]
    assert len(slats) == 6 and all(d["size"][0] == 1.3 for d in slats)
    assert top["lid-opening"]["size"][0] > 6 * 1.3 + 7 * 3.0
    screws = [d for d in views["left"]["panel"]["decor"] if d["id"].startswith("flank-screw-")]
    assert len(screws) == 3 and all(d["size"] == [5.8, 5.8] and d["rx"] == 2.9 for d in screws)


def test_the_serial_jacks_stand_on_their_openings_clear_of_the_bars_and_say_why_they_are_not_wider():
    lm4 = _lm4()
    decor = _decor(lm4)
    serial = {p["id"]: p for p in _in_group(lm4, "serial")}
    assert all("size" not in p for p in serial.values())
    assert [serial[i]["at"][0] + 6.35 for i in ("serial-1", "serial-2")] == [125.0, 141.2]
    block = decor["housing-serial"]
    assert serial["serial-3"]["at"][1] + 11.0 <= block["at"][1] + block["size"][1] <= decor["bar-serial-bottom"]["at"][1]
    assert serial["serial-1"]["at"][1] >= decor["bar-serial-top"]["at"][1] + decor["bar-serial-top"]["size"][1]
    note = next(g for g in lm4["gaps"] if g["what"] == "front-positions")["note"].replace("\n", " ")
    assert "a placement cannot change a part's width" in note


def test_the_network_jack_and_the_sfp_cage_stand_at_their_measured_places():
    placed = {p["id"]: p for p in _front(_lm4())}
    assert placed["net-1"]["at"] == [47.45, 23.1] and placed["port-2"]["at"] == [72.5, 28.1]


def test_no_note_says_the_marks_lamps_slats_or_screws_are_left_out():
    notes = _notes(_lm4())
    for phrase in ("None is drawn", "so none is drawn lit", "leaving them out", "The four faces draw the envelope only", "bare text"):
        assert phrase not in notes
    assert "No interface is known, so no part is placed" in notes


def test_the_registered_mark_is_a_named_gap_because_it_is_too_small_to_place():
    gap = next(g for g in _lm4()["gaps"] if g["what"] == "registered-mark")
    assert gap["reason"] == "needs-photo" and "about 9 px" in gap["note"].replace("\n", " ")


def test_the_dc_input_is_a_stated_gap_and_not_drawn_as_decoration():
    lm4 = _lm4()
    assert any(g["what"] == "dc-input" for g in lm4["gaps"])
    decor = lm4["views"]["front"]["panel"]["decor"]
    assert not [d for d in decor if "dc" in d["id"] or d.get("kind") == "connector"]
