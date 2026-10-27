"""The first Ubiquiti devices: the USW-Pro-24-PoE and the UDM-Pro (#1269).

The maker's own data sheets state the envelope, the port counts and the weights; the faceplate
photographs and the community elevations give the order and the arrangement. These tests hold the
parts the sheets state, so a later edit cannot drift from them, and the DCIM export of each device.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

DEVICES = {
    "usw-pro-24-poe": {
        "part": "USW-Pro-24-PoE",
        # Mechanical, "442.4 x 285.4 x 43.7 mm": width, depth, height
        "width": 442.4, "depth": 285.4, "height": 43.7,
        "rj45": 24, "sfp": [25, 26],
    },
    "udm-pro": {
        "part": "UDM-Pro",
        # Mechanical, "442.4 x 43.7 x 285.6 mm": width, height, depth
        "width": 442.4, "depth": 285.6, "height": 43.7,
        "rj45": 9, "sfp": [10, 11],
    },
}


def load(name):
    return yaml.safe_load((LIB / "devices/ubiquiti" / name / "device.yaml").read_text())


def placements(d, view):
    comps = d["views"][view].get("components") or {}
    return list(comps.get("placements") or [])


def ports(d, view, ref_part):
    return [p for p in placements(d, view) if ref_part in p["ref"]]


def test_ubiquiti_resolves_in_the_vendor_registry():
    reg = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert reg["ubiquiti"]["display"] == "Ubiquiti"
    assert reg["ubiquiti"]["role"] == "hardware"
    assert str(reg["ubiquiti"]["source"]).strip()
    # the entry sits directly after ufispace, apart from the MikroTik pilot's (after cisco)
    keys = list(reg)
    assert keys.index("ubiquiti") == keys.index("ufispace") + 1


@pytest.mark.parametrize("name", DEVICES)
def test_envelope_matches_the_data_sheet(name):
    want = DEVICES[name]
    d = load(name)
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == (want["width"], want["height"], want["depth"])
    assert c["ru"] == 1
    assert (c.get("mount") or "rack") == "rack"
    assert d["manufacturer"] == "Ubiquiti"


@pytest.mark.parametrize("name", DEVICES)
def test_front_ports_per_sheet(name):
    want = DEVICES[name]
    d = load(name)
    jacks = [p for p in placements(d, "front") if "rj45" in p["ref"]]
    assert len(jacks) == want["rj45"]
    assert sorted(int(p["id"].split("-")[1]) for p in jacks) == list(range(1, want["rj45"] + 1))
    cages = [p for p in placements(d, "front") if p["ref"].startswith("std/sfp-ganged")]
    assert sorted(int(p["id"].split("-")[1]) for p in cages) == want["sfp"]
    # the ports are all on the front: the rear carries no data port
    assert not [p for p in placements(d, "rear") if "rj45" in p["ref"] or "sfp" in p["ref"]]


def test_switch_upper_row_takes_the_odd_numbers():
    d = load("usw-pro-24-poe")
    y = {p["id"]: p["at"][1] for p in placements(d, "front") if "rj45" in p["ref"]}
    for n in range(1, 25, 2):
        assert y[f"port-{n}"] < y[f"port-{n + 1}"]


def test_the_gateway_numbers_its_wan_and_lan_ports():
    d = load("udm-pro")
    roles = {p["id"]: (p.get("attrs") or {}).get("role") for p in placements(d, "front")}
    for n in (9, 10):
        assert roles[f"port-{n}"] == "wan"
    assert roles["port-11"] == "lan"


@pytest.mark.parametrize("name", DEVICES)
def test_one_touchscreen_component_on_both_faces_of_the_line(name):
    d = load(name)
    screens = [p for p in placements(d, "front") if p["ref"] == "ubiquiti/lcm-touchscreen-1-3@1"]
    assert len(screens) == 1


@pytest.mark.parametrize("name", DEVICES)
def test_power_and_fans_are_chassis_not_bays(name):
    d = load(name)
    for v in ("front", "rear"):
        comps = d["views"][v].get("components") or {}
        assert not comps.get("bays"), f"{name} {v}: the supply and fans are built in"
    assert d["chassis"].get("power") == "ac"


@pytest.mark.parametrize("name", DEVICES)
def test_logo_is_reserved_not_drawn(name):
    d = load(name)
    rear = d["views"]["rear"]
    assert any(r["id"] == "logo-zone" for r in rear["regions"])
    for v in d["views"].values():
        for s in v.get("silkscreen") or []:
            text = str(s.get("text") or "").lower()
            assert "ubiquiti" not in text and "unifi" not in text


@pytest.mark.parametrize("name", DEVICES)
def test_ears_state_no_position_without_a_figure(name):
    d = load(name)
    ears = (d["chassis"].get("ears") or {})
    for pos in ears.get("positions") or []:
        assert "at" not in pos
    assert not [p for v in ("front", "rear") for p in placements(d, v)
                if p["ref"].startswith("common/rack-ear")]
    assert any(g["what"] == "rack-ears" for g in d["gaps"])


@pytest.mark.parametrize("name", DEVICES)
def test_each_configuration_names_the_sheet_part_number(name):
    d = load(name)
    pns = [pn for c in d["configurations"].values() for pn in c["part-numbers"]]
    assert pns == [DEVICES[name]["part"]]


@pytest.mark.parametrize("name", DEVICES)
def test_dcim_device_type_is_one_u_per_configuration(name):
    part = DEVICES[name]["part"]
    for tool in ("netbox", "nautobot"):
        f = LIB / "exports" / tool / "device-types" / "Ubiquiti" / f"{part}.yaml"
        assert f.exists(), f"{f} missing: run dcim_export.py for {name}"
        t = yaml.safe_load(f.read_text())
        assert t["u_height"] == 1
        assert t["manufacturer"] == "Ubiquiti"
        assert t["model"] == part
