"""The Cisco Catalyst 2960-S family: what each model's own guide states, held in the library.

Read from the Catalyst 2960-S Switch Hardware Installation Guide (OL-19732-04): Table 1-1 for the
models, the front and rear figures of chapter 1, and the appendix's specification tables 1-2 and 1-3
(the appendix restarts its table numbers). Each device is checked against the row of its own model.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
COMPONENTS = ROOT / "library/components/cisco"
EXPORTS = ROOT / "library/exports"

BLANK = "cisco/c2960s-flexstack-blank@1"


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def component(name):
    return yaml.safe_load((COMPONENTS / name / "v1" / "contract.yaml").read_text())


def placements(d, view):
    return d["views"][view]["components"].get("placements") or []


def bays(d, view="rear"):
    return {b["id"]: b for b in d["views"][view]["components"].get("bays") or []}


def ports(d, group):
    return [p for p in placements(d, "front") if p.get("group") == group]


def by_id(d, view):
    return {p["id"]: p for p in placements(d, view)}


# --- the WS-C2960S-48FPD-L: Table 1-1, Figure 1-1, spec Table 1-2 ----------------------


def test_48fpd_envelope_is_spec_table_1_2():
    """H x D x W 1.75 x 15.19 x 17.5 in (4.45 x 38.6 x 44.5 cm), applies to all PoE switches."""
    c = device("ws-c2960s-48fpd")["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (444.5, 44.45, 386.0, 1)
    assert c["weight-kg"] == 5.89  # 13 lb (5.89 kg), the 48FPD-L's own row
    assert c["power"] == "ac"


def test_48fpd_front_has_forty_eight_rj45_numbered_as_printed_and_two_sfp_plus():
    """Table 1-1: 48 10/100/1000 PoE+ ports and 2 SFP+ module slots, numbered 49 and 50 (PDF p5 note)."""
    d = device("ws-c2960s-48fpd")
    rj45 = ports(d, "rj45")
    assert [p["id"] for p in rj45] == [f"port-{n}" for n in range(1, 49)]
    assert {p["ref"] for p in rj45} == {"std/rj45-ganged@2"}
    sfp = {p["id"]: p for p in ports(d, "sfp-plus")}
    assert set(sfp) == {"port-49", "port-50"}
    assert {p["ref"] for p in sfp.values()} == {"std/sfp@1"}
    # "The first member of the pair (port 1) is above the second member (port 2)."
    assert rj45[0]["at"][0] == rj45[1]["at"][0] and rj45[0]["at"][1] < rj45[1]["at"][1]


def test_48fpd_front_has_the_usb_and_console_ports_the_figure_names():
    """Figure 1-1 callouts 4 to 7: USB Type A, USB mini-Type B console, RJ-45 console, Ethernet management."""
    d = device("ws-c2960s-48fpd")
    p = by_id(d, "front")
    assert p["usb-a"]["ref"] == "std/usb-a@1"
    assert p["console-usb"]["ref"] == "std/mini-usb@1"
    assert p["console-usb"]["attrs"]["role"] == "console"
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt"]["attrs"]["media"] == "rj45"
    assert not any(g["what"] == "usb-console-jack" for g in d.get("gaps", []))


def test_48fpd_front_lamps_are_the_guides_switch_leds():
    """Figure 1-7: System, RPS, Master, Status, Duplex, Speed, Stack and PoE lamps."""
    d = device("ws-c2960s-48fpd")
    lamps = {p["id"] for p in placements(d, "front") if p.get("group") in ("leds", "mode-leds")}
    assert {"led-system", "led-rps", "led-master", "led-stat", "led-duplx", "led-speed",
            "led-stack", "led-poe"} <= lamps


def test_48fpd_rear_has_the_flexstack_slot_seating_its_blank_by_default():
    """Figures 1-10/1-11: the slot has a cover, removed only to fit the module (PDF p31)."""
    d = device("ws-c2960s-48fpd")
    b = bays(d)
    assert set(b) == {"flexstack-slot"}
    assert b["flexstack-slot"]["accepts"] == [BLANK]
    assert b["flexstack-slot"]["default"] == BLANK


def test_the_flexstack_blank_has_no_invented_part_number():
    c = component("c2960s-flexstack-blank")
    assert "part-numbers" not in c
    assert c["class"] == "blank"
    assert c["attrs"]["model"] == "FlexStack slot blank cover"


def test_48fpd_power_is_built_in_with_a_chassis_inlet_and_no_supply_bay():
    d = device("ws-c2960s-48fpd")
    assert not [b for b in bays(d) if b.startswith("psu")]
    inlet = by_id(d, "rear")["ac-inlet"]
    assert inlet["ref"] == "std/c14-inlet@1"


def test_48fpd_rps_connector_is_chassis_art_with_a_gap():
    d = device("ws-c2960s-48fpd")
    ids = {x["id"] for x in d["views"]["rear"]["panel"]["decor"]}
    assert "rps-connector" in ids
    assert "rps-connector-part" in {g["what"] for g in d["gaps"]}


def test_48fpd_attrs_come_from_its_own_row_of_spec_table_1_2():
    a = device("ws-c2960s-48fpd")["attrs"]["power"]
    assert a["power-input-ac"].startswith("100 to 240 VAC") and "9 to 4 A" in a["power-input-ac"]
    assert "-52 V" in a["rps-input"].replace("–", "-") and "15 A" in a["rps-input"]
    assert a["power-consumption-w"] == 129
    assert a["heat-dissipation-btu-hr"] == 440
    assert a["poe-budget-w"] == 740


def test_48fpd_configurations_carry_the_one_sku_and_seat_the_blank():
    d = device("ws-c2960s-48fpd")
    cfg = d["configurations"]
    assert cfg["ac"]["kind"] == "base" and cfg["ac"]["default"] is True
    orderable = {k: v for k, v in cfg.items() if v["kind"] == "orderable"}
    assert {k: set(v["part-numbers"]) for k, v in orderable.items()} == {"ws-c2960s-48fpd-l": {"WS-C2960S-48FPD-L"}}
    assert orderable["ws-c2960s-48fpd-l"]["bays"] == {"flexstack-slot": BLANK}


def test_48fpd_ears_default_to_the_front_mounting_position():
    """Figures 1-12 and 1-13: front, mid and rear positions; none dimensioned."""
    ears = device("ws-c2960s-48fpd")["chassis"]["ears"]
    names = {p["name"]: p for p in ears["positions"]}
    assert set(names) == {"flush", "mid", "rear"}
    assert names["flush"]["default"] is True
    assert all("at" not in p for p in ears["positions"])


def test_48fpd_lists_no_kit_and_opens_an_etsi_bracket_gap():
    d = device("ws-c2960s-48fpd")
    assert "kits" not in d["chassis"]
    assert "etsi-bracket" in {g["what"] for g in d["gaps"]}


def test_48fpd_unmeasurable_faces_are_empty():
    d = device("ws-c2960s-48fpd")
    for face in ("top", "bottom", "left", "right"):
        assert d["views"][face].get("empty"), face


def test_48fpd_exports_one_device_type_per_orderable_part_number():
    for tool, sub in (("netbox", "device-types/Cisco"), ("nautobot", "device-types/Cisco")):
        path = EXPORTS / tool / sub / "WS-C2960S-48FPD-L.yaml"
        assert path.exists(), f"{path}: run dcim_export.py for ws-c2960s-48fpd"
        doc = yaml.safe_load(path.read_text())
        assert doc["u_height"] == 1
        assert doc["model"] == "WS-C2960S-48FPD-L"
