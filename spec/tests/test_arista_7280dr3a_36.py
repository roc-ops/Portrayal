"""The Arista 7280DR3A-36, a 2RU fixed switch with 36 x 400G QSFP-DD ports (#1204, slice 1).

One device, `arista/7280dr3a-36`. The DR3AM-36, DR3AK-36 and DR3AK-36S share its front panel
(guide figure C-2), size and weight (Table 1) and power draw (Table 4), so they are
`kind: orderable` configurations of it. The expected figures are Arista's: the 7280R3A Series
Quick Start Guide (DOC-07042-01, Table 1 for the envelope, Table 3 and 4 for the supplies,
Appendix C and D for the faces) and the 7280R3A Series Data Sheet (04-0040-26, 15 April 2025:
the DR3A-36 comparison table and its ordering information). Each test reads the YAML a
contributor edits, or the generated export a DCIM user imports.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = "7280dr3a-36"
AC = "arista/7280dr3a-pwr-2400-ac@1"
DC = "arista/7280dr3a-pwr-2400-dc@1"
FAN = "arista/7280dr3a-fan@1"

# configuration -> the part number it orders under; data sheet ordering information
ORDERABLE = {
    "ac": "DCS-7280DR3A-36-F",
    "ac-m": "DCS-7280DR3AM-36-F",
    "ac-k": "DCS-7280DR3AK-36-F",
    "ac-k-s": "DCS-7280DR3AK-36S-F",
}


def load():
    return yaml.safe_load((LIB / "devices/arista" / DEV / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/arista" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


# ---------------------------------------------------------------- the envelope


def test_the_envelope_is_the_guides_table_1():
    """Table 1: 48.3 x 8.8 x 61.2 cm, 19 in over the ears and 2RU. The data sheet gives the body,
    43.99 x 8.79 x 61.18 cm; the width is the body's, the guide's figure being over the ears."""
    c = load()["chassis"]
    assert c["ru"] == 2
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert c["height"] == pytest.approx(88.0, abs=0.5)
    assert c["depth"] == pytest.approx(612.0, abs=0.5)
    assert c["weight-kg"] == pytest.approx(24.1, abs=0.05)
    assert (483.0 - c["width"]) / 2 == pytest.approx(21.5, abs=0.5)


def test_every_face_is_sized_from_the_envelope():
    d = load()
    c = d["chassis"]
    v = d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    for n in ("front", "rear"):
        assert v[n]["size"] == {"w": c["width"], "h": c["height"]}, n
    for n in ("top", "bottom"):
        assert v[n]["size"] == {"w": c["width"], "h": c["depth"]}, n
    for n in ("left", "right"):
        assert v[n]["size"] == {"w": c["depth"], "h": c["height"]}, n


def test_the_maker_and_the_names_are_as_printed():
    d = load()
    assert d["manufacturer"] == "Arista"
    assert d["model"] == "7280DR3A-36"
    assert d["portfolio"] == {"line": "7000 Series", "family": "7280DR3A"}
    assert d["maturity"] == "modelled"


def test_the_arista_maker_is_in_the_registry():
    reg = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert reg["arista"]["display"] == "Arista Networks"
    assert reg["arista"]["role"] == "both"


# ------------------------------------------------------------------ the front


def test_the_front_has_36_qsfp_dd_cages_numbered_down_eighteen_columns():
    d = load()
    cages = {int(p["id"].split("-")[1]): p for p in placements(d, "front")
             if p["ref"] == "std/qsfp-dd@1"}
    assert sorted(cages) == list(range(1, 37))
    for n, p in cages.items():
        assert p["rel-pos"] == n and p["group"] == "qsfpdd-400g"
        # the odd number is the upper cage, the even one below it and turned
        assert p.get("rotate", 0) == (180 if n % 2 == 0 else 0)
        assert (p["at"][1] < cages[n + 1]["at"][1]) if n % 2 == 1 else True
    xs = sorted({p["at"][0] for p in cages.values()})
    assert len(xs) == 18
    for a, b in zip(xs, xs[1:]):
        assert b - a == pytest.approx(23.05, abs=0.02)
    assert d["groups"]["qsfpdd-400g"]["attrs"] == {"media": "qsfp-dd", "speed": "400g"}


def test_two_osfp_line_system_ports_are_numbered_37_and_38():
    d = load()
    osfp = {p["id"]: p for p in placements(d, "front") if p["ref"] == "std/osfp@1"}
    assert sorted(osfp) == ["port-37", "port-38"]
    assert osfp["port-37"]["at"][0] < osfp["port-38"]["at"][0]
    assert d["groups"]["osfp-ls-400g"]["attrs"] == {"media": "osfp", "speed": "400g"}
    printed = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
               if s.get("for") in osfp and s.get("text")}
    assert printed == {"port-37": "37", "port-38": "38"}


def test_every_cage_has_its_strip_numeral_and_a_lamp():
    d = load()
    printed = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
               if str(s.get("for", "")).startswith("port-") and s.get("text")}
    assert printed == {f"port-{n}": str(n) for n in range(1, 39)}
    lamps = [p for p in placements(d, "front") if p["id"].startswith("led-port-")]
    assert len(lamps) == 36


def test_the_front_carries_four_status_lamps_console_usb_management_and_timing():
    d = load()
    ps = {p["id"]: p for p in placements(d, "front")}
    for pid in ("led-sys", "led-fan", "led-psu1", "led-psu2", "console", "usb", "mgmt",
                "tod", "pps", "clk-10mhz"):
        assert pid in ps, pid
    xs = [ps[k]["at"][0] for k in ("led-sys", "led-fan", "led-psu1", "led-psu2")]
    assert xs == sorted(xs)
    # figure C-2 left to right: lamps, console, USB, management
    assert (ps["led-psu2"]["at"][0] < ps["console"]["at"][0] < ps["usb"]["at"][0]
            < ps["mgmt"]["at"][0])
    assert ps["mgmt"]["ref"] == "common/rj45-eth@1" and ps["console"]["ref"] == "std/rj45@2"
    assert ps["tod"]["ref"] == "std/usb-c@1"
    assert ps["led-psu1"]["for"] == "rear/psu-1" and ps["led-psu2"]["for"] == "rear/psu-2"


def test_the_front_prints_the_model_and_reserves_the_logo_zone():
    d = load()
    front = d["views"]["front"]
    assert "7280DR3A-36" in {s.get("text") for s in front["silkscreen"]}
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for name, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, name


# ------------------------------------------------------------------- the rear


def test_the_rear_has_four_fan_bays_and_two_psu_bays_that_take_the_listed_modules():
    d = load()
    b = bays(d, "rear")
    assert sorted(b) == ["fan-1", "fan-2", "fan-3", "fan-4", "psu-1", "psu-2"]
    for i in range(1, 5):
        assert b[f"fan-{i}"]["accepts"] == [FAN] and b[f"fan-{i}"]["default"] == FAN
    for i in (1, 2):
        assert sorted(b[f"psu-{i}"]["accepts"]) == sorted([AC, DC])
        assert b[f"psu-{i}"]["default"] == AC
    # the supplies stand one above the other at the right, the fans left of them
    assert b["psu-1"]["at"][0] == b["psu-2"]["at"][0] > b["fan-4"]["at"][0]
    assert b["psu-1"]["at"][1] < b["psu-2"]["at"][1]
    # figure D-3: fan 1 is separated from fan 2 by the grounding pad
    xs = [b[f"fan-{i}"]["at"][0] for i in range(1, 5)]
    assert xs[1] - xs[0] > xs[2] - xs[1] + 5
    assert xs[2] - xs[1] == pytest.approx(xs[3] - xs[2], abs=0.2)
    assert {p["id"] for p in placements(d, "rear")} == {"ground-1", "ground-2"}


def test_the_fan_and_supply_modules_carry_the_data_sheets_part_numbers_and_airflow():
    fan, ac, dc = contract("7280dr3a-fan"), contract("7280dr3a-pwr-2400-ac"), \
        contract("7280dr3a-pwr-2400-dc")
    assert list(fan["part-numbers"]) == ["FAN-7012H-RED"] and fan["class"] == "fan"
    assert list(ac["part-numbers"]) == ["PWR-2411-AC-RED"] and ac["class"] == "psu"
    assert list(dc["part-numbers"]) == ["PWR-2411-DC-RED"] and dc["class"] == "psu"
    for c in (fan, ac, dc):
        assert c["attrs"]["airflow"] == "front-to-back"
        assert c["fields"]["handle-finish"]["default"].startswith("#")
    assert ac["attrs"]["power-output-w"] == dc["attrs"]["power-output-w"] == 2400
    assert ac["size"] == dc["size"] == {"w": 73.5, "h": 40.0}


def test_the_new_components_are_family_prefixed_and_cite_a_size():
    root = LIB / "components/arista"
    names = sorted(p.name for p in root.iterdir() if p.name.startswith("7280dr3a-"))
    # the DR3A-54's supplies (pwr-3000) sit beside these and are held by its own test
    assert set(names) >= {"7280dr3a-fan", "7280dr3a-pwr-2400-ac", "7280dr3a-pwr-2400-dc"}
    names = [n for n in names if "pwr-3000" not in n]
    for n in names:
        assert "size" in (contract(n).get("provenance") or {}), n


# ------------------------------------------------------------ configurations


def test_the_orderable_configurations_are_the_datasheets_f_part_numbers():
    cf = load()["configurations"]
    assert {n for n, c in cf.items() if c["kind"] == "orderable"} == set(ORDERABLE)
    for name, pn in ORDERABLE.items():
        assert list(cf[name]["part-numbers"]) == [pn], name
    # the DC build is a worked example: the data sheet lists no DC part number
    assert cf["dc"]["kind"] == "example" and "part-numbers" not in cf["dc"]
    assert [n for n, c in cf.items() if c.get("default")] == ["base"]


def test_each_configuration_seats_matching_supplies_and_no_airflow_override():
    cf = load()["configurations"]
    for name, c in cf.items():
        assert "airflow" not in c, name
        psus = (c.get("bays") or {})
        if name == "dc":
            assert psus == {"psu-1": DC, "psu-2": DC}
            assert c["power"] == "dc"
        elif name != "base":
            assert psus == {"psu-1": AC, "psu-2": AC}, name
    assert load()["chassis"]["airflow"] == "front-to-back"


def test_the_dc_rear_differs_from_the_ac_rear_only_in_the_supplies():
    cf = load()["configurations"]
    assert cf["dc"]["bays"]["psu-1"] != cf["ac"]["bays"]["psu-1"]


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_orderable_configuration_two_u_high(target):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    got = {p.stem for p in folder.glob("DCS-7280DR3A*-36*.yaml")}
    assert got == set(ORDERABLE.values())
    for pn in ORDERABLE.values():
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista" and doc["model"] == pn
        assert doc["u_height"] == 2.0
    for pn in ("FAN-7012H-RED", "PWR-2411-AC-RED", "PWR-2411-DC-RED"):
        mod = yaml.safe_load((LIB / "exports" / target / "module-types/Arista" / f"{pn}.yaml").read_text())
        assert mod["manufacturer"] == "Arista" and mod["part_number"] == pn


def test_the_exported_type_lists_the_38_ports_and_no_more():
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Arista/DCS-7280DR3A-36-F.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {f"port-{n}" for n in range(1, 39)} <= set(types)
    assert "port-39" not in types and "port-0" not in types
    assert {types[f"port-{n}"] for n in range(1, 37)} == {"400gbase-x-qsfpdd"}
    assert {types["port-37"], types["port-38"]} == {"400gbase-x-osfp"}
