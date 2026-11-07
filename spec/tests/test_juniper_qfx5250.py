"""The Juniper QFX5250-64OE-L, from its hardware guide.

Source: QFX5250 Switch Hardware Guide, published 2026-06-17 (140 pages).

The guide describes one model, the liquid-cooled QFX5250-64OE-L for an Open Rack v3 rack, so there is one
device and one configuration. It is powered from the rack busbar and cooled through two quick-disconnect plugs:
the guide gives it no power supply, no fan module and no field-replaceable unit (Table 9, "QFX5250
Field-Replaceable Units"), so no face has a bay.

What the guide fixes, and so what these tests hold:
  Table 4          the envelope - 3.649 x 21 x 31.71 in, 48.00 kg
  Table 2          2 OU, 64 OSFP and 2 SFP28 ports, one Type-A USB, one RJ-45 console, one management port, two
                   DIN timing connectors
  Table 7, fig 10  the front panel; ports numbered 0 to 63, then 64 and 65 on the SFP28 pair
  Table 8, fig 11  the rear: coolant outlet, IT gear input connector, coolant inlet
  Tables 9, 10     no power supply and no fan; one hardware configuration
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/juniper/qfx5250-64oe-l/device.yaml"
EXPORTS = ROOT / "library/exports"

INCH = 25.4
PART = "QFX5250-64OE-L"


@pytest.fixture(scope="module")
def dev():
    return yaml.safe_load(DEVICE.read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def ref_name(p):
    return p["ref"].split("/")[-1].split("@")[0]


def by_id(dev, view):
    return {p["id"]: p for p in placements(dev, view)}


# --- the envelope ------------------------------------------------------------

def test_the_envelope_is_the_guides_table(dev):
    ch = dev["chassis"]
    assert ch["ru"] == 2
    assert ch["height"] == pytest.approx(3.649 * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(21 * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(31.71 * INCH, abs=0.1)
    assert ch["weight-kg"] == 48.0


def test_the_faces_are_the_chassis_size(dev):
    ch = dev["chassis"]
    for view in ("front", "rear"):
        size = dev["views"][view]["size"]
        assert (size["w"], size["h"]) == (ch["width"], ch["height"])


def test_the_identity_is_the_guides(dev):
    assert dev["manufacturer"] == "Juniper"
    assert dev["model"] == PART
    assert dev["portfolio"]["family"] == "QFX5250"


# --- the front panel ---------------------------------------------------------

def test_the_front_has_64_osfp_ports_numbered_0_to_63(dev):
    osfp = [p for p in placements(dev, "front") if ref_name(p) == "osfp"]
    assert sorted(int(p["id"].split("-")[1]) for p in osfp) == list(range(64))
    assert {p["group"] for p in osfp} == {"osfp"}
    assert dev["groups"]["osfp"]["attrs"] == {"media": "osfp", "speed": "1.6t"}


def test_the_osfp_ports_run_down_each_column_of_four(dev):
    """Printed "n up-arrow, down-arrow n+1" between rows one and two: column c holds 4c to 4c+3 from the top."""
    ports = by_id(dev, "front")
    for c in range(16):
        col = [ports[f"port-{4 * c + r}"] for r in range(4)]
        assert len({p["at"][0] for p in col}) == 1, f"column {c} is not a column"
        ys = [p["at"][1] for p in col]
        assert ys == sorted(ys), f"column {c} does not run top to bottom"
    # two banks of eight columns, 23.1 mm apart, a gap between them
    xs = sorted({p["at"][0] for p in ports.values() if ref_name(p) == "osfp"})
    assert len(xs) == 16
    steps = [round(b - a, 1) for a, b in zip(xs, xs[1:])]
    assert steps.count(23.1) == 14
    assert max(steps) > 40


def test_the_printed_numbers_match_the_ports(dev):
    legends = {m["for"]: m["text"] for m in dev["views"]["front"]["silkscreen"] if m.get("for", "").startswith("port-")}
    for n in range(64):
        assert str(n) in legends[f"port-{n}"], n
    assert "64" in legends["port-64"] and "65" in legends["port-65"]


def test_each_osfp_port_has_one_numbered_lamp(dev):
    lamps = [p for p in placements(dev, "front") if p["id"].startswith("led-port-")]
    assert sorted(int(p["id"].rsplit("-", 1)[1]) for p in lamps) == list(range(64))
    for p in lamps:
        assert p["for"] == f"port-{p['id'].rsplit('-', 1)[1]}"


def test_the_two_sfp28_ports_are_numbered_64_and_65(dev):
    ports = by_id(dev, "front")
    sfp = [p for p in placements(dev, "front") if ref_name(p) == "sfp"]
    assert sorted(p["id"] for p in sfp) == ["port-64", "port-65"]
    assert ports["port-64"]["at"][1] < ports["port-65"]["at"][1]
    assert dev["groups"]["sfp28"]["attrs"]["media"] == "sfp28"


def test_the_management_ports_are_the_guides_list(dev):
    refs = [(p["id"], ref_name(p)) for p in placements(dev, "front")
            if not p["id"].startswith(("port-", "led-port-"))]
    ids = dict(refs)
    assert ids["console"] == "rj45"
    assert ids["mgmt"] == "rj45-eth"
    assert ids["usb"] == "usb-a"
    assert ids["clk-10mhz"] == "din-1-0-2-3-jack" and ids["clk-1pps"] == "din-1-0-2-3-jack"
    assert ids["power-btn"] == "reset-button" and ids["reset"] == "reset-button"
    assert {"led-leakage", "led-id", "led-sys", "led-alm"} <= set(ids)


def test_the_front_reserves_the_logo_and_draws_no_logo(dev):
    regions = {r["id"] for r in dev["views"]["front"].get("regions") or []}
    assert "logo-zone" in regions
    texts = {m.get("text", "").upper() for m in dev["views"]["front"]["silkscreen"]}
    assert not any("JUNIPER" in t or "NETWORKS" in t for t in texts)
    assert PART in texts


# --- the rear ----------------------------------------------------------------

def test_the_rear_is_two_coolant_plugs_and_the_busbar_connector(dev):
    rear = by_id(dev, "rear")
    assert sorted(rear) == ["busbar", "qd-inlet", "qd-outlet"]
    assert ref_name(rear["qd-outlet"]) == "liquid-qd-coupler"
    assert ref_name(rear["qd-inlet"]) == "liquid-qd-coupler"
    assert ref_name(rear["busbar"]) == "orv3-busbar-connector"
    # seen from the rear the outlet (hot) plug is at the left end, the inlet (cold) at the right
    assert rear["qd-outlet"]["at"][0] < rear["busbar"]["at"][0] < rear["qd-inlet"]["at"][0]
    legends = {m["text"] for m in dev["views"]["rear"]["silkscreen"] if "text" in m}
    assert {"Outlet (Hot)", "Inlet (Cold)"} <= legends


# --- nothing seats: no power supply, no fan module, no module bay -------------

@pytest.mark.parametrize("view", ["front", "rear", "top", "bottom", "left", "right"])
def test_no_face_has_a_bay(dev, view):
    assert bays(dev, view) == []


def test_the_chassis_names_no_airflow_and_is_dc_powered(dev):
    ch = dev["chassis"]
    assert "airflow" not in ch
    assert ch["power"] == "dc"
    power = dev["attrs"]["power"]
    assert power["power-max-w"] == 3435 and power["power-typical-w"] == 3375


# --- the one configuration ---------------------------------------------------

def test_there_is_one_orderable_configuration_with_the_guides_part_number(dev):
    configs = dev["configurations"]
    assert len(configs) == 1
    (cid, cfg), = configs.items()
    assert cfg["kind"] == "orderable" and cfg.get("default") is True
    assert list(cfg["part-numbers"]) == [PART]
    assert "bays" not in cfg


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_device_type_is_exported_with_the_guides_height(target):
    path = EXPORTS / target / "device-types/Juniper" / f"{PART}.yaml"
    assert path.exists(), path
    doc = yaml.safe_load(path.read_text())
    assert doc["manufacturer"] == "Juniper"
    assert doc["model"] == PART
    assert doc["u_height"] == 2
    assert doc["weight"] == 48.0


def test_no_module_type_is_exported_for_a_box_with_no_modules():
    """Nothing seats, so the family exports one device type and no module type."""
    for target in ("netbox", "nautobot"):
        base = EXPORTS / target / "module-types/Juniper"
        assert not list(base.glob("QFX5250*")), target
