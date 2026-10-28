"""The Cisco Catalyst 3650 batch: the 48PD and the parts only the 3650 takes.

Figures are the Cisco Catalyst 3650 Switches Hardware Installation Guide (OL-29734-01): spec
Table 1-1 for the envelope, Table 1-1 of chapter 1 for the ports and the shipped supply, Tables
1-13 to 1-15 for the supply builds, Table 4-1 for the part numbers.
"""
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = ["ws-c3650-48pd"]
IN = 25.4

PSUS = ["cisco/pwr-c2-250wac@1", "cisco/pwr-c2-640wac@1", "cisco/pwr-c2-1025wac@1",
        "cisco/pwr-c2-640wdc@1", "cisco/pwr-c2-blank@1"]


def load(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def placements(d, view):
    c = d["views"][view]["components"]
    return {p["id"]: p for p in c.get("placements", [])}


def bays(d, view):
    return {b["id"]: b for b in d["views"][view]["components"]["bays"]}


@pytest.mark.parametrize("name", DEVICES)
def test_envelope_is_spec_table_1_1_for_48_port_poe_plus(name):
    ch = load(name)["chassis"]
    assert ch["width"] == pytest.approx(17.5 * IN)
    assert ch["depth"] == pytest.approx(17.625 * IN, abs=0.1)
    assert ch["height"] == pytest.approx(44.45)
    assert ch["ru"] == 1
    assert ch["weight-kg"] == 7.6


@pytest.mark.parametrize("name", DEVICES)
def test_a_new_device_is_at_1_0_0(name):
    assert load(name)["version"] == "1.0.0"


def test_48pd_has_48_rj45_numbered_1_to_48_odd_on_top():
    d = load("ws-c3650-48pd")
    p = placements(d, "front")
    ports = [p[f"port-{n}"] for n in range(1, 49)]
    assert all(x["ref"] == "std/rj45-ganged@2" for x in ports)
    assert all(x["group"] == "rj45" for x in ports)
    assert sum(1 for k in p if k.startswith("port-")) == 48
    for n in (1, 3, 47):
        assert p[f"port-{n}"]["at"][1] < p[f"port-{n + 1}"]["at"][1]


def test_48pd_uplinks_are_two_sfp_and_two_sfp_plus_cages():
    d = load("ws-c3650-48pd")
    p = placements(d, "front")
    up = [p[f"uplink-{n}"] for n in range(1, 5)]
    assert all(x["ref"] == "std/sfp-ganged@1" for x in up)
    assert [x["group"] for x in up] == ["sfp", "sfp", "sfp-plus", "sfp-plus"]
    assert d["groups"]["sfp"]["attrs"] == {"media": "sfp", "speed": "1g"}
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}


def test_48pd_front_has_usb_a_and_the_mini_b_stays_a_gap_while_no_jack_is_on_main():
    d = load("ws-c3650-48pd")
    assert placements(d, "front")["usb-a"]["ref"] == "std/usb-a@1"
    mini_b = [c for c in (LIB / "components").rglob("contract.yaml")
              if "conforms: mini-usb-b" in c.read_text()]
    gaps = {g["what"] for g in d["gaps"]}
    if mini_b:
        pytest.fail("a mini-B jack is now a library part: place it and drop the gap")
    assert "usb-console-jack" in gaps
    assert "rack-kit" in gaps


def test_48pd_rear_has_console_and_management_jacks():
    p = placements(load("ws-c3650-48pd"), "rear")
    assert p["console"]["attrs"]["role"] == "console"
    assert p["mgmt"]["attrs"]["role"] == "mgmt"


def test_the_supply_bays_accept_exactly_the_four_supplies_and_the_blank():
    b = bays(load("ws-c3650-48pd"), "rear")
    for bay in ("psu-1", "psu-2"):
        assert sorted(b[bay]["accepts"]) == sorted(PSUS)
    assert b["psu-1"]["default"] == "cisco/pwr-c2-640wac@1"
    assert b["psu-2"]["default"] == "cisco/pwr-c2-blank@1"


def test_three_fan_bays_each_accept_only_fan_t1_and_two_stackwise_bays_the_blank():
    b = bays(load("ws-c3650-48pd"), "rear")
    for n in (1, 2, 3):
        assert b[f"fan-{n}"]["accepts"] == ["cisco/fan-t1@1"]
        assert b[f"fan-{n}"]["default"] == "cisco/fan-t1@1"
    for n in (1, 2):
        assert b[f"stack-{n}"]["accepts"] == ["cisco/c3650-stackwise-blank@1"]


def test_the_base_build_is_the_shipped_one_and_carries_no_part_number():
    cfg = load("ws-c3650-48pd")["configurations"]
    assert cfg["ac"]["kind"] == "base" and cfg["ac"]["default"] is True
    for c in cfg.values():
        assert "part-numbers" not in c
        assert c["kind"] in ("base", "example")


def test_ears_default_is_the_front_mounting_position_and_no_ear_is_placed():
    d = load("ws-c3650-48pd")
    pos = d["chassis"]["ears"]["positions"]
    assert [x["name"] for x in pos if x.get("default")] == ["flush"]
    assert all("at" not in x for x in pos)
    for view in ("front", "rear"):
        assert "common/rack-ear@1" not in json.dumps(d["views"][view])


@pytest.mark.parametrize("part,watts,depth_in", [
    ("pwr-c2-250wac", 250, 11.75), ("pwr-c2-640wac", 640, 11.75),
    ("pwr-c2-1025wac", 1025, 13.25), ("pwr-c2-640wdc", 640, 11.75)])
def test_supply_contracts_match_spec_tables_1_2_and_1_3(part, watts, depth_in):
    c = yaml.safe_load((LIB / f"components/cisco/{part}/v1/contract.yaml").read_text())
    assert c["attrs"]["power-output-w"] == watts
    assert c["attrs"]["model"] == part.upper()
    assert c["size"]["w"] == pytest.approx(3.75 * IN, abs=0.01)
    assert c["size"]["h"] == pytest.approx(1.58 * IN, abs=0.01)
    assert c["body"]["depth"] == pytest.approx(depth_in * IN, abs=0.1)


def test_the_blank_and_the_stackwise_blank_have_no_invented_part_number():
    for part in ("pwr-c2-blank", "c3650-stackwise-blank"):
        c = yaml.safe_load((LIB / f"components/cisco/{part}/v1/contract.yaml").read_text())
        assert c["class"] == "blank" and "part-numbers" not in c
    sw = yaml.safe_load((LIB / "components/cisco/c3650-stackwise-blank/v1/contract.yaml").read_text())
    assert sw["attrs"]["weight-kg"] == 0.05


def test_fan_t1_face_is_the_width_that_fits_three_fans_and_two_supplies():
    c = yaml.safe_load((LIB / "components/cisco/fan-t1/v1/contract.yaml").read_text())
    assert c["size"]["w"] == pytest.approx(1.73 * IN, abs=0.01)
    assert c["size"]["h"] == pytest.approx(1.62 * IN, abs=0.01)
    assert c["body"]["depth"] == pytest.approx(4.24 * IN, abs=0.1)
    assert 3 * c["size"]["w"] + 2 * 95.25 < 444.5


@pytest.mark.parametrize("name", DEVICES)
def test_the_lock_agrees_with_the_device(name):
    from portrayal import devicelock
    findings = devicelock.check(LIB)
    assert not [f for f in findings if name in str(f)]


@pytest.mark.parametrize("name", DEVICES)
def test_dcim_exports_exist_for_the_device_with_u_height_1(name):
    found = []
    for tool in ("netbox", "nautobot"):
        for f in (LIB / "exports" / tool).rglob(f"{name.upper()}*"):
            if f.suffix in (".yaml", ".yml", ".json"):
                found.append(f)
    assert found, f"no DCIM export for {name}"
    for f in found:
        doc = yaml.safe_load(f.read_text())
        if isinstance(doc, dict) and "u_height" in doc:
            assert doc["u_height"] == 1
