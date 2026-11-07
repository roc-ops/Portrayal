"""The Juniper EX4100 family, the four 1G copper models: EX4100-24T, -24P, -48T and -48P.

Each model is a device of its own, because the front panels differ (24 or 48 jacks, and the
PoE+ printing on the P models). The guide's Table 19 gives one chassis for the whole family,
Tables 7 to 14 give the port counts and the supply each model ships with, and Table 27 gives
the airflow. The -AFI and -DC builds share a front panel with their sibling and are
configurations of it.
"""
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
    "ex4100-24t": (24, "ex4100-jpsu-150-ac-afo", "JPSU-150-AC-AFO", False),
    "ex4100-24p": (24, "ex4100-jpsu-920-ac-afo", "JPSU-920-AC-AFO", True),
    "ex4100-48t": (48, "ex4100-jpsu-150-ac-afo", "JPSU-150-AC-AFO", False),
    "ex4100-48p": (48, "ex4100-jpsu-920-ac-afo", "JPSU-920-AC-AFO", True),
}

# Tables 9 and 13: the variants that share a front panel are configurations of one device. Only the
# EX4100-48T has a back-to-front (-AFI) build, the T models have a -DC build, and the PoE models have
# one build each. The EX4100-48T-DC-T1 is a tray assembly (Table 56) and is not a configuration.
CONFIGS = {
    "ex4100-24t": {"ac": "EX4100-24T", "dc": "EX4100-24T-DC"},
    "ex4100-24p": {"ac": "EX4100-24P"},
    "ex4100-48t": {"ac": "EX4100-48T", "afi": "EX4100-48T-AFI", "dc": "EX4100-48T-DC"},
    "ex4100-48p": {"ac": "EX4100-48P"},
}
DC_PSU = "juniper/ex4100-jpsu-150-dc-afo@1"
AFI_PSU = "juniper/ex4100-jpsu-150-ac-afi@1"
AFI_FAN = "juniper/ex4100-fan-afi@1"
COVER = "juniper/ex4100-psu-cover@1"


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
def test_envelope_is_table_19(name):
    # Table 19: 1.72 in. (4.37 cm) high, 13.78 in. (35 cm) deep with no power supply and fan module
    # and 17.36 in. (44.09 cm) wide for all models. The 19 in. width is with the brackets attached.
    ch = load(name)["chassis"]
    assert ch["width"] == 440.9
    assert ch["height"] == 43.7
    assert ch["depth"] == 350.0
    assert ch["ru"] == 1
    d = load(name)
    for face, size in (("front", (440.9, 43.7)), ("rear", (440.9, 43.7)), ("top", (440.9, 350.0))):
        assert (d["views"][face]["size"]["w"], d["views"][face]["size"]["h"]) == size


@pytest.mark.parametrize("name", MODELS)
def test_naming(name):
    d = load(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4100"}
    assert d["maturity"] == "modelled"


@pytest.mark.parametrize("name", MODELS)
def test_front_jacks_are_numbered_from_zero_with_the_even_ports_on_top(name):
    count = MODELS[name][0]
    jacks = {p["id"]: p for p in placements(load(name), "front") if p["id"].startswith("port-")}
    assert sorted(jacks, key=lambda i: int(i.split("-")[1])) == [f"port-{n}" for n in range(count)]
    assert {p["ref"] for p in jacks.values()} == {"common/rj45-ganged-eth@1"}
    for n in range(count):
        j = jacks[f"port-{n}"]
        assert j["rel-pos"] == n
        # the upper jack of a column is turned 180 so that its lamp tabs face up, as rendered
        assert j.get("rotate", 0) == (180 if n % 2 == 0 else 0)
        if n % 2 == 0:
            assert jacks[f"port-{n + 1}"]["at"][1] > j["at"][1]
            assert jacks[f"port-{n + 1}"]["at"][0] == j["at"][0]


@pytest.mark.parametrize("name", MODELS)
def test_jack_columns_are_the_blocks_the_figures_draw(name):
    # Figures 1, 5, 10 and 14: the 48-port models have three blocks of eight columns on the
    # registry's 13.97 mm pitch. The 24-port models have a block of four columns spread 15.78 mm
    # apart and a block of eight on the 13.97 mm pitch.
    count = MODELS[name][0]
    jacks = {p["id"]: p for p in placements(load(name), "front") if p["id"].startswith("port-")}
    xs = [jacks[f"port-{n}"]["at"][0] for n in range(0, count, 2)]
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    if count == 48:
        assert steps == ([13.97] * 7 + [19.67]) * 2 + [13.97] * 7
    else:
        assert steps == [15.78] * 3 + [round(243.75 - (176.75 + 15.78 * 3), 2)] + [13.97] * 7
    ys = {round(jacks[f"port-{n}"]["at"][1], 2) for n in range(0, count, 2)}
    assert ys == {10.32}


@pytest.mark.parametrize("name", MODELS)
@pytest.mark.parametrize("prefix,lead", (("vcp-", 359.7), ("uplink-", 391.0)))
def test_front_has_two_blocks_of_four_sfp_cages_numbered_0_to_3(name, prefix, lead):
    # Tables 8, 10, 12 and 14: four 10GE/25GE SFP28 Virtual Chassis ports and four 1GE/10GE SFP+
    # uplink ports, each printed 0 to 3 in two columns of two (the even ports on top).
    cages = {p["id"]: p for p in placements(load(name), "front") if p["id"].startswith(prefix)
             and not p["id"].startswith("led-")}
    assert sorted(cages) == [f"{prefix}{n}" for n in range(4)]
    assert {p["ref"] for p in cages.values()} == {"std/sfp-ganged@1"}
    assert cages[f"{prefix}0"]["at"][0] == lead
    assert cages[f"{prefix}2"]["at"][0] - lead == 14.25
    for n in (0, 2):
        assert cages[f"{prefix}{n + 1}"]["at"][1] > cages[f"{prefix}{n}"]["at"][1]
        assert cages[f"{prefix}{n + 1}"].get("rotate") == 180
    groups = {p["group"] for p in cages.values()}
    assert groups == {"sfp28" if prefix == "vcp-" else "sfp-plus"}


@pytest.mark.parametrize("name", MODELS)
def test_each_cage_has_a_link_and_a_status_lamp(name):
    # Figure 30 and Figure 31: a Link Activity lamp and a Status lamp on every cage
    ids = {p["id"] for p in placements(load(name), "front")}
    for prefix in ("vcp", "uplink"):
        for n in range(4):
            assert {f"led-{prefix}-{n}-link", f"led-{prefix}-{n}-status"} <= ids


@pytest.mark.parametrize("name", MODELS)
def test_front_has_the_status_block_the_guide_names(name):
    d = load(name)
    ids = {p["id"] for p in placements(d, "front")}
    poe = MODELS[name][3]
    # Figure 27: SYS, ALM, MST and CLD. Figure 32: SPD, DX, EN, and PoE where the model has PoE.
    # Then the Factory Reset/Mode button and the RS232 to USB Type-C console.
    assert {"led-sys", "led-alm", "led-mst", "led-cld", "led-spd", "led-dx", "led-en",
            "mode-btn", "usb-c", "reset-pinhole"} <= ids
    assert ("led-poe" in ids) is poe
    usbc = next(p for p in placements(d, "front") if p["id"] == "usb-c")
    assert usbc["ref"] == "std/usb-c@1" and usbc["attrs"]["role"] == "console"
    legends = {s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s}
    assert {"SYS", "ALM", "MST", "CLD", "SPD", "DX", "EN", "CON", "UPLINK"} <= legends
    assert ("PoE" in legends) is poe
    assert ("PoE+" in legends) is poe


@pytest.mark.parametrize("name", MODELS)
def test_rear_ports(name):
    d = load(name)
    byid = {p["id"]: p["ref"] for p in placements(d, "rear")}
    # Figures 4, 8, 13 and 17: MGMT RJ-45 over a USB 2.0 Type-A, the CON RJ-45, the protective
    # earthing terminal (Table 59: two M5 screws) and the ESD point
    assert byid["mgmt"] == "common/rj45-eth@1"
    assert byid["con"] == "std/rj45@2"
    assert byid["usb"] == "std/usb-a@1"
    assert {"ground-hole-1", "ground-hole-2"} <= {x["id"] for x in d["views"]["rear"]["panel"]["decor"]}
    assert byid["esd-rear"] == "common/esd-jack@1"
    legends = {s["text"] for s in d["views"]["rear"]["silkscreen"] if "text" in s}
    assert {"MGMT", "CON", "0", "1"} <= legends
    regions = {r["id"] for r in d["views"]["rear"].get("regions") or []}
    # Figure 3 callout 10: the 24-port models carry the claim code label on the front, the 48-port ones on the rear
    assert ("label-claim" in regions) is (MODELS[name][0] == 48)
    front_regions = {r["id"] for r in d["views"]["front"].get("regions") or []}
    assert ("label-claim" in front_regions) is (MODELS[name][0] == 24)


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
    # Table 53: the switch ships with one power supply and two fan modules, preinstalled
    assert by["psu-0"]["default"] == f"juniper/{psu}@1"
    assert by["psu-1"]["default"] == COVER
    assert by["fan-0"]["default"] == by["fan-1"]["default"] == "juniper/ex4100-fan-afo@1"
    assert component(psu)["part-numbers"] == {psu_pn: {"part": psu_pn}}
    assert component("ex4100-fan-afo")["part-numbers"] == {"EX4100-FAN-AFO": {"part": "EX4100-FAN-AFO"}}


def seated(d, cfg, bay):
    """The module a configuration seats in a rear bay: its own entry, else the bay's default."""
    by = {b["id"]: b for b in bays(d, "rear")}
    return (d["configurations"][cfg].get("bays") or {}).get(bay, by[bay]["default"])


@pytest.mark.parametrize("name", MODELS)
def test_modules_airflow_matches_the_chassis(name):
    # Table 27: every model is front to back except the EX4100-48T-AFI, and a mix of directions
    # raises an alarm, so each configuration seats one direction
    d = load(name)
    assert d["chassis"]["airflow"] == "front-to-back"
    for cfg in d["configurations"]:
        want = d["configurations"][cfg].get("airflow", d["chassis"]["airflow"])
        assert want == ("back-to-front" if cfg == "afi" else "front-to-back")
        for bay in ("psu-0", "fan-0", "fan-1"):
            ref = seated(d, cfg, bay).split("/", 1)[1].split("@")[0]
            attrs = component(ref).get("attrs") or {}
            assert attrs["airflow"] == want, (cfg, bay, ref)


def test_the_afi_and_dc_builds_seat_their_own_supplies():
    d = load("ex4100-48t")
    assert seated(d, "afi", "psu-0") == AFI_PSU
    assert seated(d, "afi", "fan-0") == seated(d, "afi", "fan-1") == AFI_FAN
    assert seated(d, "dc", "psu-0") == DC_PSU
    assert d["configurations"]["dc"]["power"] == "dc"
    # the slot that ships covered stays covered in every build
    assert {seated(d, c, "psu-1") for c in d["configurations"]} == {COVER}
    assert seated(load("ex4100-24t"), "dc", "psu-0") == DC_PSU
    # Table 9 and Table 13 build no -AFI of the 24T, and no -AFI or -DC of the PoE models
    assert list(load("ex4100-24t")["configurations"]) == ["ac", "dc"]
    for name in ("ex4100-24p", "ex4100-48p"):
        assert list(load(name)["configurations"]) == ["ac"]


def test_the_airflow_in_modules_have_blue_handles_and_the_airflow_out_ones_orange():
    # Table 26: AIR OUT with an orange handle, AIR IN with a blue handle
    for fan, colour, label in (("ex4100-fan-afo", "#ee6a1f", "AIR"), ("ex4100-fan-afi", "#3d7bd6", "AIR")):
        svg = (COMPONENTS / fan / "v1/skins/default.svg").read_text()
        assert colour in svg
        assert component(fan)["attrs"]["handle-colour"] == ("orange" if colour == "#ee6a1f" else "blue")
    assert "OUT</text>" in (COMPONENTS / "ex4100-fan-afo/v1/skins/default.svg").read_text()
    assert "IN</text>" in (COMPONENTS / "ex4100-fan-afi/v1/skins/default.svg").read_text()
    assert "#ee6a1f" not in (COMPONENTS / "ex4100-fan-afi/v1/skins/default.svg").read_text()
    assert "#3d7bd6" in (COMPONENTS / "ex4100-jpsu-150-ac-afi/v1/skins/default.svg").read_text()


@pytest.mark.parametrize("name", MODELS)
def test_bays_accept_what_the_guide_lists(name):
    psu = MODELS[name][1]
    by = {b["id"]: b for b in bays(load(name), "rear")}
    assert set(by) == {"fan-0", "fan-1", "psu-0", "psu-1"}
    fans = ["juniper/ex4100-fan-afo@1"] + ([AFI_FAN] if name == "ex4100-48t" else [])
    for i in ("fan-0", "fan-1"):
        assert sorted(by[i]["accepts"]) == sorted(fans)
    # a slot takes the model's supplies (Tables 29 and 37) or the cover panel that closes it
    want = [f"juniper/{psu}@1", COVER]
    if not MODELS[name][3]:
        want.append(DC_PSU)
    if name == "ex4100-48t":
        want.append(AFI_PSU)
    for i in ("psu-0", "psu-1"):
        assert sorted(by[i]["accepts"]) == sorted(want)


def test_module_sizes_are_the_guides_table_20_note():
    # fan 1.9 x 1.65 x 4.41 in. and supply 2.87 x 1.57 x 8.86 in.: the heights and depths are the
    # guide's, and the fan face is 41.9 wide where the render measures it
    for fan in ("ex4100-fan-afo", "ex4100-fan-afi"):
        s = component(fan)["size"]
        assert (s["h"], s["d"]) == (41.8, 112.0)
    for psu in ("ex4100-jpsu-150-ac-afo", "ex4100-jpsu-150-ac-afi", "ex4100-jpsu-150-dc-afo",
                "ex4100-jpsu-920-ac-afo"):
        s = component(psu)["size"]
        assert (s["w"], s["h"], s["d"]) == (73.0, 40.0, 225.0)


@pytest.mark.parametrize("pn,watts", (("ex4100-jpsu-150-ac-afo", 150), ("ex4100-jpsu-150-ac-afi", 150),
                                      ("ex4100-jpsu-150-dc-afo", 150), ("ex4100-jpsu-920-ac-afo", 920)))
def test_power_supplies_state_their_output(pn, watts):
    # Tables 30, 31 and 38: output power
    assert component(pn)["attrs"]["power-output-w"] == watts


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


def silk_texts(d):
    """Every printed string on every face of a device, with its entry."""
    out = []
    for view in d["views"].values():
        out += [s for s in (view.get("silkscreen") or []) if "text" in s]
    return out


@pytest.mark.parametrize("name", MODELS)
def test_no_face_draws_the_vendor_wordmark(name):
    # The logo is a trademark, so the layout reserves a `logo-zone` and prints nothing in it.
    # "EX4100" and "PoE+" are the model's own printing and stay.
    d = load(name)
    texts = {s["text"] for s in silk_texts(d)}
    assert not {t for t in texts if t.upper() in ("JUNIPER", "NETWORKS", "MIST AI")}, texts
    assert "EX4100" in texts
    assert ("PoE+" in texts) == MODELS[name][3]
    assert "logo-zone" in {r["id"] for r in d["views"]["front"]["regions"]}


# The renders print the port numerals salmon on the PoE models (the median of the most saturated
# pixels, #ff8074) and light grey on the others.
NUMERAL_FILL = {"ex4100-24t": "#e8eaec", "ex4100-48t": "#e8eaec",
                "ex4100-24p": "#ff8074", "ex4100-48p": "#ff8074"}


@pytest.mark.parametrize("name", MODELS)
def test_port_numerals_take_the_colour_the_render_prints(name):
    d = load(name)
    numerals = [s for s in silk_texts(d) if str(s.get("for", "")).startswith("port-")]
    assert len(numerals) == MODELS[name][0]
    assert {s["fill"] for s in numerals} == {NUMERAL_FILL[name]}
