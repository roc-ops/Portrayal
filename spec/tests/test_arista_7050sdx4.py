"""The Arista 7050SDX4-48D8, a fixed 1RU switch with 48 SFP-DD and 8 QSFP-DD ports (#1204, slice 1).

One device under `arista/`, 7050sdx4-48d8 (DCS-7050SDX4-48D8, figure C-3), with two orderable
configurations (-F and -R) and two DC examples. The DCS-7050SPX4-48D8 (48 DSFP) is NOT modelled: the
library has no DSFP cage.

The expected figures are Arista's: the 7050X4 Series Quick Start Guide (DOC-06569-02: Table 1 for the
envelope, Tables 3 and 4 for the supplies, Appendix C figure C-3 and Appendix D for the faces) and the
7050X4 Series Data Sheet (03-0057-27, 27 Aug 2025: the model comparison and its ordering information).
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
NAME = "7050sdx4-48d8"

P1000 = ["arista/7280cr3-pwr-1000-ac@1", "arista/7280cr3-pwr-1000-ac-rev@1",
         "arista/7280cr3-pwr-1000-dc@1", "arista/7280cr3-pwr-1000-dc-rev@1"]
# The data sheet's "Fan Tray" cell for this model: FAN-7011M-F and FAN-7011H-R.
FANS = ["arista/7280r3-fan-m@1", "arista/7280cr3-fan-rev@1"]
SFPDD, QDD = "std/sfp-dd-ganged@1", "std/qsfp-dd@1"
PORTS = {**{n: SFPDD for n in range(1, 49)}, **{n: QDD for n in range(49, 57)}}
ORDERABLE = {"f": "DCS-7050SDX4-48D8-F", "r": "DCS-7050SDX4-48D8-R"}


def load():
    return yaml.safe_load((LIB / "devices/arista" / NAME / "device.yaml").read_text())


def contract_of(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def ports(d):
    return {int(p["id"].split("-")[1]): p for p in placements(d, "front")
            if re.fullmatch(r"port-\d+", p["id"])}


def seated(d, cfg, bay):
    c = d["configurations"][cfg]
    return (c.get("bays") or {}).get(bay) or bays(d, "rear")[bay]["default"]


# ---------------------------------------------------------------- the envelope


def test_the_envelope_is_the_guides_table_1():
    """Table 1: 48.3 x 4.4 x 47.5 cm over the ears, 1RU; the body between them is the data sheet's
    43.99 cm wide and 4.37 cm high."""
    c = load()["chassis"]
    assert c["ru"] == 1
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert (483.0 - c["width"]) / 2 == pytest.approx(21.5, abs=0.5)
    assert c["height"] == pytest.approx(43.7, abs=0.1)
    assert c["depth"] == pytest.approx(475.0, abs=0.1)


def test_every_face_is_sized_from_the_envelope():
    d = load()
    c, v = d["chassis"], d["views"]
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
    assert d["model"] == "7050SDX4-48D8"
    assert d["portfolio"] == {"line": "7000 Series", "family": "7050X4"}
    assert d["maturity"] == "modelled"


def test_the_power_figures_are_table_4_and_the_data_sheet():
    p = load()["attrs"]["power"]
    assert (p["power-typical-w"], p["power-max-w"]) == (165, 520)


# ------------------------------------------------------------------ the front


def test_the_front_has_48_sfp_dd_and_8_qsfp_dd_numbered_as_printed():
    """Figure C-3: 1 to 24 left of the QSFP-DD columns, 49 to 56 in them, 25 to 48 right of them; the
    odd number is the upper cage."""
    d = load()
    got = ports(d)
    assert sorted(got) == sorted(PORTS)
    for n, ref in PORTS.items():
        assert got[n]["ref"] == ref, n
        assert got[n]["rel-pos"] == n, n
        want_turn = 180 if n % 2 == 0 else 0
        assert got[n].get("rotate", 0) == want_turn, n
    for n in PORTS:
        if n % 2 == 1:
            up, low = got[n], got[n + 1]
            assert up["at"][0] == pytest.approx(low["at"][0], abs=0.01), n
            assert up["at"][1] < low["at"][1], n


def test_the_cages_are_on_the_pitch_the_figure_gives():
    """Tab centres 26.8 px apart at 1.884 px/mm is the registry's 14.25 mm SFP-DD ganged pitch; the
    QSFP-DD tabs are 19.0 mm apart. The groups run left to right 1-12, 13-24, 49-56, 25-36, 37-48."""
    got = ports(load())
    xs = sorted({round(got[n]["at"][0], 2) for n in range(1, 49) if n % 2})
    assert len(xs) == 24
    runs = [xs[i + 1] - xs[i] for i in range(23)]
    assert sorted(runs)[:20] == [pytest.approx(14.25, abs=0.01)] * 20
    q = sorted({round(got[n]["at"][0], 2) for n in range(49, 57) if n % 2})
    assert [round(q[i + 1] - q[i], 2) for i in range(3)] == [19.0, 19.0, 19.0]
    first = {k: got[k]["at"][0] for k in (1, 13, 25, 37, 49)}
    assert first[1] < first[13] < first[49] < first[25] < first[37]
    assert got[2]["at"][1] > got[1]["at"][1]


def test_the_groups_carry_the_media_and_speed_of_each_family():
    d = load()
    for n, p in ports(d).items():
        assert p["group"] in d["groups"], n
    media = {g: (v["attrs"]["media"], v["attrs"]["speed"])
             for g, v in d["groups"].items() if v["role"] == "traffic"}
    assert media == {"sfp-dd": ("sfp-dd", "100g"), "qsfpdd-400g": ("qsfp-dd", "400g")}


def test_the_front_prints_every_port_number_and_the_model_and_reserves_the_logo_zone():
    d = load()
    front = d["views"]["front"]
    printed = {s["for"]: s["text"] for s in front["silkscreen"]
               if re.fullmatch(r"port-\d+", str(s.get("for", ""))) and s.get("text")}
    assert printed == {f"port-{n}": str(n) for n in PORTS}
    assert "7050SDX4-48D8" in {s.get("text") for s in front["silkscreen"]}
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for vname, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, vname


def test_the_front_has_four_status_lamps_and_one_lamp_a_port():
    d = load()
    ps = {p["id"]: p for p in placements(d, "front")}
    for pid in ("led-system", "led-fan", "led-ps1", "led-ps2"):
        assert ps[pid]["group"] == "status-leds", pid
    assert ps["led-ps1"]["for"] == "rear/psu-1" and ps["led-ps2"]["for"] == "rear/psu-2"
    assert ps["led-fan"]["for"] == ["rear/fan-1", "rear/fan-2", "rear/fan-3"]
    lamps = {i for i in ps if i.startswith("led-port-")}
    assert lamps == {f"led-port-{n}" for n in PORTS}


def test_the_management_ports_are_at_the_rear_as_figure_d_1_draws_them():
    d = load()
    ps = {p["id"]: p for p in placements(d, "rear")}
    assert sorted(ps) == ["console", "mgmt", "usb"]
    assert ps["mgmt"]["at"][1] < ps["usb"]["at"][1] < ps["console"]["at"][1]
    assert not [p for p in placements(d, "front") if p["id"] in ("mgmt", "usb", "console")]


# ------------------------------------------------------------------- the rear


def test_each_bay_accepts_the_modules_the_data_sheet_lists():
    """Table 4: PWR-1011-AC and -DC; the data sheet: PWR-1011-AC/DC-RED/BLUE and the fan tray cell
    FAN-7011M-F and FAN-7011H-R."""
    b = bays(load(), "rear")
    assert sorted(b) == ["fan-1", "fan-2", "fan-3", "psu-1", "psu-2"]
    for i in (1, 2):
        assert b[f"psu-{i}"]["accepts"] == P1000
        assert b[f"psu-{i}"]["default"] == P1000[0]
    for i in (1, 2, 3):
        assert b[f"fan-{i}"]["accepts"] == FANS
        assert b[f"fan-{i}"]["default"] == FANS[0]
    assert b["psu-1"]["at"][0] < b["fan-1"]["at"][0] < b["fan-3"]["at"][0] < b["psu-2"]["at"][0]


def test_the_fans_are_the_exact_part_numbers_other_arista_models_already_carry():
    """One part number, one component: nothing is added for any of them."""
    assert list(contract_of("arista/7280r3-fan-m@1")["part-numbers"]) == ["FAN-7011M-F"]
    assert list(contract_of("arista/7280cr3-fan-rev@1")["part-numbers"]) == ["FAN-7011H-R"]
    assert list(contract_of("arista/7280cr3-pwr-1000-ac@1")["part-numbers"]) == ["PWR-1011-AC-RED"]
    assert list(contract_of("arista/7280cr3-pwr-1000-dc-rev@1")["part-numbers"]) == ["PWR-1011-DC-BLUE"]
    assert not [p for p in (LIB / "components/arista").iterdir() if "7050sdx4" in p.name]


def test_every_module_a_bay_accepts_has_its_part_number_and_airflow():
    for ref in P1000 + FANS:
        c = contract_of(ref)
        assert c["class"] in ("psu", "fan"), ref
        assert c["part-numbers"], ref
        part = list(c["part-numbers"])[0]
        red = part.endswith(("-RED", "-F"))
        assert (c["attrs"]["airflow"] == "front-to-back") == red, (ref, part)


# ------------------------------------------------------------ configurations


def test_the_orderable_configurations_are_the_data_sheets_part_numbers():
    cf = load()["configurations"]
    assert {n for n, c in cf.items() if c["kind"] == "orderable"} == set(ORDERABLE)
    for cfg, pn in ORDERABLE.items():
        assert list(cf[cfg]["part-numbers"]) == [pn], cfg
    assert [n for n, c in cf.items() if c.get("default")] == ["base"]
    for n, c in cf.items():
        if c["kind"] == "example":
            assert "part-numbers" not in c, n


def test_each_configuration_seats_matching_supplies_and_fans_with_matching_airflow():
    """-F seats the PWR-1011-AC-RED supplies and FAN-7011M-F; -R the BLUE supplies and FAN-7011H-R."""
    d = load()
    assert d["chassis"]["airflow"] == "front-to-back"
    assert d["configurations"]["base"].get("bays") is None
    for cfg, c in d["configurations"].items():
        rev = cfg.endswith("r") and cfg != "base"
        dc = c.get("power") == "dc"
        flow = "back-to-front" if rev else "front-to-back"
        assert c.get("airflow", "front-to-back") == flow, cfg
        modules = [seated(d, cfg, f"psu-{i}") for i in (1, 2)] + \
                  [seated(d, cfg, f"fan-{i}") for i in (1, 2, 3)]
        for ref in modules:
            assert ref in P1000 + FANS, (cfg, ref)
            assert contract_of(ref)["attrs"]["airflow"] == flow, (cfg, ref)
        for i in (1, 2):
            psu = contract_of(seated(d, cfg, f"psu-{i}"))
            assert psu["attrs"]["input"] == ("dc" if dc else "ac"), (cfg, i)
        assert seated(d, cfg, "psu-1") == seated(d, cfg, "psu-2"), cfg
        assert len({seated(d, cfg, f"fan-{i}") for i in (1, 2, 3)}) == 1, cfg
    fan = {cfg: list(contract_of(seated(d, cfg, "fan-1"))["part-numbers"])[0] for cfg in ("f", "r")}
    assert fan == {"f": "FAN-7011M-F", "r": "FAN-7011H-R"}


def test_the_dsfp_sibling_is_left_out_and_the_gaps_say_what_the_figure_got_wrong():
    assert not (LIB / "devices/arista/7050spx4-48d8").exists()
    gaps = {g["what"] for g in load()["gaps"]}
    assert {"figure-typo", "fan-count", "rack-ears"} <= gaps


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_types_export_one_per_orderable_configuration_with_the_guides_height(target):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    for pn in ORDERABLE.values():
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista" and doc["model"] == pn
        assert doc["u_height"] == 1.0, pn
        names = {i["name"] for i in doc["interfaces"]}
        assert {f"port-{n}" for n in PORTS} <= names, pn
        assert "port-57" not in names, pn
    assert {p.stem for p in folder.glob("DCS-7050SDX4*.yaml")} == set(ORDERABLE.values())


def test_the_exported_ports_are_the_cages_the_data_sheet_names():
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Arista/DCS-7050SDX4-48D8-F.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {types[f"port-{n}"] for n in range(49, 57)} == {"400gbase-x-qsfpdd"}
    assert {types[f"port-{n}"] for n in range(1, 49)} == {"100gbase-x-sfpdd"}
