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


# ---- the owner's six fixes -------------------------------------------------------------------

SLOT_X = {
    ("usw-pro-24-poe", "front"): [36.7, 113.7, 191.2, 268.2, 345.3],
    ("usw-pro-24-poe", "rear"): [18.0, 97.1, 176.1, 255.1, 334.3],
    ("udm-pro", "front"): [37.7, 114.9, 191.9, 269.0, 346.2],
    ("udm-pro", "rear"): [18.4, 97.2, 177.6, 257.5, 333.2],
}


@pytest.mark.parametrize("name,view", list(SLOT_X))
def test_vent_slots_are_plain_bars_not_a_pattern(name, view):
    # `pattern: vent` is a perforated field drawn at a 1.0 mm pitch: in a strip under 2 mm high it
    # shows as a zig-zag or a broken chain. A slot is a plain dark bar that declares `vent`.
    decor = load(name)["views"][view]["panel"]["decor"]
    slots = [r for r in decor if "vent" in r]
    assert [r["at"][0] for r in slots] == SLOT_X[(name, view)]
    for r in slots:
        assert "pattern" not in r, f"{name} {view}: slot at {r['at']} is a pattern fill"
        assert r["vent"] == 1.0 and r["size"][1] < 2.0 and r.get("fill")


def _skin(comp):
    import xml.etree.ElementTree as ET
    return ET.parse(LIB / "components/ubiquiti" / comp / "v1/skins/default.svg").getroot()


def _contract(comp):
    return yaml.safe_load((LIB / "components/ubiquiti" / comp / "v1/contract.yaml").read_text())


@pytest.mark.parametrize("comp,outer", [("lcm-touchscreen-1-3", "bezel"), ("usp-rps-input", "opening")])
def test_component_sides_close_flush(comp, outer):
    # the 3D body is a box of the skin's size; a rounded or stroked outermost rect leaves the box's
    # corners and top and right edges standing clear of the drawing as a thin strip
    root = _skin(comp)
    vb = [float(v) for v in root.get("viewBox").split()]
    ns = "{http://www.w3.org/2000/svg}"
    rect = next(e for e in root.iter(ns + "rect") if e.get("id") == outer)
    assert (float(rect.get("x")), float(rect.get("y"))) == (0.0, 0.0)
    assert (float(rect.get("width")), float(rect.get("height"))) == (vb[2], vb[3])
    assert not rect.get("rx") and not rect.get("ry") and not rect.get("stroke")


def test_component_versions_carry_the_fixes():
    assert _contract("lcm-touchscreen-1-3")["version"] == "1.1.0"
    assert _contract("usp-rps-input")["version"] == "1.1.0"


def test_touchscreen_is_a_plain_lit_field():
    root = _skin("lcm-touchscreen-1-3")
    ns = "{http://www.w3.org/2000/svg}"
    tags = {e.tag.replace(ns, "") for e in root.iter()}
    assert tags <= {"svg", "rect", "defs", "linearGradient", "radialGradient", "stop"}, tags
    screen = next(e for e in root.iter(ns + "rect") if e.get("id") == "screen")
    assert screen.get("fill", "").startswith("url(#")


@pytest.mark.parametrize("name,legend", [("usw-pro-24-poe", "USW Pro"), ("udm-pro", "Dream Machine Pro")])
def test_legend_under_the_screen(name, legend):
    texts = [s["text"] for s in load(name)["views"]["front"]["silkscreen"] if s.get("for") == "lcm"]
    assert texts == [legend]
    assert any(r["id"] == "logo-zone" for r in load(name)["views"]["rear"]["regions"])


def test_switch_rps_lamp_has_a_blue_lit_state():
    d = load("usw-pro-24-poe")
    lamp = next(p for p in placements(d, "rear") if p["id"] == "rps-led")
    assert lamp["states"][0] == "off"
    assert [s["color"] for s in lamp["states"][1:]] == ["#3b82f6"]


def test_wan_jack_carries_its_lamp_and_its_mark_like_the_others():
    d = load("udm-pro")
    jacks = {p["id"]: p for p in placements(d, "front") if "rj45" in p["ref"]}
    for i in range(1, 9):
        assert jacks["port-9"]["states"] == jacks[f"port-{i}"]["states"]
    # the blue circle printed beside the numeral 9 (the photograph and the elevation both show it)
    num = next(s for s in d["views"]["front"]["silkscreen"] if s.get("for") == "port-9")
    marks = [r for r in d["views"]["front"]["panel"]["decor"] if r.get("id") == "wan-mark"]
    assert len(marks) == 1
    cx = marks[0]["at"][0] + marks[0]["size"][0] / 2
    assert 1.5 < cx - num["at"][0] < 4.0
    assert marks[0]["fill"].lower() not in ("#000000", "#17191c")


def test_both_chassis_are_one_grey():
    assert load("usw-pro-24-poe")["chassis"]["color"] == load("udm-pro")["chassis"]["color"] == "#c8cacc"
