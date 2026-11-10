"""The Juniper EX-UM uplink modules of the EX3200 and EX4200 switches.

Four module types, one component for each maker part number: EX-UM-4SFP, EX-UM-2X4SFP, EX-UM-2X4SFP-M
and EX-UM-2XFP. The EX3200 and EX4200 hardware guides draw the same three figures (g020107, g020123,
g020108) and the EX4200 guide prints the four part numbers. Each test reads the YAML a contributor edits.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# component -> (model as printed, cages, cage interface, the lamps it draws)
MODULES = {
    "ex-um-4sfp": ("EX-UM-4SFP", 4, "sfp", 8),
    "ex-um-2x4sfp": ("EX-UM-2X4SFP", 4, "sfp", 9),
    "ex-um-2x4sfp-m": ("EX-UM-2X4SFP-M", 4, "sfp", 9),
    "ex-um-2xfp": ("EX-UM-2XFP", 2, "xfp", 4),
}
COVER = {"ex3200": "ex3200-uplink-cover", "ex4200": "ex4200-uplink-cover"}
# device -> the modules its slot takes: the EX3200 guide lists the SFP, SFP+ (and its MACsec variant) and
# XFP modules, the EX4200 guide lists all four by part number
TAKES = {
    "ex3200": set(MODULES),
    "ex4200": set(MODULES),
}
DEVICES = {
    "ex3200": ["ex3200-24t", "ex3200-48t", "ex3200-24p", "ex3200-48p"],
    "ex4200": ["ex4200-24t", "ex4200-48t", "ex4200-24p", "ex4200-48p", "ex4200-24px", "ex4200-48px",
               "ex4200-24f"],
}
ALL = [(fam, dev) for fam, devs in DEVICES.items() for dev in devs]


def contract(name):
    return yaml.safe_load((LIB / "components/juniper" / name / "v1/contract.yaml").read_text())


def device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def layout(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "layout.yaml").read_text())


def front_bay(d):
    return {b["id"]: b for b in d["views"]["front"]["components"]["bays"]}["uplink"]


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_is_a_line_card_that_fills_the_uplink_slot(comp):
    c = contract(comp)
    assert (c["kind"], c["class"], c["behaviour"]) == ("module", "line-card", "fills")
    assert c["attrs"]["model"] == MODULES[comp][0]
    assert (c["size"]["w"], c["size"]["h"]) == (63.0, 14.5)  # the slot the cover panels close


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_has_the_cages_and_lamps_its_figure_draws(comp):
    _model, cages, interface, lamps = MODULES[comp]
    parts = contract(comp)["parts"]
    ports = [p for p in parts if p["ref"].startswith("std/") and p["id"].startswith("port-")]
    assert len(ports) == cages
    assert {p["ref"] for p in ports} == ({"std/xfp@1"} if interface == "xfp" else {"std/sfp-ganged@1"})
    assert len([p for p in parts if p["ref"] == "common/led-dot@1"]) == lamps


@pytest.mark.parametrize("comp", ["ex-um-2x4sfp", "ex-um-2x4sfp-m"])
def test_the_sfp_plus_modules_take_sfp_plus_in_ports_0_and_2_only(comp):
    """Figure 6: "SFP+ transceivers are supported in ports 0 and 2"; SFP in all four."""
    ports = {p["id"]: p for p in contract(comp)["parts"] if p["id"].startswith("port-")}
    media = {i: p["attrs"]["media"] for i, p in ports.items()}
    assert media == {"port-0": "sfp-plus", "port-1": "sfp", "port-2": "sfp-plus", "port-3": "sfp"}


def test_one_maker_part_number_is_one_component():
    """A part number is never carried by a second component (no twin)."""
    seen = {}
    for path in (LIB / "components").glob("*/*/v*/contract.yaml"):
        model = str((yaml.safe_load(path.read_text()).get("attrs") or {}).get("model", ""))
        if model.startswith("EX-UM-"):
            seen.setdefault(model, []).append(path.parent.parent.name)
    assert {m: sorted(v) for m, v in seen.items()} == {MODULES[c][0]: [c] for c in MODULES}


@pytest.mark.parametrize("fam,dev", ALL)
def test_the_uplink_slot_takes_the_modules_the_guide_lists_and_ships_the_cover(fam, dev):
    bay = front_bay(device(dev))
    want = {f"juniper/{COVER[fam]}@1"} | {f"juniper/{c}@1" for c in TAKES[fam]}
    assert set(bay["accepts"]) == want
    assert bay["default"] == f"juniper/{COVER[fam]}@1"


@pytest.mark.parametrize("dev", ["ex3200-24t", "ex4200-24t"])
def test_one_example_configuration_seats_each_module_and_none_is_orderable(dev):
    """An example shows a module in the slot; it is an illustration, so it is never an order code."""
    cfgs = device(dev)["configurations"]
    seated = {k: c["bays"]["uplink"] for k, c in cfgs.items() if c.get("kind") == "example"}
    assert seated == {"um-4sfp": "juniper/ex-um-4sfp@1", "um-2x4sfp": "juniper/ex-um-2x4sfp@1",
                      "um-2x4sfp-m": "juniper/ex-um-2x4sfp-m@1", "um-2xfp": "juniper/ex-um-2xfp@1"}
    assert not any(c.get("part-numbers") for k, c in cfgs.items() if k in seated)


@pytest.mark.parametrize("fam,dev", ALL)
def test_the_layout_no_longer_lists_the_modules_as_a_gap(fam, dev):
    gaps = {g["what"] for g in layout(dev).get("gaps") or []}
    assert "uplink-modules" not in gaps
