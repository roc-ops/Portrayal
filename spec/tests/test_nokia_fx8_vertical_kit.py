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


# Tables 2 and 3 of the unit data sheet print a bracket's height, width and length: read as the bar's
# height, the ear's rise and the length across the rack (Figure 2 of the sheet draws each so)
BRACKETS = {
    "below": {"bar-h": 25.4, "ear-h": 92.44, "length": 486.41},    # shelf horizontal mount bracket, Table 3
    "above": {"bar-h": 31.5, "ear-h": 62.0, "length": 486.75},     # top cross bracket, Table 2
}


def shelf_brackets():
    return {b["id"]: b for b in load("nfxs-e-bb")["chassis"]["ears"]["rolled"]}


def test_the_shelf_states_the_two_brackets_that_hold_it_stood_on_its_side_at_the_sizes_the_sheet_prints():
    brackets = shelf_brackets()
    assert sorted(brackets) == ["above", "below"]
    for name, size in BRACKETS.items():
        got = brackets[name]
        assert got["side"] == name
        for key, value in size.items():
            assert got[key] == value, (name, key)
        assert got["length"] > 465.1,"long enough to reach the hole columns of both posts"
        assert got["ear-w"] > 0 and got["color"].startswith("#"), name


def test_the_brackets_say_which_figures_they_are_read_from_and_what_is_estimated():
    doc = load("nfxs-e-bb")
    note = doc["provenance"]["rolled-brackets"]
    assert note["confidence"] == "drawing"
    for words in ("Figure 84", "Table 2", "Table 3", "ear width", "colour"):
        assert words in note["note"], words
    assert any(g["what"] == "rolled-brackets" for g in doc["gaps"])


def test_a_device_that_states_no_brackets_publishes_none_and_one_that_does_publishes_floats():
    from portrayal.render import published_ears
    assert "rolled" not in published_ears({"behind": True})
    out = published_ears({"rolled": [{"id": "x", "side": "below", "bar-h": 25, "length": 486, "ear-h": 92, "ear-w": 28}]})
    assert out == {"rolled": [{"id": "x", "side": "below", "bar-h": 25.0, "length": 486.0, "ear-h": 92.0, "ear-w": 28.0}]}


def test_the_shelf_validates_against_the_device_schema_with_the_brackets():
    import json
    import jsonschema
    schema = json.loads((ROOT / "spec" / "schemas" / "device.schema.json").read_text())
    jsonschema.validate(load("nfxs-e-bb"), schema)


def test_the_tray_and_the_baffle_state_that_they_have_no_ears_and_draw_no_generic_ear():
    from portrayal import ears
    for name in PARTS:
        doc = load(name)
        assert doc["chassis"]["ears"] == {"none": True}, name
        assert ears.plan(doc) is None, name
        note = doc["provenance"]["ears"]
        assert "Figure 84" in note["note"], name


def test_a_device_that_states_none_is_unchanged_and_the_key_is_published_only_when_stated():
    from portrayal import ears
    from portrayal.render import published_ears
    assert published_ears({"none": True}) == {"none": True}
    assert "none" not in published_ears({"behind": True})
    assert "none" not in published_ears({"h": 40})
    box = {"chassis": {"width": 350.01, "height": 89.02, "depth": 251.97}, "views": {"front": {"size": {"w": 350.01, "h": 89.02}}}}
    assert ears.plan(box)["flange"] > 60, "a box that states nothing gets its ear as before"
    box["chassis"]["ears"] = {"none": False}
    assert ears.plan(box) is not None


def test_the_none_key_is_a_boolean_in_the_device_schema():
    import json
    import jsonschema
    schema = json.loads((ROOT / "spec" / "schemas" / "device.schema.json").read_text())
    ears = schema["properties"]["chassis"]["properties"]["ears"]["oneOf"][1]["properties"]
    assert ears["none"]["type"] == "boolean"


def test_each_part_names_its_unit_data_sheet_with_a_hash_and_says_the_units_are_read_off_a_figure():
    for name in PARTS:
        doc = load(name)
        assert "Vertical shelf mount kit unit data sheet" in doc["datasheet"]["title"], name
        assert len(doc["datasheet"]["sha256"]) == 64, name
        assert doc["provenance"]["units"]["confidence"] == "drawing", name
        assert "Figure 84" in doc["provenance"]["units"]["note"], name
