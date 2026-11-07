"""The Juniper EX3400 family: four fixed access switches that share one chassis.

Each model is a device of its own, because the front panels differ (24 or 48 jacks, and the
PoE+ printing on the P models). The guide's Table 3 gives one chassis for the whole family, so
the envelope is the same for every model; Tables 1 and 12 give the port counts and the power
supply each model ships with, and Table 10 gives the airflow.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/juniper"
COMPONENTS = LIB / "components/juniper"
EXPORTS = LIB / "exports/netbox"

# model -> (RJ-45 ports, default power supply component, its part number, PoE)
MODELS = {
    "ex3400-24t": (24, "ex3400-jpsu-150-ac-afo", "JPSU-150-AC-AFO", False),
    "ex3400-24p": (24, "ex3400-jpsu-600-ac-afo", "JPSU-600-AC-AFO", True),
    "ex3400-48t": (48, "ex3400-jpsu-150-ac-afo", "JPSU-150-AC-AFO", False),
    "ex3400-48p": (48, "ex3400-jpsu-920-ac-afo", "JPSU-920-AC-AFO", True),
}


# Table 1: the variants that share a front panel are configurations of one device, keyed here by
# configuration id and giving the part number. The PoE models have one build each, and only the
# EX3400-48T has a back-to-front (-AFI) build.
CONFIGS = {
    "ex3400-24t": {"ac": "EX3400-24T", "dc": "EX3400-24T-DC"},
    "ex3400-24p": {"ac": "EX3400-24P"},
    "ex3400-48t": {"ac": "EX3400-48T", "ac-afi": "EX3400-48T-AFI", "dc": "EX3400-48T-DC"},
    "ex3400-48p": {"ac": "EX3400-48P"},
}
DC_PSU = "juniper/ex3400-jpsu-150-dc-afo@1"
AFI_PSU = "juniper/ex3400-jpsu-150-ac-afi@1"
AFI_FAN = "juniper/ex3400-fan-afi@1"


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def component(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def placements(d, face):
    comps = (d["views"][face].get("components") or {})
    return comps.get("placements") or []


def bays(d, face):
    return (d["views"][face].get("components") or {}).get("bays") or []


@pytest.mark.parametrize("name", MODELS)
def test_envelope_is_table_3(name):
    # Table 3: 1.72 in. (4.37 cm) high, 17.4 in. (44.1 cm) wide, 13.78 in. (35 cm) deep with no
    # power supply installed. The 19 in. width is with the mounting brackets attached.
    ch = load(name)["chassis"]
    assert ch["width"] == 441.0
    assert ch["height"] == 43.7
    assert ch["depth"] == 350.0
    assert ch["ru"] == 1


@pytest.mark.parametrize("name", MODELS)
def test_naming(name):
    d = load(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "EX Series", "family": "EX3400"}


@pytest.mark.parametrize("name", MODELS)
def test_front_jacks_are_numbered_from_zero_with_the_even_ports_on_top(name):
    count = MODELS[name][0]
    jacks = {p["id"]: p for p in placements(load(name), "front") if p["id"].startswith("port-")}
    assert sorted(jacks, key=lambda i: int(i.split("-")[1])) == [f"port-{n}" for n in range(count)]
    assert {p["ref"] for p in jacks.values()} == {"common/rj45-ganged-eth@1"}
    for n in range(count):
        j = jacks[f"port-{n}"]
        assert j["rel-pos"] == n
        # the upper jack of a column is turned 180 so that its keyway and lamps face up
        assert j.get("rotate", 0) == (180 if n % 2 == 0 else 0)
        if n % 2 == 0:
            assert jacks[f"port-{n + 1}"]["at"][1] > j["at"][1]
            assert jacks[f"port-{n + 1}"]["at"][0] == j["at"][0]


@pytest.mark.parametrize("name", MODELS)
def test_front_uplinks_are_four_sfp_cages_numbered_0_to_3(name):
    cages = [p for p in placements(load(name), "front") if p["id"].startswith("uplink-")]
    assert [p["id"] for p in cages] == [f"uplink-{n}" for n in range(4)]
    assert {p["ref"] for p in cages} == {"std/sfp-ganged@1"}
    xs = [p["at"][0] for p in cages]
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [14.25] * 3


@pytest.mark.parametrize("name", MODELS)
def test_front_has_the_status_block_the_guide_names(name):
    d = load(name)
    ids = {p["id"] for p in placements(d, "front")}
    # Figure 5: SYS, ALM, MST. Figure 10: SPD, DX, EN, PoE. Then the Factory Reset/Mode button. The
    # Mini-USB console is the placed registry receptacle, and its old gap is gone.
    assert {"led-sys", "led-alm", "led-mst", "led-spd", "led-dx", "led-en", "led-poe",
            "mode-btn", "console-usb"} <= ids
    assert not any(g["what"] == "mini-usb-console-port" for g in d["gaps"])
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {"SYS", "ALM", "MST", "SPD", "DX", "EN", "POE", "CON"} <= legends
    # the photographs print PoE+ on the P models and not on the T models
    assert ("PoE+" in legends) is MODELS[name][3]


@pytest.mark.parametrize("name", MODELS)
def test_rear_ports(name):
    d = load(name)
    byid = {p["id"]: p["ref"] for p in placements(d, "rear")}
    assert byid["vcp-0"] == byid["vcp-1"] == "std/qsfp-ganged@1"
    assert byid["mgmt"] == "common/rj45-eth@1"
    assert byid["con"] == "std/rj45@2"
    assert byid["usb"] == "std/usb-a@1"
    assert len([i for i in byid if i.startswith("vcp-")]) == 2
    # Table 41: the earthing terminal takes two 10-32 screws and a two-hole lug
    assert byid["ground-pair"] == "juniper/ex3400-ground-pair@1"
    legends = {s["text"] for s in d["views"]["rear"]["silkscreen"] if "text" in s}
    assert {"MGMT", "CON", "0", "1"} <= legends


@pytest.mark.parametrize("name", MODELS)
def test_default_configuration_part_numbers_and_modules(name):
    _, psu, psu_pn, _ = MODELS[name]
    d = load(name)
    cfgs = d["configurations"]
    assert {k: list(c["part-numbers"]) for k, c in cfgs.items()} == \
        {k: [pn] for k, pn in CONFIGS[name].items()}
    assert all(c["kind"] == "orderable" for c in cfgs.values())
    ac = cfgs["ac"]
    assert ac["default"] is True and not any(c.get("default") for k, c in cfgs.items() if k != "ac")
    assert list(ac["part-numbers"]) == [d["model"]]
    by = {b["id"]: b for b in bays(d, "rear")}
    # Table 36: the switch ships with one power supply and two fan modules
    assert by["psu-0"]["default"] == f"juniper/{psu}@1"
    assert by["psu-1"]["default"] == "juniper/ex3400-psu-blank@1"
    assert by["fan-0"]["default"] == by["fan-1"]["default"] == "juniper/ex3400-fan-afo@1"
    assert component(psu)["part-numbers"] == {psu_pn: {"part": psu_pn}}


def seated(d, cfg, bay):
    """The module a configuration seats in a rear bay: its own entry, else the bay's default."""
    by = {b["id"]: b for b in bays(d, "rear")}
    return (d["configurations"][cfg].get("bays") or {}).get(bay, by[bay]["default"])


@pytest.mark.parametrize("name", MODELS)
def test_modules_airflow_matches_the_chassis(name):
    # Table 10: every model is front-to-back except the EX3400-48T-AFI, and a mix of directions is
    # a major alarm (Table 12 and the install topics), so each configuration seats one direction
    d = load(name)
    assert d["chassis"]["airflow"] == "front-to-back"
    for cfg in d["configurations"]:
        want = d["configurations"][cfg].get("airflow", d["chassis"]["airflow"])
        assert want == ("back-to-front" if cfg == "ac-afi" else "front-to-back")
        for bay in ("psu-0", "fan-0", "fan-1"):
            ref = seated(d, cfg, bay).split("/", 1)[1].split("@")[0]
            attrs = component(ref).get("attrs") or {}
            assert attrs["airflow"] == want, (cfg, bay, ref)


def test_the_afi_and_dc_builds_seat_their_own_supplies():
    d = load("ex3400-48t")
    assert seated(d, "ac-afi", "psu-0") == AFI_PSU
    assert seated(d, "ac-afi", "fan-0") == seated(d, "ac-afi", "fan-1") == AFI_FAN
    assert seated(d, "dc", "psu-0") == DC_PSU
    assert d["configurations"]["dc"]["power"] == "dc"
    # the slot that ships blank stays blank in every build
    assert {seated(d, c, "psu-1") for c in d["configurations"]} == {"juniper/ex3400-psu-blank@1"}
    assert seated(load("ex3400-24t"), "dc", "psu-0") == DC_PSU
    # Table 1 builds no -AFI or -DC of the PoE models
    for name in ("ex3400-24p", "ex3400-48p"):
        assert list(load(name)["configurations"]) == ["ac"]


@pytest.mark.parametrize("name", MODELS)
def test_bays_accept_what_the_guide_lists(name):
    psu = MODELS[name][1]
    by = {b["id"]: b for b in bays(load(name), "rear")}
    assert set(by) == {"fan-0", "fan-1", "psu-0", "psu-1"}
    fans = ["juniper/ex3400-fan-afo@1"] + (["juniper/ex3400-fan-afi@1"] if name == "ex3400-48t" else [])
    for i in ("fan-0", "fan-1"):
        assert sorted(by[i]["accepts"]) == sorted(fans)
    # a slot takes the model's supplies (Table 12 and 16) or the blank panel that covers it
    want = [f"juniper/{psu}@1", "juniper/ex3400-psu-blank@1"]
    if not MODELS[name][3]:
        want.append(DC_PSU)
    if name == "ex3400-48t":
        want.append(AFI_PSU)
    for i in ("psu-0", "psu-1"):
        assert sorted(by[i]["accepts"]) == sorted(want)


@pytest.mark.parametrize("name", MODELS)
def test_dcim_export_has_one_device_type_per_orderable_configuration(name):
    d = load(name)
    exported = sorted(p.stem for p in (EXPORTS / "device-types/Juniper").glob(f"{d['model']}*.yaml"))
    assert exported == sorted(CONFIGS[name].values())
    for pn in exported:
        doc = yaml.safe_load((EXPORTS / f"device-types/Juniper/{pn}.yaml").read_text())
        assert doc["u_height"] == 1.0
        assert doc["manufacturer"] == "Juniper"
        assert doc["airflow"] == ("rear-to-front" if pn.endswith("-AFI") else "front-to-rear")


@pytest.mark.parametrize("pn", sorted({v[2] for v in MODELS.values()} |
                                      {"EX3400-FAN-AFO2", "JPSU-150-AC-AFI", "JPSU-150-DC-AFO"}))
def test_module_types_are_exported_under_their_part_numbers(pn):
    doc = yaml.safe_load((EXPORTS / f"module-types/Juniper/{pn}.yaml").read_text())
    assert doc["part_number"] == pn


def silk_texts(d):
    """Every printed string on every face of a device, with its entry."""
    out = []
    for view in d["views"].values():
        out += [s for s in (view.get("silkscreen") or []) if "text" in s]
    return out


@pytest.mark.parametrize("name", MODELS)
def test_no_face_draws_the_vendor_wordmark(name):
    # The logo is a trademark, so the layout reserves a `logo-zone` and prints nothing in it.
    # "EX3400" and "PoE+" are the model's own printing and stay.
    texts = {s["text"] for s in silk_texts(load(name))}
    assert not {t for t in texts if t.upper() in ("JUNIPER", "NETWORKS")}, texts
    assert "EX3400" in texts
    assert ("PoE+" in texts) == MODELS[name][3]


# The 48T photograph (ex3400-48t-front-high) prints the port numerals light grey: the lightest
# pixels of the numeral row, median of the 20 brightest, are (193, 188, 186). The 48P photograph
# prints them orange. The ink is thin, so the photograph's value is a floor on the true one.
NUMERAL_FILL = {"ex3400-24t": "#c1bcba", "ex3400-48t": "#c1bcba",
                "ex3400-24p": "#e8603a", "ex3400-48p": "#e8603a"}


@pytest.mark.parametrize("name", MODELS)
def test_port_numerals_take_the_colour_their_photograph_prints(name):
    d = load(name)
    numerals = [s for s in silk_texts(d) if s.get("for", "").startswith("port-")]
    assert len(numerals) == MODELS[name][0]
    assert {s["fill"] for s in numerals} == {NUMERAL_FILL[name]}


def test_the_blank_panels_finger_holes_are_d_shaped_recesses_with_a_lip():
    # Figure 3 callout 11 and the EX3400-48P rear photograph: a flat edge on the outer side, a
    # round end toward the middle of the plate, and an inner lip around the well.
    svg = (COMPONENTS / "ex3400-psu-blank/v1/skins/default.svg").read_text()
    for side in ("left", "right"):
        hole = re.search(rf'<path id="grip-{side}"[^>]*\bd="([^"]*)"', svg)
        assert hole and " A" in hole.group(1), f"grip-{side} is not an arc-ended path"
        assert f'id="grip-{side}-lip"' in svg
    assert 'rx="10.0"' not in svg, "a stadium oval is still drawn"
