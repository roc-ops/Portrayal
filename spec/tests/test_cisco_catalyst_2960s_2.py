"""The Cisco Catalyst 2960-S, second batch: the 48LPD-L, 48TD-L, 24PD-L and 24TD-L, each against its own row.

Read from the Catalyst 2960-S Switch Hardware Installation Guide (OL-19732-04): Table 1-1 for the models and
their port counts, the Front Panel note on port numbering (PDF p5), Figures 1-10 and 1-11 for the rear, and the
appendix's specification Tables 1-2 (PoE models) and 1-3 (non-PoE models; the appendix restarts its table
numbers). The 48FPD-L is covered by test_cisco_catalyst_2960s.py.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
DEVICES = LIBRARY / "devices/cisco"
EXPORTS = LIBRARY / "exports"

BLANK = "cisco/c2960s-flexstack-blank@1"

# name -> what that model's own row of Table 1-1 and spec Table 1-2 / 1-3 says.
SPEC = {
    "ws-c2960s-48lpd": dict(
        sku="WS-C2960S-48LPD-L", cfg="ws-c2960s-48lpd-l", rj45=48, depth=386.0, kg=5.66, poe=370,
        ac="5 to 2 A", rps="-52 V @8 A", watts=100, btu=341, kva=0.48),
    "ws-c2960s-48td": dict(
        sku="WS-C2960S-48TD-L", cfg="ws-c2960s-48td-l", rj45=48, depth=299.0, kg=4.30, poe=None,
        ac="1 to 0.5 A", rps="+12 V @4 A", watts=55, btu=188, kva=0.09),
    "ws-c2960s-24pd": dict(
        sku="WS-C2960S-24PD-L", cfg="ws-c2960s-24pd-l", rj45=24, depth=386.0, kg=5.66, poe=370,
        ac="5 to 2 A", rps="+12 V @3 A", watts=84, btu=286, kva=0.46),
    "ws-c2960s-24td": dict(
        sku="WS-C2960S-24TD-L", cfg="ws-c2960s-24td-l", rj45=24, depth=299.0, kg=4.30, poe=None,
        ac="1 to 0.5 A", rps="+12 V @3 A", watts=40, btu=136, kva=0.09),
}
NAMES = list(SPEC)


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return d["views"][view]["components"].get("placements") or []


def bays(d, view="rear"):
    return {b["id"]: b for b in d["views"][view]["components"].get("bays") or []}


def ports(d, group):
    return [p for p in placements(d, "front") if p.get("group") == group]


def by_id(d, view):
    return {p["id"]: p for p in placements(d, view)}


@pytest.mark.parametrize("name", NAMES)
def test_envelope_is_the_models_spec_table_dimensions(name):
    """H x D x W 1.75 x 15.19 x 17.5 in on every PoE model (Table 1-2); 1.75 x 11.77 x 17.50 in on the 48TD-L and 24TD-L (Table 1-3)."""
    s = SPEC[name]
    c = device(name)["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (444.5, 44.45, s["depth"], 1)
    assert c["weight-kg"] == s["kg"]
    assert c["power"] == "ac"


@pytest.mark.parametrize("name", NAMES)
def test_front_has_the_rj45_count_of_table_1_1_numbered_as_printed(name):
    """Table 1-1: 48 or 24 10/100/1000 ports; port 1 above port 2 (Front Panel note, PDF p5)."""
    s = SPEC[name]
    rj45 = ports(device(name), "rj45")
    assert [p["id"] for p in rj45] == [f"port-{n}" for n in range(1, s["rj45"] + 1)]
    assert {p["ref"] for p in rj45} == {"std/rj45-ganged@2"}
    assert rj45[0]["at"][0] == rj45[1]["at"][0] and rj45[0]["at"][1] < rj45[1]["at"][1]


@pytest.mark.parametrize("name", NAMES)
def test_front_has_two_sfp_plus_slots_after_the_copper_ports(name):
    """Table 1-1: two SFP+ module slots. The guide numbers them 49 and 50 on the 48-port models and says nothing for the 24-port ones."""
    s = SPEC[name]
    sfp = {p["id"]: p for p in ports(device(name), "sfp-plus")}
    assert set(sfp) == {f"port-{s['rj45'] + 1}", f"port-{s['rj45'] + 2}"}
    assert {p["ref"] for p in sfp.values()} == {"std/sfp@1"}


def test_the_24_port_slot_numbers_are_a_declared_gap():
    for name in ("ws-c2960s-24pd", "ws-c2960s-24td"):
        assert "sfp-slot-numbers" in {g["what"] for g in device(name).get("gaps", [])}


@pytest.mark.parametrize("name", NAMES)
def test_front_has_the_usb_and_console_ports_figure_1_1_names(name):
    """Figure 1-1 callouts 4 to 7: USB Type A, USB mini-Type B console, RJ-45 console, Ethernet management."""
    d = device(name)
    p = by_id(d, "front")
    assert p["usb-a"]["ref"] == "std/usb-a@1"
    assert p["console-usb"]["ref"] == "std/mini-usb@1"
    assert p["console-usb"]["attrs"]["role"] == "console"
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt"]["attrs"]["media"] == "rj45"
    assert "usb-console-jack" not in {g["what"] for g in d.get("gaps", [])}


@pytest.mark.parametrize("name", NAMES)
def test_front_lamps_are_figure_1_7s_and_the_poe_lamp_is_on_poe_models_only(name):
    """Figure 1-7: the PoE lamp is 'only on switch models that support PoE'."""
    lamps = {p["id"] for p in placements(device(name), "front") if p.get("group") in ("leds", "mode-leds")}
    base = {"led-system", "led-rps", "led-master", "led-stat", "led-duplx", "led-speed", "led-stack"}
    assert base <= lamps
    assert ("led-poe" in lamps) == (SPEC[name]["poe"] is not None)


@pytest.mark.parametrize("name", NAMES)
def test_rear_flexstack_slot_seats_the_blank_cover_by_default(name):
    """Figures 1-10 and 1-11: the slot has a cover, removed only to fit the module (PDF p31)."""
    b = bays(device(name))
    assert set(b) == {"flexstack-slot"}
    assert b["flexstack-slot"]["accepts"] == [BLANK]
    assert b["flexstack-slot"]["default"] == BLANK


@pytest.mark.parametrize("name", NAMES)
def test_power_is_built_in_with_a_chassis_inlet_and_no_supply_bay(name):
    d = device(name)
    assert not [b for b in bays(d) if b.startswith("psu")]
    assert by_id(d, "rear")["ac-inlet"]["ref"] == "std/c14-inlet@1"
    assert "fan-redundancy" not in d["attrs"].get("features", {})


@pytest.mark.parametrize("name", NAMES)
def test_rps_connector_is_chassis_art_with_a_gap(name):
    d = device(name)
    assert "rps-connector" in {x["id"] for x in d["views"]["rear"]["panel"]["decor"]}
    assert "rps-connector-part" in {g["what"] for g in d["gaps"]}


def test_the_td_rear_slot_conflict_is_a_declared_gap():
    """The serial-number figure for the TD models draws no cover; Table 1-1 footnote 1 says they support FlexStack."""
    for name in ("ws-c2960s-48td", "ws-c2960s-24td"):
        assert "flexstack-slot-on-the-td-rear" in {g["what"] for g in device(name)["gaps"]}
    for name in ("ws-c2960s-48lpd", "ws-c2960s-24pd"):
        assert "flexstack-slot-on-the-td-rear" not in {g["what"] for g in device(name)["gaps"]}


@pytest.mark.parametrize("name", NAMES)
def test_power_attrs_come_from_the_models_own_row(name):
    s = SPEC[name]
    a = device(name)["attrs"]["power"]
    assert a["power-input-ac"].startswith("100 to 240 VAC") and s["ac"] in a["power-input-ac"]
    assert s["rps"] in a["rps-input"].replace("@ ", "@")
    assert a["power-consumption-w"] == s["watts"]
    assert a["heat-dissipation-btu-hr"] == s["btu"]
    assert a["power-rating-kva"] == s["kva"]
    if s["poe"] is None:
        assert "poe-budget-w" not in a
    else:
        assert a["poe-budget-w"] == s["poe"]


@pytest.mark.parametrize("name", NAMES)
def test_weight_note_names_the_models_own_row(name):
    d = device(name)
    assert d["attrs"]["physical"]["weight-note"].endswith(f"row Catalyst {SPEC[name]['sku'][4:]}")


@pytest.mark.parametrize("name", NAMES)
def test_configurations_are_the_base_build_and_the_one_sku_seating_the_blank(name):
    s = SPEC[name]
    cfg = device(name)["configurations"]
    assert cfg["ac"]["kind"] == "base" and cfg["ac"]["default"] is True
    orderable = {k: v for k, v in cfg.items() if v["kind"] == "orderable"}
    assert {k: set(v["part-numbers"]) for k, v in orderable.items()} == {s["cfg"]: {s["sku"]}}
    assert orderable[s["cfg"]]["bays"] == {"flexstack-slot": BLANK}
    assert device(name)["model"] == s["sku"]


@pytest.mark.parametrize("name", NAMES)
def test_ears_default_to_the_front_mounting_position_and_no_kit_is_listed(name):
    """Figures 1-12 and 1-13: front, mid and rear positions, none dimensioned; the ETSI bracket is a gap."""
    d = device(name)
    names = {p["name"]: p for p in d["chassis"]["ears"]["positions"]}
    assert set(names) == {"flush", "mid", "rear"}
    assert names["flush"]["default"] is True
    assert all("at" not in p for p in names.values())
    assert "kits" not in d["chassis"]
    assert "etsi-bracket" in {g["what"] for g in d["gaps"]}


@pytest.mark.parametrize("name", NAMES)
def test_unmeasurable_faces_are_empty(name):
    d = device(name)
    for face in ("top", "bottom", "left", "right"):
        assert d["views"][face].get("empty"), face


@pytest.mark.parametrize("name", NAMES)
def test_exports_carry_one_device_type_per_orderable_sku(name):
    s = SPEC[name]
    for tool in ("netbox", "nautobot"):
        path = EXPORTS / tool / "device-types/Cisco" / f"{s['sku']}.yaml"
        assert path.exists(), f"{path}: run dcim_export.py for {name}"
        doc = yaml.safe_load(path.read_text())
        assert doc["u_height"] == 1
        assert doc["model"] == s["sku"]


def test_the_lock_files_agree_with_the_devices():
    mine = [f for f in devicelock.check(LIBRARY) if f[0] in {f"cisco/{n}" for n in NAMES}]
    assert mine == []
