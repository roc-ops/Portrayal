"""A ceiling mount, and a powered device's PoE standard and draw.

The library could say what a switch hands out over PoE and could not describe
the box at the other end of the cable. `chassis.mount` had no value for a
ceiling, and nothing stated, as numbers, which 802.3 standard a powered device
needs or the most it takes in. This module holds what is now true of the
library: the schema's `ceiling` value and its four `poe-pd-*` keys, the lint
rule that relates them, what the DCIM exports say, and the two ReadyLinks
access points that are the first devices to use them.
"""
import copy
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())

from portrayal import comparable        # noqa: E402
from portrayal import dcim_export as dx  # noqa: E402
from portrayal import lint              # noqa: E402

WALL_PLATE = "ipc-apwf6-poe-wp"
CEILING = "ipc-apwf7-poe-cl"
DEVICES = (WALL_PLATE, CEILING)
PD_KEYS = ("poe-pd-standard", "poe-pd-standard-min", "poe-pd-class", "poe-pd-max-w")
STANDARDS = ["802.3af", "802.3at", "802.3bt"]


def _device(name):
    return yaml.safe_load((LIB / "devices/readylinks" / name / "device.yaml").read_text())


def _export(vendor, name):
    model = name.upper()
    path = LIB / "exports" / vendor / "device-types/ReadyLinks" / f"{model}.yaml"
    return yaml.safe_load(path.read_text())


def _power_properties():
    return SCHEMA["properties"]["attrs"]["properties"]["power"]["properties"]


# --- the schema ---------------------------------------------------------------

def test_the_schema_names_a_ceiling_mount():
    mount = SCHEMA["properties"]["chassis"]["properties"]["mount"]
    assert "ceiling" in mount["enum"]
    assert "`ceiling` is one that fixes to a ceiling or hangs below it" in mount["description"]


def test_the_schema_defines_the_four_pd_keys_as_values_a_tool_can_read():
    props = _power_properties()
    assert all(key in props for key in PD_KEYS)
    assert props["poe-pd-standard"]["enum"] == STANDARDS
    assert props["poe-pd-standard-min"]["enum"] == STANDARDS
    assert props["poe-pd-class"]["type"] == "integer"
    assert (props["poe-pd-class"]["minimum"], props["poe-pd-class"]["maximum"]) == (0, 8)
    assert props["poe-pd-max-w"]["type"] == "number"
    assert props["poe-pd-max-w"]["exclusiveMinimum"] == 0


@pytest.mark.parametrize("key,value", [
    ("poe-pd-standard", "802.3at PoE+"),
    ("poe-pd-standard-min", "af"),
    ("poe-pd-class", "4"),
    ("poe-pd-class", 9),
    ("poe-pd-max-w", "25 W"),
    ("poe-pd-max-w", 0),
])
def test_the_schema_refuses_a_pd_value_a_tool_could_not_read(key, value):
    power = {"poe-pd-standard": "802.3at", "poe-pd-max-w": 25}
    power[key] = value
    doc = {"attrs": {"power": power}}
    validator = Draft202012Validator(SCHEMA["properties"]["attrs"])
    assert list(validator.iter_errors(doc["attrs"]))


@pytest.mark.parametrize("name", DEVICES)
def test_each_access_point_validates_against_the_schema(name):
    errors = list(Draft202012Validator(SCHEMA).iter_errors(_device(name)))
    assert not errors, [e.message for e in errors[:3]]


# --- the access points --------------------------------------------------------

def test_the_wall_plate_and_the_ceiling_unit_say_how_they_are_installed():
    assert _device(WALL_PLATE)["chassis"]["mount"] == "wall"
    assert _device(CEILING)["chassis"]["mount"] == "ceiling"
    for name in DEVICES:
        assert "ru" not in _device(name)["chassis"]


@pytest.mark.parametrize("name", DEVICES)
def test_a_tool_reads_each_access_points_standard_and_draw_as_numbers(name):
    power = _device(name)["attrs"]["power"]
    assert power["poe-pd-standard"] in STANDARDS
    assert STANDARDS.index(power["poe-pd-standard-min"]) < STANDARDS.index(power["poe-pd-standard"])
    for key in ("poe-pd-max-w", "poe-budget-w"):
        assert type(power[key]) in (int, float) and power[key] > 0, key
    assert "poe-pd-class" not in power, "neither data sheet prints a class"


def test_the_draw_that_is_the_whole_intake_is_never_below_what_the_unit_uses_and_hands_on():
    power = _device(CEILING)["attrs"]["power"]
    assert power["poe-pd-max-w"] == pytest.approx(power["power-self-max-w"] + power["poe-budget-w"])


@pytest.mark.parametrize("name", DEVICES)
def test_the_access_point_does_not_state_the_rack_fields_it_has_no_use_for(name):
    chassis = _device(name)["chassis"]
    assert not any(key in chassis for key in ("ru", "full-depth", "overhang", "ears", "kits"))


@pytest.mark.parametrize("vendor", ("netbox", "nautobot"))
@pytest.mark.parametrize("name", DEVICES)
def test_each_access_point_exports_as_a_box_that_takes_no_rack_unit(vendor, name):
    exported = _export(vendor, name)
    assert exported["u_height"] == 0
    assert exported["is_full_depth"] is False
    assert exported["manufacturer"] == "ReadyLinks"


@pytest.mark.parametrize("vendor", ("netbox", "nautobot"))
def test_the_export_comment_says_where_the_box_goes_and_what_it_needs(vendor):
    wall = _export(vendor, WALL_PLATE)["comments"]
    ceiling = _export(vendor, CEILING)["comments"]
    assert "Wall-mounted; not rack-mounted." in wall
    assert "Ceiling-mounted; not rack-mounted." in ceiling
    assert "PoE powered device: 802.3at (runs on 802.3af), at most 25 W at the PD input." in wall
    assert "PoE powered device: 802.3bt (runs on 802.3at), at most 72.95 W at the PD input." in ceiling


# --- the DCIM export ----------------------------------------------------------

def test_a_ceiling_box_exports_no_rack_units_and_says_so():
    assert dx.u_height({"mount": "ceiling"}) == 0.0
    assert dx.is_full_depth({"mount": "ceiling"}) is False
    assert dx.MOUNT_PROSE["ceiling"] == "Ceiling-mounted; not rack-mounted."


def test_the_pd_sentence_names_the_standard_the_floor_the_class_and_the_draw():
    power = {"poe-pd-standard": "802.3bt", "poe-pd-standard-min": "802.3at",
             "poe-pd-class": 6, "poe-pd-max-w": 60}
    comment = dx.comments_for({"attrs": {"power": power}}, "base", {})
    assert "PoE powered device: 802.3bt (runs on 802.3at), class 6, at most 60 W at the PD input." in comment


def test_a_box_that_states_no_pd_standard_gets_no_pd_sentence():
    assert "PoE powered device" not in dx.comments_for({"attrs": {"power": {"poe-budget-w": 120}}}, "base", {})


# --- the lint rule that relates the keys --------------------------------------

def _found(power):
    with lint.collecting() as found:
        lint.lint_device_poe_pd("device.yaml", {"attrs": {"power": power}})
    return ([m for m in found.errors if "[L198]" in m], [m for m in found.warnings if "[L198]" in m])


def test_L198_a_consistent_set_of_keys_is_quiet():
    assert _found({"poe-pd-standard": "802.3at", "poe-pd-standard-min": "802.3af",
                   "poe-pd-class": 4, "poe-pd-max-w": 25}) == ([], [])


def test_L198_the_floor_is_stated_with_the_standard_and_below_it():
    assert _found({"poe-pd-standard-min": "802.3af"})[0]
    assert _found({"poe-pd-standard": "802.3at", "poe-pd-standard-min": "802.3at"})[0]
    assert _found({"poe-pd-standard": "802.3at", "poe-pd-standard-min": "802.3bt"})[0]


def test_L198_a_class_is_stated_with_a_standard():
    assert _found({"poe-pd-class": 4})[0]


def test_L198_a_draw_with_no_standard_cannot_be_checked_against_a_port():
    errors, warnings = _found({"poe-pd-max-w": 25})
    assert not errors and warnings


def test_L198_the_intake_is_at_least_what_the_unit_uses_plus_what_it_hands_on():
    base = {"poe-pd-standard": "802.3bt", "power-self-max-w": 60, "poe-budget-w": 12.95}
    assert _found({**base, "poe-pd-max-w": 60})[1]
    assert not _found({**base, "poe-pd-max-w": 72.95})[1]
    # prose on either side is not a number and is not summed
    assert not _found({**base, "poe-budget-w": "12.95 W", "poe-pd-max-w": 60})[1]


def test_L198_a_box_that_gives_and_takes_poe_states_its_whole_intake():
    errors, warnings = _found({"poe-pd-standard": "802.3at", "poe-budget-w": 10})
    assert not errors and warnings
    assert not _found({"poe-pd-standard": "802.3at", "poe-budget-w": 10, "poe-pd-max-w": 25})[1]


def test_L198_is_in_the_catalogue_beside_the_others():
    assert "L198" in lint.RULES


@pytest.mark.parametrize("key", PD_KEYS)
def test_L28_a_module_states_no_pd_key(key):
    contract = {"kind": "module", "name": "m", "class": "line-card", "attrs": {key: 1}}
    with lint.collecting() as found:
        lint.lint_component_power("contract.yaml", contract)
    assert any("[L28]" in m and key in m for m in found.errors)


# --- L125 and the comparable facts --------------------------------------------

def test_L125_a_ceiling_box_states_no_rack_units():
    def l125(chassis):
        with lint.collecting() as found:
            lint.lint_device_mount("device.yaml", {"chassis": chassis})
        return [m for m in found.errors + found.warnings if "[L125]" in m]
    assert not l125({"mount": "ceiling"})
    assert l125({"mount": "ceiling", "ru": 1})
    assert l125({"mount": "ceiling", "full-depth": False})
    assert "ceiling" in lint.RULES["L125"][1]


def test_the_comparable_facts_read_the_standard_and_the_draw():
    facts = comparable.resolve(copy.deepcopy(_device(CEILING)))
    assert [r["value"] for r in facts["poe-pd-max-w"]["readings"]] == [72.95]
    assert [r["value"] for r in facts["poe-pd-standard"]["readings"]] == ["802.3bt"]
