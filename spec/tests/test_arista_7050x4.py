"""The Arista 7050X4 line, five fixed switches (#1204, slice 1).

Devices, one per front panel, under `arista/`:

    7050dx4-32s       DCS-7050DX4-32S   (and, as a configuration, the DX4M-32S: figure C-1 is shared)
    7050px4-32s       DCS-7050PX4-32S
    7050cx4-24d8      DCS-7050CX4-24D8
    7050x4-48y-4df    DCS-7050X4-48Y-4DF
    7050cx4m-48d8     DCS-7050CX4M-48D8 (2RU)

The 7050SDX4-48D8 has its own module, test_arista_7050sdx4.py (it needs the SFP-DD cage). The
7050SPX4-48D8 is NOT modelled: the library has no DSFP cage, so there is nothing to seat.

The expected figures are Arista's: the 7050X4 Series Quick Start Guide (DOC-06569-02: Table 1 for the
envelope, Tables 3 and 4 for the supplies, Appendix C and D for the faces) and the 7050X4 Series Data
Sheet (03-0057-27, 27 Aug 2025: the model comparison and its ordering information). Each test reads the
YAML a contributor edits, or the generated export a DCIM user imports.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

P1500 = ["arista/7050x4-pwr-1500-ac@1", "arista/7050x4-pwr-1500-ac-rev@1",
         "arista/7280r3-pwr-1500-dc@1", "arista/7050x4-pwr-1500-dc-rev@1"]
P1000 = ["arista/7280cr3-pwr-1000-ac@1", "arista/7280cr3-pwr-1000-ac-rev@1",
         "arista/7280cr3-pwr-1000-dc@1", "arista/7280cr3-pwr-1000-dc-rev@1"]
P500 = ["arista/7280r3-pwr-500-ac@1", "arista/7280r3-pwr-500-ac-rev@1",
        "arista/7280r3-pwr-500-dc@1", "arista/7280r3-pwr-500-dc-rev@1"]
F7011H = ["arista/7280cr3-fan@1", "arista/7280cr3-fan-rev@1"]
F7011M = ["arista/7280r3-fan-m@1", "arista/7280r3-fan-m-rev@1"]
F7012H = ["arista/7280dr3a-fan@1", "arista/7050x4-fan-7012h-rev@1"]

QDD, QSFP56, QSFPG, OSFP, SFPG = ("std/qsfp-dd@1", "std/qsfp56@1", "std/qsfp-ganged@1", "std/osfp@1",
                                   "std/sfp-ganged@1")

# name -> what the guide and the data sheet say of it. `ports` is {number: cage ref}.
DEVICES = {
    "7050dx4-32s": dict(
        model="7050DX4-32S", ru=1, height=43.7, depth=505.6,
        ports={**{n: QDD for n in range(1, 33)}, 33: SFPG, 34: SFPG},
        psu=P1500, fan=F7011H, nfans=3, mgmt_view="rear", ledcount=34, ship="f",
        orderable={"f": "DCS-7050DX4-32S-F", "r": "DCS-7050DX4-32S-R", "m-f": "DCS-7050DX4M-32S-F"},
        rev={"r"}, stacked=True),
    "7050px4-32s": dict(
        model="7050PX4-32S", ru=1, height=43.7, depth=527.0,
        ports={**{n: OSFP for n in range(1, 33)}, 33: SFPG, 34: SFPG},
        psu=P1500, fan=F7011H, nfans=3, mgmt_view="rear", ledcount=34, ship="f",
        orderable={"f": "DCS-7050PX4-32S-F", "r": "DCS-7050PX4-32S-R"},
        rev={"r"}, stacked=True),
    "7050cx4-24d8": dict(
        model="7050CX4-24D8", ru=1, height=43.7, depth=475.0,
        ports={**{n: QSFP56 for n in range(1, 25)}, **{n: QDD for n in range(25, 33)}, 33: SFPG, 34: SFPG},
        psu=P1000, fan=F7011H, nfans=3, mgmt_view="rear", ledcount=34, ship="f",
        orderable={"f": "DCS-7050CX4-24D8-F", "r": "DCS-7050CX4-24D8-R"},
        rev={"r"}, stacked=True),
    "7050x4-48y-4df": dict(
        model="7050X4-48Y-4DF", ru=1, height=43.7, depth=475.0,
        ports={**{n: SFPG for n in range(1, 49)}, **{n: QDD for n in range(49, 53)}},
        psu=P500, fan=F7011M, nfans=3, mgmt_view="rear", ledcount=52, ship="f",
        orderable={"f": "DCS-7050X4-48Y-4DF-F", "r": "DCS-7050X4-48Y-4DF-R"},
        rev={"r"}, stacked=True),
    "7050cx4m-48d8": dict(
        model="7050CX4M-48D8", ru=2, height=87.9, depth=668.0,
        ports={**{n: QSFPG for n in range(1, 49)}, **{n: QDD for n in range(49, 57)}, 57: SFPG, 58: SFPG},
        psu=P1500, fan=F7012H, nfans=4, mgmt_view="front", ledcount=10, ship="f",
        orderable={"f": "DCS-7050CX4M-48D8-F", "r": "DCS-7050CX4M-48D8-R"},
        rev={"r"}, stacked=True),
}
NAMES = sorted(DEVICES)


def load(name):
    return yaml.safe_load((LIB / "devices/arista" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/arista" / name / "v1/contract.yaml").read_text())


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
    """What a configuration seats in a rear bay: its own entry, else the bay's default."""
    c = d["configurations"][cfg]
    return (c.get("bays") or {}).get(bay) or bays(d, "rear")[bay]["default"]


# ---------------------------------------------------------------- the envelope


@pytest.mark.parametrize("name", NAMES)
def test_the_envelope_is_the_guides_table_1(name):
    """Table 1: 48.3 cm over the ears (the body between them is the data sheet's 43.99 cm), 4.4 cm
    (1RU) or 8.8 cm (2RU) high. The DX4-32S depth is settled between the guide's 50.1 cm and its own
    19.9 in (505.5 mm): 505.6, the data sheet's, which the inches agree with."""
    want = DEVICES[name]
    c = load(name)["chassis"]
    assert c["ru"] == want["ru"]
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert (483.0 - c["width"]) / 2 == pytest.approx(21.5, abs=0.5)
    assert c["height"] == pytest.approx(want["height"], abs=0.1)
    assert c["height"] == pytest.approx(44.0 * want["ru"], abs=0.5 * want["ru"] + 0.3)
    assert c["depth"] == pytest.approx(want["depth"], abs=0.1)


@pytest.mark.parametrize("name", NAMES)
def test_every_face_is_sized_from_the_envelope(name):
    d = load(name)
    c, v = d["chassis"], d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    for n in ("front", "rear"):
        assert v[n]["size"] == {"w": c["width"], "h": c["height"]}, n
    for n in ("top", "bottom"):
        assert v[n]["size"] == {"w": c["width"], "h": c["depth"]}, n
    for n in ("left", "right"):
        assert v[n]["size"] == {"w": c["depth"], "h": c["height"]}, n


@pytest.mark.parametrize("name", NAMES)
def test_the_maker_and_the_names_are_as_printed(name):
    d = load(name)
    assert d["manufacturer"] == "Arista"
    assert d["model"] == DEVICES[name]["model"]
    assert d["portfolio"] == {"line": "7000 Series", "family": "7050X4"}
    assert d["maturity"] == "modelled"


# ------------------------------------------------------------------ the front


@pytest.mark.parametrize("name", NAMES)
def test_the_front_ports_are_the_guides_count_cage_and_numbering(name):
    """Figures C-1 to C-7: numbered as printed (1 to the last, odd over even in a stacked pair), each in
    the cage the data sheet names."""
    d = load(name)
    got = ports(d)
    want = DEVICES[name]["ports"]
    assert sorted(got) == sorted(want)
    for n, ref in want.items():
        p = got[n]
        assert p["ref"] == ref, n
        assert p["rel-pos"] == n, n
    for n in want:
        if n % 2 == 1 and n + 1 in want:
            up, low = got[n], got[n + 1]
            assert up["at"][0] == pytest.approx(low["at"][0], abs=0.01), n
            assert up["at"][1] < low["at"][1], n


@pytest.mark.parametrize("name", NAMES)
def test_every_front_port_is_in_a_declared_group_with_its_media_and_speed(name):
    d = load(name)
    for n, p in ports(d).items():
        assert p["group"] in d["groups"], n
    media = {g: v.get("attrs") for g, v in d["groups"].items() if v["role"] == "traffic"}
    want = {
        "7050dx4-32s": {"qsfpdd-400g": ("qsfp-dd", "400g"), "sfp-plus": ("sfp-plus", "10g")},
        "7050px4-32s": {"osfp-400g": ("osfp", "400g"), "sfp-plus": ("sfp-plus", "10g")},
        "7050cx4-24d8": {"qsfp56-200g": ("qsfp56", "200g"), "qsfpdd-400g": ("qsfp-dd", "400g"),
                         "sfp-plus": ("sfp-plus", "10g")},
        "7050x4-48y-4df": {"sfp28": ("sfp28", "25g"), "qsfpdd-400g": ("qsfp-dd", "400g")},
        "7050cx4m-48d8": {"qsfp28-100g": ("qsfp28", "100g"), "qsfpdd-400g": ("qsfp-dd", "400g"),
                          "sfp-plus": ("sfp-plus", "10g")},
    }[name]
    assert {g: (a["media"], a["speed"]) for g, a in media.items()} == want


@pytest.mark.parametrize("name", NAMES)
def test_the_lower_cage_of_a_stacked_pair_is_turned_by_the_librarys_convention(name):
    """Belly to belly (upper 0, lower 180) for the QSFP, SFP and QSFP-DD families; a stacked OSFP pair
    is turned alike (lint L108, the OSFP MSA)."""
    got = ports(load(name))
    for n, p in got.items():
        if p["ref"] == OSFP:
            assert p.get("rotate", 0) == 0, n
        elif n % 2 == 0:
            assert p.get("rotate", 0) == 180, n
        else:
            assert p.get("rotate", 0) == 0, n


@pytest.mark.parametrize("name", NAMES)
def test_the_front_prints_every_port_number_and_the_model_and_reserves_the_logo_zone(name):
    d = load(name)
    front = d["views"][("front")]
    printed = {s["for"]: s["text"] for s in front["silkscreen"]
               if re.fullmatch(r"port-\d+", str(s.get("for", ""))) and s.get("text")}
    assert printed == {f"port-{n}": str(n) for n in DEVICES[name]["ports"]}
    assert DEVICES[name]["model"] in {s.get("text") for s in front["silkscreen"]}
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for vname, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, vname


@pytest.mark.parametrize("name", NAMES)
def test_the_front_has_four_status_lamps_naming_the_fans_and_both_supplies(name):
    d = load(name)
    ps = {p["id"]: p for p in placements(d, "front")}
    for pid in ("led-system", "led-fan", "led-ps1", "led-ps2"):
        assert pid in ps, pid
        assert ps[pid]["group"] == "status-leds"
    assert ps["led-ps1"]["for"] == "rear/psu-1" and ps["led-ps2"]["for"] == "rear/psu-2"
    n = DEVICES[name]["nfans"]
    assert ps["led-fan"]["for"] == [f"rear/fan-{i}" for i in range(1, n + 1)]


@pytest.mark.parametrize("name", NAMES)
def test_the_port_lamps_are_one_a_port_where_the_figure_shows_them(name):
    """Table 10: a link lamp near each port. Figure C-7 shows none beside the 48 QSFP28 cages (a gap)."""
    d = load(name)
    lamps = {p["id"] for p in placements(d, "front") if p["id"].startswith("led-port-")}
    want = {f"led-port-{n}" for n in DEVICES[name]["ports"]}
    if name == "7050cx4m-48d8":
        want = {f"led-port-{n}" for n in range(49, 59)}
        assert any(g["what"] == "port-lamps" for g in d["gaps"])
    assert lamps == want


def test_the_cx4m_front_carries_the_management_usb_and_console_ports():
    """Figure C-7 callouts 2 to 4; every other 7050X4 model carries them at the rear (figure D-1)."""
    d = load("7050cx4m-48d8")
    ps = {p["id"]: p for p in placements(d, "front")}
    assert ps["mgmt"]["ref"] == "common/rj45-eth@1" and ps["usb"]["ref"] == "std/usb-a@1"
    assert ps["console"]["ref"] == "std/rj45@2"
    assert ps["mgmt"]["at"][1] < ps["usb"]["at"][1] < ps["console"]["at"][1]
    assert {p["id"] for p in placements(d, "rear")} == {"ground-1", "ground-2"}


@pytest.mark.parametrize("name", [n for n in NAMES if n != "7050cx4m-48d8"])
def test_the_one_ru_models_carry_their_management_ports_at_the_rear(name):
    d = load(name)
    ps = {p["id"]: p for p in placements(d, "rear")}
    assert sorted(ps) == ["console", "mgmt", "usb"]
    assert ps["mgmt"]["at"][1] < ps["usb"]["at"][1] < ps["console"]["at"][1]
    assert not [p for p in placements(d, "front") if p["id"] in ("mgmt", "usb", "console")]


# ------------------------------------------------------------------- the rear


@pytest.mark.parametrize("name", NAMES)
def test_each_bay_accepts_the_modules_the_guide_and_data_sheet_list(name):
    """Table 4 and the data sheet's model comparison: the supply and fan family of each model, red and
    blue, AC and DC."""
    want = DEVICES[name]
    d = load(name)
    b = bays(d, "rear")
    nf = want["nfans"]
    assert sorted(b) == sorted([f"fan-{i}" for i in range(1, nf + 1)] + ["psu-1", "psu-2"])
    for i in (1, 2):
        assert b[f"psu-{i}"]["accepts"] == want["psu"]
        assert b[f"psu-{i}"]["default"] == want["psu"][0]
    for i in range(1, nf + 1):
        assert b[f"fan-{i}"]["accepts"] == want["fan"]
        assert b[f"fan-{i}"]["default"] == want["fan"][0]
    xs = [b[f"fan-{i}"]["at"][0] for i in range(1, nf + 1)]
    assert xs == sorted(xs)


@pytest.mark.parametrize("name", NAMES)
def test_the_supplies_stand_at_the_ends_of_a_1ru_rear_and_one_above_the_other_on_a_2ru_one(name):
    b = bays(load(name), "rear")
    if DEVICES[name]["ru"] == 1:
        assert b["psu-1"]["at"][0] < b["fan-1"]["at"][0] < b["fan-3"]["at"][0] < b["psu-2"]["at"][0]
    else:
        assert b["psu-1"]["at"][0] == b["psu-2"]["at"][0] > b["fan-4"]["at"][0]
        assert b["psu-1"]["at"][1] < b["psu-2"]["at"][1]


@pytest.mark.parametrize("name", NAMES)
def test_every_module_a_bay_accepts_is_a_component_with_its_part_number_and_airflow(name):
    want = DEVICES[name]
    for ref in want["psu"] + want["fan"]:
        c = contract_of(ref)
        assert c["class"] in ("psu", "fan"), ref
        assert c["part-numbers"], ref
        assert c["attrs"]["airflow"] in ("front-to-back", "back-to-front"), ref
        part = list(c["part-numbers"])[0]
        red = part.endswith(("-RED", "-F")) or part == "FAN-7011H-F"
        assert (c["attrs"]["airflow"] == "front-to-back") == red, (ref, part)


# ------------------------------------------------------------ configurations


@pytest.mark.parametrize("name", NAMES)
def test_the_orderable_configurations_are_the_datasheets_part_numbers(name):
    cf = load(name)["configurations"]
    want = DEVICES[name]["orderable"]
    assert {n for n, c in cf.items() if c["kind"] == "orderable"} == set(want)
    for cfg, pn in want.items():
        assert list(cf[cfg]["part-numbers"]) == [pn], cfg
    assert [n for n, c in cf.items() if c.get("default")] == ["base"]
    for n, c in cf.items():
        if c["kind"] == "example":
            assert "part-numbers" not in c, n


@pytest.mark.parametrize("name", NAMES)
def test_each_configuration_seats_matching_supplies_and_fans_with_matching_airflow(name):
    """-F: red, front-to-back; -R: blue, back-to-front; the DC examples likewise. The two supplies and
    all the fans of a build agree with each other and with the configuration's airflow."""
    d = load(name)
    want = DEVICES[name]
    nf = want["nfans"]
    for cfg, c in d["configurations"].items():
        rev = cfg.endswith("r") and cfg != "base"
        dc = c.get("power") == "dc"
        flow = "back-to-front" if rev else "front-to-back"
        assert c.get("airflow", "front-to-back") == flow, cfg
        modules = [seated(d, cfg, f"psu-{i}") for i in (1, 2)] + \
                  [seated(d, cfg, f"fan-{i}") for i in range(1, nf + 1)]
        for ref in modules:
            assert ref in want["psu"] + want["fan"], (cfg, ref)
            assert contract_of(ref)["attrs"]["airflow"] == flow, (cfg, ref)
        for i in (1, 2):
            psu = contract_of(seated(d, cfg, f"psu-{i}"))
            assert psu["attrs"]["input"] == ("dc" if dc else "ac"), (cfg, i)
        assert seated(d, cfg, "psu-1") == seated(d, cfg, "psu-2"), cfg
        assert len({seated(d, cfg, f"fan-{i}") for i in range(1, nf + 1)}) == 1, cfg
    assert d["configurations"]["base"].get("bays") is None
    assert d["chassis"]["airflow"] == "front-to-back"


def test_the_dx4m_is_a_configuration_of_the_dx4_because_figure_c_1_is_shared():
    """Figure C-1 is captioned "DCS-7050DX4-32S and DCS-7050DX4M-32S"; the other MACsec build, the
    CX4M-48D8, has a front of its own and is a device of its own. The DX4M has no -R build."""
    d = load("7050dx4-32s")
    m = d["configurations"]["m-f"]
    assert list(m["part-numbers"]) == ["DCS-7050DX4M-32S-F"]
    assert "423" in m["description"] and "1208" in m["description"]
    assert not [n for n in d["configurations"] if n.startswith("m-r")]
    assert not (LIB / "devices/arista/7050dx4m-32s").exists()
    assert not (LIB / "devices/arista/7050spx4-48d8").exists()


def test_the_48y_power_figures_are_the_datasheets_because_the_guides_read_typical_above_maximum():
    p = load("7050x4-48y-4df")["attrs"]["power"]
    assert (p["power-typical-w"], p["power-max-w"]) == (120, 223)
    assert p["power-typical-w"] < p["power-max-w"]
    assert any(g["what"] == "power-figures" for g in load("7050x4-48y-4df")["gaps"])


# ---------------------------------------------------------------- components


def test_the_new_components_are_family_prefixed_with_the_part_numbers_and_colours_of_the_data_sheet():
    root = LIB / "components/arista"
    names = sorted(p.name for p in root.iterdir() if p.name.startswith("7050x4-"))
    assert names == [
        "7050x4-fan-7012h-rev",
        "7050x4-pwr-1500-ac", "7050x4-pwr-1500-ac-rev", "7050x4-pwr-1500-dc-rev"]
    parts = {
        "7050x4-fan-7012h-rev": "FAN-7012H-BLUE",
        "7050x4-pwr-1500-ac": "PWR-1512-AC-RED", "7050x4-pwr-1500-ac-rev": "PWR-1512-AC-BLUE",
        "7050x4-pwr-1500-dc-rev": "PWR-1511-DC-BLUE"}
    for n, pn in parts.items():
        c = contract(n)
        assert list(c["part-numbers"]) == [pn], n
        assert "size" in (c.get("provenance") or {}), n
        blue = n.endswith("-rev")
        assert c["attrs"]["airflow"] == ("back-to-front" if blue else "front-to-back"), n
        assert c["fields"]["handle-finish"]["default"] == ("#3d7bd6" if blue else
                                                           ("#e0332e" if "fan" in n else "#a32a38")), n
        if c["class"] == "psu":
            assert c["size"] == {"w": 73.5, "h": 40.0}
            assert c["attrs"]["power-output-w"] == int(n.split("-")[2])


def test_the_reused_components_are_the_exact_part_numbers_other_arista_models_already_carry():
    """PWR-1011-AC/DC RED/BLUE, FAN-7011H-F/R and FAN-7012H-RED are reused, not copied."""
    assert list(contract("7280cr3-pwr-1000-ac")["part-numbers"]) == ["PWR-1011-AC-RED"]
    assert list(contract("7280cr3-pwr-1000-dc-rev")["part-numbers"]) == ["PWR-1011-DC-BLUE"]
    assert list(contract("7280cr3-fan")["part-numbers"]) == ["FAN-7011H-F"]
    assert list(contract("7280cr3-fan-rev")["part-numbers"]) == ["FAN-7011H-R"]
    assert list(contract("7280dr3a-fan")["part-numbers"]) == ["FAN-7012H-RED"]
    # the part numbers the 7280R3 models carry too are that line's components, not 7050X4 copies
    for n, pn in {"7280r3-fan-m": "FAN-7011M-F", "7280r3-fan-m-rev": "FAN-7011M-R",
                  "7280r3-pwr-1500-dc": "PWR-1511-DC-RED",
                  "7280r3-pwr-500-ac": "PWR-511-AC-RED", "7280r3-pwr-500-ac-rev": "PWR-511-AC-BLUE",
                  "7280r3-pwr-500-dc": "PWR-511-DC-RED", "7280r3-pwr-500-dc-rev": "PWR-511-DC-BLUE"}.items():
        assert list(contract(n)["part-numbers"]) == [pn], n
    held = {pn for p in (LIB / "components/arista").iterdir() if p.name.startswith("7050x4-")
            for pn in contract(p.name)["part-numbers"]}
    carried = {pn for p in (LIB / "components/arista").iterdir() if p.name.startswith("7280r3-")
               for pn in contract(p.name)["part-numbers"]}
    assert not held & carried


# ------------------------------------------------------------------ the DCIM


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_dcim_types_export_one_per_orderable_configuration_with_the_guides_height(target, name):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    for cfg, pn in DEVICES[name]["orderable"].items():
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista" and doc["model"] == pn
        assert doc["u_height"] == float(DEVICES[name]["ru"]), pn
        types = {i["name"] for i in doc["interfaces"]}
        assert {f"port-{n}" for n in DEVICES[name]["ports"]} <= types, pn
        assert f"port-{max(DEVICES[name]['ports']) + 1}" not in types, pn


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_exports_nothing_for_an_example_or_a_left_out_model(target):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    got = {p.stem for p in folder.glob("DCS-7050*.yaml") if "7050SDX4" not in p.stem}
    want = {pn for v in DEVICES.values() for pn in v["orderable"].values()}
    assert got == want


def test_the_exported_ports_are_the_cages_the_data_sheet_names():
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Arista/DCS-7050CX4-24D8-F.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert {types[f"port-{n}"] for n in range(25, 33)} == {"400gbase-x-qsfpdd"}
    assert len({types[f"port-{n}"] for n in range(1, 25)}) == 1
    assert types["port-1"] not in ("400gbase-x-qsfpdd", "10gbase-x-sfpp")
    assert {types["port-33"], types["port-34"]} == {"10gbase-x-sfpp"}
    doc = yaml.safe_load(
        (LIB / "exports/netbox/device-types/Arista/DCS-7050PX4-32S-F.yaml").read_text())
    assert {i["type"] for i in doc["interfaces"] if i["name"] in {f"port-{n}" for n in range(1, 33)}} \
        == {"400gbase-x-osfp"}
