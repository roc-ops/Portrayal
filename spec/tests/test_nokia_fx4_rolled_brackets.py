"""The brackets that hold the 7360 ISAM FX-4 shelf stood on its side, stated by the shelf itself.

A shelf rolled a quarter turn in a rack elevation is held by a bar against each edge and an
ear on each post. The FX-4 vertical shelf mount kit's unit data sheet prints each bracket's
height, width and length apart from the tray and the skirts it is assembled with; these tests
hold the shelf's `chassis.ears.rolled` to those figures and to its own provenance.
"""
import json
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "nokia" / "nfxs-f-bb" / "device.yaml"

# Table 3 (shelf horizontal mount bracket) and Table 2 (top cross bracket) of the kit's unit data
# sheet: height, width and length, read as the bar's height, the ear's rise and the span across the posts
BRACKETS = {
    "below": {"bar-h": 25.4, "ear-h": 92.44, "length": 486.41},
    "above": {"bar-h": 31.5, "ear-h": 62.0, "length": 486.75},
}


def load():
    return yaml.safe_load(DEVICE.read_text())


def brackets():
    return {b["id"]: b for b in load()["chassis"]["ears"]["rolled"]}


def test_the_shelf_states_the_two_brackets_at_the_sizes_the_sheet_prints():
    got = brackets()
    assert sorted(got) == ["above", "below"]
    for name, size in BRACKETS.items():
        assert got[name]["side"] == name
        for key, value in size.items():
            assert got[name][key] == value, (name, key)
        assert got[name]["length"] > 465.1, "long enough to reach the hole columns of both posts"
        assert got[name]["ear-w"] > 0, name


def test_the_bracket_colour_is_the_neutral_silver_and_says_it_is_not_a_reading():
    for name, bracket in brackets().items():
        assert bracket["color"] == "#c8cacc", name
    note = load()["provenance"]["rolled-brackets"]["note"]
    assert "neutral" in note and "no held source" in note


def test_the_provenance_cites_the_tables_and_says_what_is_estimated():
    doc = load()
    note = doc["provenance"]["rolled-brackets"]
    assert note["confidence"] in ("drawing", "estimated")
    for words in ("Table 2", "Table 3", "Figure 1", "Figure 2", "ear width", "estimate"):
        assert words in note["note"], words
    assert any(g["what"] == "rolled-brackets" for g in doc["gaps"])


def test_the_shelf_keeps_its_own_body_and_ears_state_only_the_rolled_brackets():
    doc = load()
    assert doc["chassis"]["width"] == 447.0 and doc["chassis"]["height"] == 221.9
    assert set(doc["chassis"]["ears"]) == {"rolled"}


def test_the_shelf_validates_against_the_device_schema():
    schema = json.loads((ROOT / "spec" / "schemas" / "device.schema.json").read_text())
    jsonschema.validate(load(), schema)
