"""A configuration can carry its own attributes and its own export description.

A DCIM device type is made per orderable configuration, and a few builds of one
chassis differ in a figure the device states once: a K build with more memory,
a PoE build with a bigger supply. `configurations.<name>.attrs` takes the same
sections and types as the device's `attrs`, and `export-description` is the
sentence a DCIM shows for that build alone.

THE RULE THESE PIN, AND THE ONE THEY MOST NEED TO HOLD: A KEY ABSENT CHANGES
NOTHING. A configuration with neither key resolves to the device's own `attrs`
and exports the description it always did, so no existing export moves.

  - `manifest.config_attrs(device, cfg)` is the one answer: the configuration's
    value wins key by key within a section, the rest of the section stays the
    device's, and a section the configuration does not name is untouched.
  - the exporter's facts list in `comments` reads it; `description` is the
    configuration's `export-description` where it has one.
  - the schema takes both keys, refuses a description over 200 characters (the
    exporter's own limit, so it is never cut) and refuses either key on an
    `example`, which never exports.
  - `<device>.configs.json` rows carry `attrs`, an object that is empty for a
    configuration with none.

Every document here is synthetic and lives in `tmp_path`; no library device
carries the keys.
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import manifest

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
RENDER = SPEC / "tools/portrayal/render.py"
SCHEMA = json.loads((SPEC / "schemas/device.schema.json").read_text())

# any device with a few configurations will do; the copy is edited, never this
TEMPLATE = LIB / "devices/ufispace/s9600-32x"


def device():
    return {
        "manufacturer": "Acme",
        "model": "X1",
        "name": "x1",
        "description": "Acme X1, a fixed switch with 32 ports. It is built to last.",
        "chassis": {"ru": 1},
        "attrs": {
            "power": {"power-typical-w": 200, "power-max-w": 400},
            "platform": {"memory": "8 GB", "cpu": "Dual-core"},
        },
    }


# --- the resolver -------------------------------------------------------------

def test_a_configurations_value_wins():
    cfg = {"attrs": {"power": {"power-max-w": 437}}}
    assert manifest.config_attrs(device(), cfg)["power"]["power-max-w"] == 437


def test_the_rest_of_the_section_stays_the_devices():
    cfg = {"attrs": {"power": {"power-max-w": 437}}}
    assert manifest.config_attrs(device(), cfg)["power"] == {
        "power-typical-w": 200, "power-max-w": 437}


def test_a_section_the_configuration_does_not_name_is_untouched():
    cfg = {"attrs": {"power": {"power-max-w": 437}}}
    assert manifest.config_attrs(device(), cfg)["platform"] == device()["attrs"]["platform"]


def test_a_configuration_can_add_a_section_the_device_lacks():
    cfg = {"attrs": {"performance": {"fabric-bandwidth": "60 Gbps"}}}
    got = manifest.config_attrs(device(), cfg)
    assert got["performance"] == {"fabric-bandwidth": "60 Gbps"}
    assert got["power"] == device()["attrs"]["power"]


@pytest.mark.parametrize("cfg", [None, {}, {"attrs": {}}, {"attrs": None},
                                 {"description": "no attrs here"}])
def test_none_gives_the_devices(cfg):
    assert manifest.config_attrs(device(), cfg) == device()["attrs"]


def test_a_device_with_no_attrs_gives_the_configurations():
    dev = device()
    del dev["attrs"]
    cfg = {"attrs": {"power": {"power-max-w": 437}}}
    assert manifest.config_attrs(dev, cfg) == {"power": {"power-max-w": 437}}
    assert manifest.config_attrs(dev, {}) == {}


def test_resolving_changes_neither_input():
    dev, cfg = device(), {"attrs": {"power": {"power-max-w": 437}}}
    before = copy.deepcopy((dev, cfg))
    got = manifest.config_attrs(dev, cfg)
    got["power"]["power-max-w"] = 1
    got["platform"]["memory"] = "none"
    assert (dev, cfg) == before


# --- the export ---------------------------------------------------------------

def test_the_facts_list_reads_the_configurations_own_values():
    cfg = {"attrs": {"power": {"power-typical-w": 262, "power-max-w": 437}}}
    body = dx.comments_for(device(), "k", cfg)
    assert "- power.power-typical-w: 262" in body
    assert "- power.power-max-w: 437" in body
    assert "power-max-w: 400" not in body
    assert "- platform.memory: 8 GB" in body


def test_a_configuration_with_its_own_description_exports_it():
    cfg = {"export-description": "Acme X1K, the K build with 16 GB of memory",
           "part-numbers": {"X1K": {}}}
    out = dx.build(device(), "k", cfg, None)
    assert out["description"] == "Acme X1K, the K build with 16 GB of memory"


def test_a_description_at_the_limit_is_not_cut():
    text = "x" * dx.LIMIT
    out = dx.build(device(), "k", {"export-description": text}, None)
    assert out["description"] == text


def test_no_export_description_gives_the_devices_first_sentence():
    out = dx.build(device(), "k", {}, None)
    assert out["description"] == "Acme X1, a fixed switch with 32 ports"


def test_absent_keys_change_nothing():
    """An empty `attrs` and no `attrs` export the same document, and it is the
    device's facts and the device's description."""
    plain = dx.build(device(), "k", {"kind": "orderable"}, None)
    empty = dx.build(device(), "k", {"kind": "orderable", "attrs": {}}, None)
    assert plain == empty
    assert plain["description"] == "Acme X1, a fixed switch with 32 ports"
    assert dx.comments_for(device(), "k", {}) == dx.comments_for(device(), "k", {"attrs": {}})
    assert "- power.power-max-w: 400" in plain["comments"]
    assert "- platform.memory: 8 GB" in plain["comments"]


def test_no_figure_becomes_a_power_port_draw():
    """Figures stay in `comments`: a device type's power ports carry no draw from
    a configuration's attributes."""
    cfg = {"attrs": {"power": {"power-typical-w": 262, "power-max-w": 437}}}
    out = dx.build(device(), "k", cfg, None)
    for port in out.get("power-ports") or []:
        assert "maximum_draw" not in port and "allocated_draw" not in port, port


# --- the schema ---------------------------------------------------------------

def validator():
    root = {"$schema": SCHEMA["$schema"],
            "$defs": SCHEMA["$defs"],
            "properties": {"attrs": SCHEMA["properties"]["attrs"],
                           "configurations": SCHEMA["properties"]["configurations"]},
            "$ref": "#/properties/configurations/additionalProperties"}
    return jsonschema.Draft202012Validator(root)


def errors(cfg):
    return [e.message for e in validator().iter_errors(cfg)]


def test_the_schema_accepts_both_keys():
    assert errors({"kind": "orderable",
                   "export-description": "Acme X1K, the K build",
                   "attrs": {"power": {"power-max-w": 437},
                             "platform": {"memory": "16 GB"}}}) == []


def test_the_schema_accepts_a_configuration_with_neither():
    assert errors({"kind": "orderable"}) == []


def test_the_schema_takes_a_description_of_200_characters():
    assert errors({"kind": "orderable", "export-description": "x" * 200}) == []


def test_the_schema_refuses_a_description_of_201_characters():
    assert errors({"kind": "orderable", "export-description": "x" * 201})


def test_the_schema_holds_attrs_to_the_devices_sections():
    assert errors({"kind": "orderable", "attrs": {"nonsense": {"a": 1}}})
    assert errors({"kind": "orderable", "attrs": {"power": {"power-max-w": None}}})


@pytest.mark.parametrize("extra", [{"export-description": "An illustration"},
                                   {"attrs": {"power": {"power-max-w": 437}}}])
def test_neither_key_is_legal_on_an_example(extra):
    assert errors({"kind": "example", **extra})
    assert errors({"kind": "orderable", **extra}) == []


# --- the index ----------------------------------------------------------------

@pytest.mark.heavy
def test_configs_json_rows_carry_attrs_and_it_is_empty_for_none(tmp_path):
    dev = shutil.copytree(TEMPLATE, tmp_path / "s9600-32x") / "device.yaml"
    doc = yaml.safe_load(dev.read_text())
    names = list(doc["configurations"])
    assert len(names) > 1
    own = {"power": {"power-max-w": 999}}
    doc["configurations"][names[0]]["attrs"] = copy.deepcopy(own)
    dev.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    out = tmp_path / "o"
    r = subprocess.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    idx = json.loads((out / f"{doc['name']}.configs.json").read_text())
    rows = {c["name"]: c for c in idx["configs"]}
    assert rows[names[0]]["attrs"] == own
    for n in names[1:]:
        assert rows[n]["attrs"] == {}, n
