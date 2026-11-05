"""The vertical mount kit of the 7360 ISAM FX-8, as the two parts that take rack units.

A shelf rolled a quarter turn stands on its width (446.5 mm). Nokia's vertical shelf mount
kit puts an air intake baffle/drip tray under it and a top baffle over it. The unit data
sheet gives each part's size and the installation manual's Figure 84 shows how many
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
    "fx8-vertical-air-intake-tray": {"height": 89.02, "depth": 251.97, "width": 350.01},
    "fx8-vertical-top-baffle": {"height": 99.74, "depth": 205.74, "width": 381.0},
}
# Figure 84: the tray of the second shelf stands 15 units above the tray of the first
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
    shelf = load("nfxs-e-bb")["chassis"]
    stood_up = math.ceil(shelf["width"] / RU - 1e-9)     # the kit's rule: its width over one unit, rounded up
    pitch = load("fx8-vertical-air-intake-tray")["chassis"]["ru"] + stood_up + load("fx8-vertical-top-baffle")["chassis"]["ru"]
    assert pitch == STACK_PITCH_RU


def test_each_part_names_its_unit_data_sheet_with_a_hash_and_says_the_units_are_read_off_a_figure():
    for name in PARTS:
        doc = load(name)
        assert "Vertical shelf mount kit unit data sheet" in doc["datasheet"]["title"], name
        assert len(doc["datasheet"]["sha256"]) == 64, name
        assert doc["provenance"]["units"]["confidence"] == "drawing", name
        assert "Figure 84" in doc["provenance"]["units"]["note"], name
