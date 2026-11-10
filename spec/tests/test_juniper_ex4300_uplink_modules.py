"""The Juniper EX-UM uplink modules of the EX4300 switches.

Five module types, one component for each maker part number: EX-UM-4X4SFP (24-port and 48-port models),
EX-UM-2QSFP and EX-UM-8X8SFP (EX4300-32F), EX-UM-2QSFP-MR and EX-UM-4SFPP-MR (EX4300-48MP). The EX4300
hardware guide draws each face flat (Figures 18, 20, 22, 24 and 25). Each test reads the YAML a contributor edits.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# component -> (model as printed, cages, cage ref, cage media, lamps of the cage kind, weight as printed)
MODULES = {
    "ex-um-4x4sfp": ("EX-UM-4X4SFP", 4, "std/sfp-ganged@1", "sfp-plus", ("common/led-rect-sm@1", 8), "0.44 lb (0.2 kg)"),
    "ex-um-2qsfp": ("EX-UM-2QSFP", 2, "std/qsfp-ganged@1", "qsfp", ("common/led-dot@1", 5), "0.61 lb (0.28 kg)"),
    "ex-um-8x8sfp": ("EX-UM-8X8SFP", 8, "std/sfp-ganged@1", "sfp-plus", ("common/led-arrow-sm@1", 16), "0.74 lb (0.34 kg)"),
    "ex-um-2qsfp-mr": ("EX-UM-2QSFP-MR", 2, "std/qsfp-ganged@1", "qsfp28", ("common/led-dot@1", 8), "0.57 lb (0.26 kg)"),
    "ex-um-4sfpp-mr": ("EX-UM-4SFPP-MR", 4, "std/sfp-ganged@1", "sfp-plus", ("common/led-dot@1", 8), "0.57 lb (0.26 kg)"),
}
# device family -> (the blank each bay ships, the modules it takes, the slot size)
FAMILY = {
    "24-48": ("ex4300-uplink-blank", ["ex-um-4x4sfp"], (73.9, 18.7)),
    "32f": ("ex4300-32f-uplink-blank", ["ex-um-2qsfp", "ex-um-8x8sfp"], (87.0, 40.7)),
    "48mp": ("ex4300-48mp-uplink-blank", ["ex-um-2qsfp-mr", "ex-um-4sfpp-mr"], (66.6, 24.5)),
}
DEVICES = {
    "ex4300-24t": "24-48", "ex4300-24p": "24-48", "ex4300-48t": "24-48", "ex4300-48p": "24-48",
    "ex4300-32f": "32f", "ex4300-48mp": "48mp",
}
EXAMPLES = {
    "ex4300-24t": {"um-4x4sfp": "ex-um-4x4sfp"},
    "ex4300-32f": {"um-2qsfp": "ex-um-2qsfp", "um-8x8sfp": "ex-um-8x8sfp"},
    "ex4300-48mp": {"um-2qsfp-mr": "ex-um-2qsfp-mr", "um-4sfpp-mr": "ex-um-4sfpp-mr"},
}


def contract(name):
    return yaml.safe_load((LIB / "components/juniper" / name / "v1/contract.yaml").read_text())


def device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def layout(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "layout.yaml").read_text())


def front_bay(d):
    return {b["id"]: b for b in d["views"]["front"]["components"]["bays"]}["uplink"]


def module_slot(comp):
    return next(FAMILY[f][2] for f in FAMILY if comp in FAMILY[f][1])


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_is_a_line_card_that_fills_the_slot_it_goes_in(comp):
    c = contract(comp)
    assert (c["kind"], c["class"], c["behaviour"]) == ("module", "line-card", "fills")
    assert c["attrs"]["model"] == MODULES[comp][0]
    assert (c["size"]["w"], c["size"]["h"]) == module_slot(comp)


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_has_the_cages_and_lamps_its_figure_draws(comp):
    _model, cages, cage_ref, media, (lamp_ref, lamps), _weight = MODULES[comp]
    parts = contract(comp)["parts"]
    ports = [p for p in parts if p["id"].startswith("port-")]
    assert len(ports) == cages
    assert {p["ref"] for p in ports} == {cage_ref}
    assert {p["attrs"]["media"] for p in ports} == {media}
    assert len([p for p in parts if p["ref"] == lamp_ref and p["id"].startswith("led-")]) == lamps


def test_the_eight_port_module_has_two_rows_of_four_cages():
    """Figure 22: even numbers on the upper row, odd on the lower, four columns."""
    ports = {p["id"]: p for p in contract("ex-um-8x8sfp")["parts"] if p["id"].startswith("port-")}
    upper = {i for i, p in ports.items() if p["at"][1] < 15}
    assert upper == {f"port-{n}" for n in (0, 2, 4, 6)}
    assert len({p["at"][0] for p in ports.values()}) == 4


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_states_the_guides_weight_and_no_invented_power(comp):
    c = contract(comp)
    assert c["attrs"]["weight"] == MODULES[comp][5]
    assert c["attrs"]["power-absent"] == "not-published"
    assert not any(k.startswith("power-draw") for k in c["attrs"])


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_fits_inside_its_slot(comp):
    c = contract(comp)
    w, h = c["size"]["w"], c["size"]["h"]
    for p in c["parts"]:
        if p["ref"].startswith("std/"):
            assert 0 <= p["at"][0] and p["at"][0] + 14.25 <= w
            assert 0 <= p["at"][1] and p["at"][1] + 9.5 <= h


@pytest.mark.heavy
@pytest.mark.parametrize("comp", MODULES)
def test_one_maker_part_number_is_one_component(comp):
    """A part number is never carried by a second component (no twin)."""
    holders = []
    for path in (LIB / "components").glob("*/*/v*/contract.yaml"):
        model = str((yaml.safe_load(path.read_text()).get("attrs") or {}).get("model", ""))
        if model == MODULES[comp][0]:
            holders.append(path.parent.parent.name)
    assert holders == [comp]


@pytest.mark.parametrize("dev,fam", DEVICES.items())
def test_the_uplink_bay_takes_the_modules_the_guide_lists_and_ships_the_cover(dev, fam):
    blank, modules, (w, h) = FAMILY[fam]
    bay = front_bay(device(dev))
    assert set(bay["accepts"]) == {f"juniper/{blank}@1"} | {f"juniper/{m}@1" for m in modules}
    assert bay["default"] == f"juniper/{blank}@1"
    assert (bay["size"]["w"], bay["size"]["h"]) == (w, h)


@pytest.mark.parametrize("dev", EXAMPLES)
def test_one_example_configuration_seats_each_module_and_none_is_orderable(dev):
    """An example shows a module in the slot; it is an illustration, so it is never an order code."""
    cfgs = device(dev)["configurations"]
    seated = {k: c["bays"]["uplink"] for k, c in cfgs.items() if c.get("kind") == "example"}
    assert seated == {k: f"juniper/{m}@1" for k, m in EXAMPLES[dev].items()}
    assert not any(c.get("part-numbers") for k, c in cfgs.items() if k in seated)


@pytest.mark.parametrize("dev", DEVICES)
def test_the_layout_no_longer_lists_the_modules_as_a_gap(dev):
    gaps = {g["what"] for g in layout(dev).get("gaps") or []}
    assert "uplink-modules" not in gaps
