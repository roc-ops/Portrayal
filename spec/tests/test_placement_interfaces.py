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
COMP_SCHEMA = yaml.safe_load((ROOT / "spec/schemas/component.schema.json").read_text())
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


def test_l105_is_registered_for_devices_and_components():
    assert lint.RULES["L105"][0] == "component, device"


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


# --- the same rule on a component part --------------------------------------
#
# A line card's cages are `parts:`, not placements. The FELT-B numbers its 18
# cages' ports 1-36 - a CSFP takes both of a cage's pair, an SFP the odd one -
# and exported 18 interfaces until a part could say so (UDS section 45.4.2.1).

PART = COMP_SCHEMA["properties"]["parts"]["items"]


def _vp(p):
    sub = {**PART, "$defs": COMP_SCHEMA["$defs"]}
    return list(jsonschema.Draft202012Validator(sub).iter_errors(p))


def test_a_component_part_may_declare_the_interfaces_it_presents():
    assert not _vp({"ref": "std/sfp-ganged@1", "id": "sfp-1", "at": [0, 0], "interfaces": ["port-1", "port-2"]})


@pytest.mark.parametrize("bad", [["port-1"], ["port-1", "port-1"], ["Port 1", "port-2"], []])
def test_a_part_with_one_interface_a_repeat_or_a_bad_id_is_refused(bad):
    assert _vp({"ref": "std/sfp-ganged@1", "id": "sfp-1", "at": [0, 0], "interfaces": bad})


def _card(parts, elements=None):
    return {"groups": {"sfp": {"term": "Port", "role": "traffic"},
                       "leds": {"term": "LED", "role": "indicator"}},
            "elements": elements or {}, "parts": parts}


def _lint_card(card):
    with lint.collecting() as got:
        lint.lint_component_part_interfaces(pathlib.Path("c.yaml"), card, [LIB])
    return got


def test_valid_part_interfaces_are_clean():
    got = _lint_card(_card([
        {"ref": "std/sfp-ganged@1", "id": "sfp-1", "group": "sfp", "interfaces": ["port-1", "port-2"]},
        {"ref": "std/sfp-ganged@1", "id": "sfp-2", "group": "sfp", "interfaces": ["port-3", "port-4"]}]))
    assert not got.errors and not got.warnings


def test_a_part_interface_may_not_share_an_id_with_a_part_or_element():
    got = _lint_card(_card([
        {"ref": "std/sfp-ganged@1", "id": "sfp-1", "group": "sfp", "interfaces": ["port-1", "led-1"]},
        {"ref": "std/rj45@2", "id": "port-1", "group": "sfp"}],
        elements={"led-1": {"at": [0, 0], "size": [1, 1]}}))
    assert any("[L105]" in e and "'port-1'" in e for e in got.errors), got.errors
    assert any("[L105]" in e and "'led-1'" in e for e in got.errors), got.errors


def test_two_parts_may_not_present_the_same_interface():
    got = _lint_card(_card([
        {"ref": "std/sfp-ganged@1", "id": "sfp-1", "group": "sfp", "interfaces": ["port-1", "port-2"]},
        {"ref": "std/sfp-ganged@1", "id": "sfp-2", "group": "sfp", "interfaces": ["port-2", "port-3"]}]))
    assert any("[L105]" in e and "port-2" in e for e in got.errors), got.errors


def test_only_a_port_part_presents_interfaces():
    got = _lint_card(_card([{"ref": "common/led-dot@1", "id": "lamp", "group": "leds",
                             "interfaces": ["a", "b"]}]))
    assert any("[L105]" in e for e in got.errors), got.errors


def test_build_module_emits_one_interface_per_listed_name_typed_from_the_cage():
    card = {"name": "t", "attrs": {"model": "T"},
            "groups": {"sfp": {"term": "Port", "role": "traffic", "attrs": {"media": "sfp", "speed": "1g"}}},
            "parts": [{"ref": "std/sfp-ganged@1", "id": "sfp-1", "group": "sfp", "at": [0, 0],
                       "interfaces": ["port-1", "port-2"]},
                      {"ref": "std/sfp-ganged@1", "id": "sfp-2", "group": "sfp", "at": [0, 0]}]}
    got = {i["name"]: i["type"] for i in dx.build_module(card, "X")["interfaces"]}
    assert got == {"port-1": "1000base-x-sfp", "port-2": "1000base-x-sfp", "sfp-2": "1000base-x-sfp"}


def _module_export(target, model):
    for p in sorted((LIB / f"exports/{target}/module-types/Nokia").glob("*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        if d.get("model") == model:
            return d
    return None


# (model, ports): each cage numbers two ports, 2n-1 and 2n. Sources: FELT-B
# UDS A23 45.4.2.1; FELT-C ETSI UDS 33.4.2.1; FELT-D UDS A23 47.4.1.1; NELT-B ANSI
# UDS R6.9 45.4.2.1; ME40-1GB-CSFP MDA-e guide 4.2.1.
CSFP_CARDS = [("FELT-B", 36), ("FELT-C", 32), ("FELT-D", 36), ("NELT-B", 36), ("ME40-1GB-CSFP", 40)]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("model,ports", CSFP_CARDS)
def test_a_csfp_card_exports_every_port_it_numbers(target, model, ports):
    d = _module_export(target, model)
    assert d is not None, model
    names = [i["name"] for i in d.get("interfaces") or []]
    assert len(names) == len(set(names)), "a name exported twice"
    assert {n for n in names if n.startswith("port-")} == {f"port-{n}" for n in range(1, ports + 1)}
    # the cages are where the ports live, not ports themselves
    assert not any(n.startswith(("sfp-", "csfp-")) for n in names), names
