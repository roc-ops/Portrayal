"""The Eaton ePDU G3 managed EMA325-10: what is true of its device file.

No build is needed: each test reads the device and its contracts from the library folder.
"""
import pathlib

import yaml

LIB = pathlib.Path(__file__).resolve().parents[2] / "library"
DEVICE = yaml.safe_load((LIB / "devices/eaton/ema325-10/device.yaml").read_text())
CORD = yaml.safe_load((LIB / "components/eaton/g3-cord-l21-20p/v1/contract.yaml").read_text())
WELL = yaml.safe_load((LIB / "components/eaton/ema325-10-base/v1/contract.yaml").read_text())


def _placements(view):
    return DEVICE["views"][view]["components"]["placements"]


def test_the_body_is_the_drawings_size_and_stands_beside_an_upright():
    """The drawing prints 66.50 in (1689 mm) long, 2.05 in (52 mm) wide and 2.56 in (65 mm) deep."""
    chassis = DEVICE["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (52, 1689, 65)
    assert chassis["mount"] == "rack-side"


def test_eighteen_c13_and_six_c19_outlets_in_three_sections():
    refs = [p["ref"] for p in _placements("front")]
    assert refs.count("std/c13-outlet@1") == 18
    assert refs.count("std/c19-outlet@1") == 6
    through = {p["through"] for p in _placements("front") if p["ref"].startswith("std/c1")}
    assert through == {"breaker-a", "breaker-b", "breaker-c"}


def test_three_breakers_in_the_three_section_colours():
    breakers = [p for p in _placements("front") if p["ref"] == "eaton/g3-breaker-20a-2p@1"]
    assert len(breakers) == 3
    assert [b["id"] for b in breakers] == ["breaker-a", "breaker-b", "breaker-c"]


def test_the_module_has_its_ports_and_buttons():
    ids = {p["id"] for p in _placements("front")}
    assert {"serial", "daisy-chain", "network", "usb", "reset", "display"} <= ids
    assert {"button-up", "button-down", "button-esc", "button-enter"} <= ids


def test_the_two_mounting_buttons_are_on_the_rear_1555_8_apart():
    buttons = [p for p in _placements("rear") if p["ref"].endswith("mounting-button@1")]
    assert len(buttons) == 2
    assert abs(abs(buttons[1]["at"][1] - buttons[0]["at"][1]) - 1555.8) <= 1.0


def test_the_cord_part_is_the_l21_20p_cord():
    assert CORD["attrs"]["plug"] == "nema-l21-20p"
    assert CORD["attrs"]["cord-length-ft"] == 10


def test_each_breaker_takes_its_sections_sampled_colour():
    """The sheet's own fills, sampled at 300 dpi: yellow, blue and red."""
    colours = {p["id"]: (p["attrs"]["section"], p["attrs"]["section-color"])
               for p in _placements("front") if p["ref"] == "eaton/g3-breaker-20a-2p@1"}
    assert colours == {"breaker-a": ("A", "#f8e840"), "breaker-b": ("B", "#0000f8"), "breaker-c": ("C", "#f80000")}


def test_each_breaker_is_wired_across_two_lines_as_the_one_line_diagram_draws_it():
    lines = {p["id"]: p["lines"] for p in _placements("front") if p["ref"] == "eaton/g3-breaker-20a-2p@1"}
    assert lines == {"breaker-a": ["L1", "L2"], "breaker-b": ["L2", "L3"], "breaker-c": ["L3", "L1"]}


def test_every_outlet_is_numbered_one_to_eight_in_its_section():
    for section in "abc":
        ids = {p["id"] for p in _placements("front") if p["id"].startswith(f"outlet-{section}")}
        assert ids == {f"outlet-{section}{n}" for n in range(1, 9)}


def test_there_are_twenty_four_lamps_all_bound_to_the_chassis_and_drawn_off():
    lamps = [p for p in _placements("front") if p["ref"] == "common/led-dot@1"]
    assert len(lamps) == 24
    assert {p["for"] for p in lamps} == {"chassis"}
    assert not any("states" in p for p in lamps)


def test_there_are_twenty_four_lamp_numerals_one_to_eight_in_each_section():
    numerals = [s for s in DEVICE["views"]["front"]["silkscreen"] if s.get("for", "").startswith("lamp-")
                and s.get("text", "").isdigit()]
    assert len(numerals) == 24
    for section in "abc":
        assert sorted(s["text"] for s in numerals if s["for"].startswith(f"lamp-{section}")) == [str(n) for n in range(1, 9)]
        assert all(s["for"] == f"lamp-{section}{s['text']}" for s in numerals if s["for"].startswith(f"lamp-{section}"))


def test_the_module_ports_are_the_parts_the_brief_names():
    refs = {p["id"]: p["ref"] for p in _placements("front")}
    assert refs["serial"] == "std/rj45@2"
    assert refs["network"] == refs["daisy-chain"] == "common/rj45-eth@1"
    assert refs["usb"] == "std/usb-a@1"
    assert refs["reset"] == "common/reset-button@1"
    assert refs["display"] == "eaton/g3-display@1"


def test_the_cord_is_placed_once_on_the_cord_end_and_feeds_every_outlet():
    inputs = [p for view in DEVICE["views"].values() for p in view.get("components", {}).get("placements", [])
              if p["ref"] == "eaton/g3-cord-l21-20p@1"]
    assert len(inputs) == 1
    assert inputs[0] in _placements("bottom")
    fed = {p["fed-by"] for p in _placements("front") if p["ref"].startswith("std/c1")}
    assert fed == {inputs[0]["id"]}


def test_the_ends_and_the_left_side_are_built_as_the_documented_side():
    """No held document shows the far end or the left side: the notes say so."""
    assert "built as the documented side, as no document shows this one" in DEVICE["views"]["top"]["empty"]
    assert "built as the documented side, as no document shows this one" in DEVICE["provenance"]["sides"]["note"]
    right = {d["id"] for d in DEVICE["views"]["right"]["panel"]["decor"]}
    left = {d["id"] for d in DEVICE["views"]["left"]["panel"]["decor"]}
    assert left == {i + "-m" for i in right}


def test_the_input_is_exported_as_other_and_not_as_an_unregistered_connector():
    assert DEVICE["attrs"]["power"]["input-plug"] == "other"


def test_the_base_well_is_as_deep_as_the_part_so_the_solids_stand_inside_it():
    """A zero-U part that places components on its face needs a well as deep as its depth."""
    assert WELL["size"]["d"] == DEVICE["chassis"]["depth"]
    assert (WELL["size"]["w"], WELL["size"]["h"]) == (DEVICE["chassis"]["width"], DEVICE["chassis"]["height"])
    assert any(p["ref"] == "eaton/ema325-10-base@1" for p in _placements("front"))
