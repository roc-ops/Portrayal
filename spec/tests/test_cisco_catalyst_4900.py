"""The Cisco Catalyst 4900 family: what each model's own guide states, held in the library.

Each device is checked against the guide that describes it, not against a sibling: the
envelope from the guide's table, the ports and their numbering per face, the configurations
with their part numbers, and the supply and fan tray each configuration seats with the
airflow its guide gives. The WS-C4948E-F is read from the Catalyst 4948E and 4948E-F
Switch Installation Guide (OL-21561-02), and its Table 1-1 for the parts.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
COMPONENTS = ROOT / "library/components/cisco"
EXPORTS = ROOT / "library/exports/netbox/device-types/Cisco"


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def component(name):
    return yaml.safe_load((COMPONENTS / name / "v1" / "contract.yaml").read_text())


def placements(d, view):
    comps = d["views"][view]["components"]
    return comps.get("placements") or []


def bays(d, view="rear"):
    return {b["id"]: b for b in d["views"][view]["components"]["bays"]}


def ports(d, group):
    return [p for p in placements(d, "front") if p.get("group") == group]


# --- the WS-C4948E-F: the Catalyst 4948E and 4948E-F guide, OL-21561-02 ---------------


def test_4948e_f_envelope_is_the_guides():
    """Guide Table 1-2 and the data sheet: 1.75 x 17.5 x 19.4 in (4.4 x 44.4 x 49.3 cm), 1RU."""
    c = device("ws-c4948e-f")["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (444.4, 44.45, 492.8, 1)
    assert c["airflow"] == "back-to-front"
    assert c["power"] == "ac"


def test_4948e_f_front_has_fifty_two_ports_numbered_as_printed():
    d = device("ws-c4948e-f")
    rj45 = ports(d, "rj45")
    sfp = ports(d, "sfp-plus")
    assert len(rj45) == 48 and len(sfp) == 4
    assert [p["id"] for p in rj45] == [f"port-{n}" for n in range(1, 49)]
    assert [p["id"] for p in sfp] == [f"port-{n}" for n in range(49, 53)]
    assert {p["ref"] for p in rj45} == {"std/rj45-ganged@2"}
    assert {p["ref"] for p in sfp} == {"std/sfp-ganged@1"}


def test_4948e_f_front_has_console_management_and_reset():
    d = device("ws-c4948e-f")
    mgmt = {p["id"]: p for p in ports(d, "mgmt")}
    assert set(mgmt) == {"console", "mgmt", "reset"}
    assert mgmt["console"]["attrs"]["media"] == "rj45-serial"
    assert mgmt["mgmt"]["attrs"]["media"] == "rj45"
    lamps = {p["id"] for p in placements(d, "front") if p.get("group") == "leds"}
    assert lamps == {"led-ps1", "led-ps2", "led-fan", "led-mgt", "led-status"}


def test_4948e_f_rear_has_two_supply_bays_and_one_fan_tray_bay():
    d = device("ws-c4948e-f")
    b = bays(d)
    assert set(b) == {"psu-1", "fan-tray", "psu-2"}
    for psu in ("psu-1", "psu-2"):
        assert b[psu]["accepts"] == ["cisco/pwr-c49e-300ac-f@1", "cisco/ws-x4994-f@1"]
        assert b[psu]["default"] == "cisco/pwr-c49e-300ac-f@1"
    assert b["fan-tray"]["accepts"] == ["cisco/ws-x4993-f@1"]
    assert b["fan-tray"]["default"] == "cisco/ws-x4993-f@1"


def test_4948e_f_takes_none_of_the_4948es_parts():
    """Guide Table 1-1: the supplies and fan trays are not interchangeable between the two."""
    d = device("ws-c4948e-f")
    seated = {ref for b in bays(d).values() for ref in b["accepts"]}
    assert not seated & {"cisco/pwr-c49e-300ac-r@1", "cisco/ws-x4993@1"}


def test_4948e_f_configurations_carry_the_data_sheets_part_numbers():
    d = device("ws-c4948e-f")
    cfg = d["configurations"]
    assert cfg["ac"]["kind"] == "base" and cfg["ac"]["default"] is True
    orderable = {k: v for k, v in cfg.items() if v["kind"] == "orderable"}
    assert {k: set(v["part-numbers"]) for k, v in orderable.items()} == {
        "ac-ip-base": {"WS-C4948E-F-S"},
        "ac-ent-services": {"WS-C4948E-F-E"},
    }
    # Data sheet Table 5 sells "AC p/s" with the second supply as PWR-C49E-300AC-F/2, and
    # guide Table 1-1 covers an empty bay with the blank WS-X4994-F.
    for conf in orderable.values():
        assert conf["bays"] == {
            "psu-1": "cisco/pwr-c49e-300ac-f@1",
            "psu-2": "cisco/ws-x4994-f@1",
            "fan-tray": "cisco/ws-x4993-f@1",
        }
    # The base build keeps the bay defaults: two supplies.
    assert "bays" not in cfg["ac"]
    b = bays(d)
    assert b["psu-1"]["default"] == b["psu-2"]["default"] == "cisco/pwr-c49e-300ac-f@1"


def test_4948e_f_parts_state_back_to_front_airflow():
    for name in ("pwr-c49e-300ac-f", "ws-x4993-f"):
        assert component(name)["attrs"]["airflow"] == "back-to-front", name
    for name in ("pwr-c49e-300ac-r", "ws-x4993"):
        assert component(name)["attrs"]["airflow"] == "front-to-back", name


def test_4948e_f_parts_are_named_by_their_part_numbers():
    assert component("pwr-c49e-300ac-f")["attrs"]["model"] == "PWR-C49E-300AC-F"
    assert component("ws-x4993-f")["attrs"]["model"] == "WS-X4993-F"
    blank = component("ws-x4994-f")
    assert blank["attrs"]["model"] == "WS-X4994-F" and blank["class"] == "blank"


def test_4948e_f_ears_default_to_the_front_brackets_the_guide_installs_first():
    """Figure 3-1: brackets on the front sides, or on the rear sides; neither dimensioned."""
    ears = device("ws-c4948e-f")["chassis"]["ears"]
    names = {p["name"]: p for p in ears["positions"]}
    assert set(names) == {"flush", "rear"}
    assert names["flush"]["default"] is True
    assert all("at" not in p for p in ears["positions"])


def test_4948e_f_lists_no_kit_until_the_census_tests_take_one():
    """No kind: kit contract is in the library yet; the census tests walk contracts by `class`."""
    assert "kits" not in device("ws-c4948e-f")["chassis"]


def test_4948e_is_untouched():
    """The -F is its own device: the 4948E keeps its own airflow, configurations and bay accepts."""
    d = device("ws-c4948e")
    assert d["chassis"]["airflow"] == "front-to-back"
    assert bays(d)["psu-1"]["accepts"] == ["cisco/pwr-c49e-300ac-r@1"]
    for bay in bays(d).values():
        assert not any(ref.endswith("-f@1") for ref in bay["accepts"]), bay["id"]
    assert not any("4948E-F" in part for c in d["configurations"].values()
                   for part in c.get("part-numbers", {}))
    for c in d["configurations"].values():
        assert not any(ref.endswith("-f@1") for ref in c.get("bays", {}).values())


# --- the DCIM exports: one device type per orderable configuration ---------------------


@pytest.mark.parametrize("part", ["WS-C4948E-F-S", "WS-C4948E-F-E"])
def test_4948e_f_exports_one_device_type_per_orderable_part_number(part):
    path = EXPORTS / f"{part}.yaml"
    assert path.exists(), f"{path.name}: run dcim_export.py for ws-c4948e-f"
    doc = yaml.safe_load(path.read_text())
    assert doc["u_height"] == 1
    assert doc["model"] == part
    assert doc["airflow"] == "rear-to-front"
