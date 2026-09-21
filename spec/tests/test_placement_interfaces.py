"""A placement that presents several interfaces (#443).

A Compact SFP module fits a standard SFP cage and carries TWO independent BiDi
fibre connections, each its own switch interface. The switch's silicon has both
whether or not a module is seated - the ECS4530-54CSFP is 48 GE ports whichever
optics are fitted - and this library ships devices unpopulated (pluggables
slotting design: "Portrayal ships no populated device"). So the two interfaces
belong to the HOST CAGE, not to the module, and a placement says so with
`interfaces: [port-1, port-3]`.

Before this, a cage was one interface: the ECS4530s exported 24 fibre interfaces
where the switch has 48, and each carried a `csfp-dual-interface` gap for it.
"""
import pathlib

import jsonschema
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import lint                     # noqa: E402
from portrayal import dcim_export as dx        # noqa: E402

SCHEMA = yaml.safe_load((ROOT / "spec/schemas/device.schema.json").read_text())
PLACEMENT = SCHEMA["properties"]["views"]["additionalProperties"]["properties"]["components"][
    "properties"]["placements"]["items"]


def _v(p):
    # the placement schema $refs the device schema's $defs, so it is validated
    # with those in scope rather than cut out on its own
    sub = {**PLACEMENT, "$defs": SCHEMA["$defs"]}
    return list(jsonschema.Draft202012Validator(sub).iter_errors(p))


# --- the schema ------------------------------------------------------------

def test_a_placement_may_declare_the_interfaces_it_presents():
    assert not _v({"ref": "std/sfp-ganged@1", "id": "cage-1", "at": [0, 0], "interfaces": ["port-1", "port-3"]})


@pytest.mark.parametrize("bad", [["port-1"], ["port-1", "port-1"], ["Port 1", "port-2"], []])
def test_one_interface_a_repeat_or_a_bad_id_is_refused(bad):
    """One interface is just the placement; the key exists to say MORE than one."""
    assert _v({"ref": "std/sfp-ganged@1", "id": "cage-1", "at": [0, 0], "interfaces": bad})


# --- the rule --------------------------------------------------------------

def _dev(placements):
    return {"groups": {"csfp": {"term": "Port", "role": "traffic"},
                       "leds": {"term": "LED", "role": "indicator"}},
            "views": {"front": {"size": {"w": 440, "h": 44},
                                "components": {"placements": placements}}}}


def _lint(dev):
    with lint.collecting() as got:
        lint.lint_device_placement_interfaces(pathlib.Path("t.yaml"), dev, [LIB])
    return got


def test_l105_is_registered_as_a_device_rule():
    assert lint.RULES["L105"][0] == "device"


def test_valid_interfaces_are_clean():
    got = _lint(_dev([
        {"ref": "std/sfp-ganged@1", "id": "cage-1", "group": "csfp", "interfaces": ["port-1", "port-3"]},
        {"ref": "std/sfp-ganged@1", "id": "cage-2", "group": "csfp", "interfaces": ["port-2", "port-4"]}]))
    assert not got.errors and not got.warnings


def test_an_interface_may_not_share_an_id_with_a_placement():
    """The ECS4530's combo RJ-45s were `port-45`..`port-48` - exactly the ids the
    twelfth stack's CSFP interfaces need. Two connectors, one DCIM name."""
    got = _lint(_dev([
        {"ref": "std/sfp-ganged@1", "id": "cage-12", "group": "csfp", "interfaces": ["port-45", "port-47"]},
        {"ref": "std/rj45@2", "id": "port-45", "group": "csfp"}]))
    assert any("[L105]" in e and "port-45" in e for e in got.errors), got.errors


def test_two_placements_may_not_present_the_same_interface():
    got = _lint(_dev([
        {"ref": "std/sfp-ganged@1", "id": "cage-1", "group": "csfp", "interfaces": ["port-1", "port-3"]},
        {"ref": "std/sfp-ganged@1", "id": "cage-2", "group": "csfp", "interfaces": ["port-3", "port-5"]}]))
    assert any("[L105]" in e and "port-3" in e for e in got.errors), got.errors


def test_only_a_port_presents_interfaces():
    got = _lint(_dev([{"ref": "common/led-dot@1", "id": "lamp", "group": "leds",
                       "interfaces": ["a", "b"]}]))
    assert any("[L105]" in e for e in got.errors), got.errors


# --- the export ------------------------------------------------------------

def _export(model):
    for p in sorted((LIB / "exports/netbox/device-types").glob("*/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        if d.get("model") == model:
            return d
    return None


@pytest.mark.parametrize("model", ["ECS4530-54CSFP", "ECS4530-54CSFP-DC-I"])
def test_the_ecs4530_exports_every_port_its_model_number_names(model):
    """54 = 48 GE (24 CSFP cages, two interfaces each) + 4 SFP+ + 2 QSFP+, the
    '54' in the model number. The four combo copper jacks are real connectors a
    DCIM must be able to cable, so they export too, under their own names."""
    d = _export(model)
    assert d is not None, model
    names = [i["name"] for i in d.get("interfaces") or []]
    assert len(names) == len(set(names)), "a name exported twice"
    ports = {n for n in names if n.startswith("port-")}
    assert ports == {f"port-{n}" for n in range(1, 55)}, sorted(ports ^ {f"port-{n}" for n in range(1, 55)})
    assert {f"copper-{n}" for n in range(45, 49)} <= set(names)
    assert not any(n.startswith("csfp-") for n in names), "a cage exported as an interface"
    fibre = [i for i in d["interfaces"] if i["name"] in {f"port-{n}" for n in range(1, 49)}]
    assert {i["type"] for i in fibre} == {"1000base-x-sfp"}
