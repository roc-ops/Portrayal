"""The vertical mount kit of the 7360 ISAM FX-4, as the two parts that take rack units.

A shelf rolled a quarter turn stands on its width (447 mm). Nokia's vertical shelf mount
kit puts an air intake baffle/drip tray under it and a top baffle over it. The unit data
sheet gives each part's size and the installation manual's Figure 144 shows how many
rack units a shelf and its kit take; these tests hold the library to both.
"""
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "nokia"
RU = 44.45

# Table 3 and Table 5 of the unit data sheet: height up the rack, depth, width across it
PARTS = {
    "fx4-vertical-air-intake-tray": {"height": 88.14, "depth": 251.97, "width": 218.59},
    "fx4-vertical-top-baffle": {"height": 99.74, "depth": 205.74, "width": 250.2},
}
# Figure 144: the tray of the second shelf stands 15 units above the tray of the first
STACK_PITCH_RU = 15


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def test_each_part_has_the_size_the_unit_data_sheet_prints():
    for name, size in PARTS.items():
        chassis = load(name)["chassis"]
        assert (chassis["height"], chassis["depth"], chassis["width"]) == (size["height"], size["depth"], size["width"]), name


def test_each_part_states_the_units_it_takes_and_its_front_drawing_is_its_size():
    for name, size in PARTS.items():
        doc = load(name)
        assert isinstance(doc["chassis"]["ru"], int) and doc["chassis"]["ru"] >= 1, name
        assert doc["views"]["front"]["size"] == {"w": size["width"], "h": size["height"]}, name


def test_a_shelf_and_its_kit_stack_at_the_pitch_the_figure_shows():
    shelf = load("nfxs-f-bb")["chassis"]
    stood_up = math.ceil(shelf["width"] / RU - 1e-9)     # the kit's rule: its width over one unit, rounded up
    pitch = load("fx4-vertical-air-intake-tray")["chassis"]["ru"] + stood_up + load("fx4-vertical-top-baffle")["chassis"]["ru"]
    assert pitch == STACK_PITCH_RU


def test_the_tray_and_the_baffle_state_that_they_have_no_ears_and_draw_no_generic_ear():
    from portrayal import ears
    for name in PARTS:
        doc = load(name)
        assert doc["chassis"]["ears"] == {"none": True}, name
        assert ears.plan(doc) is None, name
        assert "Figure 144" in doc["provenance"]["ears"]["note"], name


def test_each_part_names_its_unit_data_sheet_with_a_hash_and_says_the_units_are_read_off_a_figure():
    for name in PARTS:
        doc = load(name)
        assert "Vertical shelf mount kit unit data sheet" in doc["datasheet"]["title"], name
        assert "3FE 67299 BAAA TQZZA Edition 01" in doc["datasheet"]["title"], name
        assert len(doc["datasheet"]["sha256"]) == 64, name
        assert doc["provenance"]["units"]["confidence"] == "drawing", name
        assert "Figure 144" in doc["provenance"]["units"]["note"], name


def test_the_colour_is_declared_an_estimate_and_the_part_numbers_are_the_sheets():
    for name in PARTS:
        doc = load(name)
        assert doc["provenance"]["color"]["confidence"] == "estimated", name
    numbers = {a["name"] for a in load("fx4-vertical-air-intake-tray")["aliases"]}
    assert numbers == {"3FE 65787 AA"}, "3FE 65751 AA is the bracket's number, listed in the FX-8 kit too"
    assert {a["name"] for a in load("fx4-vertical-top-baffle")["aliases"]} == {"3FE 67839 AA"}
