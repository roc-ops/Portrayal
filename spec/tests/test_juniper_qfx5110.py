"""The Juniper QFX5110-48S and QFX5110-32Q, from the QFX5110 Switch Hardware Guide (2026-09-24).

One device per front panel. The 48S has 48 SFP+ cages and four QSFP28 cages, the 32Q has 28 QSFP+ cages and
four QSFP28 cages, so they are two devices. Each one's power and airflow variants are `orderable`
configurations of it, because the guide shows one panel for all of them. The supplies and fan modules are
components that the library already held (the 650 W supplies of the QFX5100, the fan modules of the QFX5120)
and are reused as they are.

What the guide fixes, and so what these tests hold:
  Table 24   the envelope - 1.72 x 17.36 x 20.48 in, 1RU, and the weight of each model
  Table 3    the variants and their part numbers (the 32Q alone has a chassis-only spare, -CHAS)
  Table 11   the fan modules, their airflow and colour
  Tables 13 and 18   the 650 W AC and DC supplies, their airflow and handle colour
  Tables 5 to 8   the port lamps: two for an SFP+ port, four for a QSFP+ or QSFP28 port
  figures 14 and 15   the ports, their count and numbering, the grandmaster clock jack and the two coaxial jacks
  figures 16 and 17   the rear and the management panel
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 24: height, width, depth in inches (1RU), and the weight with two supplies in kilograms
ENVELOPE_IN = {
    "qfx5110-48s": {"h": 1.72, "w": 17.36, "d": 20.48, "kg": 10.43},
    "qfx5110-32q": {"h": 1.72, "w": 17.36, "d": 20.48, "kg": 11.16},
}
DEVICES = sorted(ENVELOPE_IN)

AFO_AC, AFI_AC = "qfx5100-jpsu-650w-ac-afo", "qfx5100-jpsu-650w-ac-afi"
AFO_DC, AFI_DC = "qfx5100-jpsu-650w-dc-afo", "qfx5100-jpsu-650w-dc-afi"
# Table 11 (pp. 40-41): one fan module per model and airflow, and p. 44 says to use only the one for the model
FAN = {
    "qfx5110-48s": ("qfx5110-48s-fanafo", "qfx5110-48s-fanafi"),
    "qfx5110-32q": ("qfx5110-32q-fanafo", "qfx5110-32q-fanafi"),
}
FAN_AFO_48S, FAN_AFI_48S = FAN["qfx5110-48s"]
FAN_AFO_32Q, FAN_AFI_32Q = FAN["qfx5110-32q"]
ALL_FANS = sorted((*FAN["qfx5110-48s"], *FAN["qfx5110-32q"]))

# Table 3: configuration -> (part number, supply, fan, airflow, feed); a None supply is an open bay
VARIANTS = {
    "qfx5110-48s": {
        "ac-f2b": ("QFX5110-48S-AFO", AFO_AC, FAN_AFO_48S, "front-to-back", "ac"),
        "ac-b2f": ("QFX5110-48S-AFI", AFI_AC, FAN_AFI_48S, "back-to-front", "ac"),
        "dc-f2b": ("QFX5110-48S-DC-AFO", AFO_DC, FAN_AFO_48S, "front-to-back", "dc"),
        "dc-b2f": ("QFX5110-48S-DC-AFI", AFI_DC, FAN_AFI_48S, "back-to-front", "dc"),
    },
    "qfx5110-32q": {
        "ac-f2b": ("QFX5110-32Q-AFO", AFO_AC, FAN_AFO_32Q, "front-to-back", "ac"),
        "ac-b2f": ("QFX5110-32Q-AFI", AFI_AC, FAN_AFI_32Q, "back-to-front", "ac"),
        "dc-f2b": ("QFX5110-32Q-DC-AFO", AFO_DC, FAN_AFO_32Q, "front-to-back", "dc"),
        "dc-b2f": ("QFX5110-32Q-DC-AFI", AFI_DC, FAN_AFI_32Q, "back-to-front", "dc"),
        "chas": ("QFX5110-32Q-CHAS", None, None, "front-to-back", "ac"),
    },
}
CASES = [(n, c) for n in sorted(VARIANTS) for c in VARIANTS[n]]
SEATED_CASES = [(n, c) for n, c in CASES if VARIANTS[n][c][1]]
PSUS = {AFO_AC, AFI_AC, AFO_DC, AFI_DC}
MODEL = {  # the part number the guide prints for each unit that the library carries
    AFO_AC: "JPSU-650W-AC-AFO", AFI_AC: "JPSU-650W-AC-AFI",
    AFO_DC: "JPSU-650W-DC-AFO", AFI_DC: "JPSU-650W-DC-AFI",
}


def load_device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def load_component(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


def number(pid):
    return int(pid.split("-")[1])


def cages(dev, *names):
    return [p for p in placements(dev, "front") if ref_name(p["ref"]) in names]


def printed(dev):
    return {s["text"] for s in dev["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_24(name):
    ch = load_device(name)["chassis"]
    want = ENVELOPE_IN[name]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(want["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(want["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(want["d"] * INCH, abs=0.1)
    assert ch["weight-kg"] == pytest.approx(want["kg"], abs=0.01)


@pytest.mark.parametrize("name", DEVICES)
def test_the_faces_are_sized_from_the_envelope(name):
    d = load_device(name)
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_is_the_body_and_not_the_rack_face(name):
    """The mounting brackets are not in Table 24's 17.36 in, so the body is what is drawn."""
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


@pytest.mark.parametrize("name", DEVICES)
def test_the_names_are_as_printed_and_the_portfolio_is_the_family(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX5110"}
    assert d["chassis"]["airflow"] == "front-to-back"
    assert d["chassis"]["power"] == "ac"


# --- the ports, per face -----------------------------------------------------

def test_48s_has_48_sfp_plus_and_4_qsfp28_cages_numbered_as_printed():
    d = load_device("qfx5110-48s")
    sfp, qsfp = cages(d, "sfp-ganged"), cages(d, "qsfp-ganged")
    assert sorted(number(p["id"]) for p in sfp) == list(range(0, 48))
    assert sorted(number(p["id"]) for p in qsfp) == list(range(48, 52))
    assert {str(n) for n in range(52)} <= printed(d)
    assert d["groups"]["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}


def test_32q_has_32_qsfp_cages_numbered_as_printed_28_plus_and_4_qsfp28():
    d = load_device("qfx5110-32q")
    qsfp = cages(d, "qsfp-ganged")
    assert sorted(number(p["id"]) for p in qsfp) == list(range(0, 32))
    assert not cages(d, "sfp-ganged")
    assert {str(n) for n in range(32)} <= printed(d)
    by_id = {p["id"]: p for p in qsfp}
    assert {by_id[f"port-{n}"]["group"] for n in range(28)} == {"qsfp-plus"}
    assert {by_id[f"port-{n}"]["group"] for n in range(28, 32)} == {"qsfp28"}
    assert d["groups"]["qsfp-plus"]["attrs"] == {"media": "qsfp", "speed": "40g"}
    assert d["groups"]["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}


def test_32q_prints_the_100g_legend_beside_ports_28_to_31():
    silk = load_device("qfx5110-32q")["views"]["front"]["silkscreen"]
    box = [s for s in silk if s.get("text") == "100G"]
    assert len(box) == 1 and set(box[0]["for"]) == {"port-28", "port-29", "port-30", "port-31"}


@pytest.mark.parametrize("name", DEVICES)
def test_the_groups_are_traffic_ports(name):
    for g in load_device(name)["groups"].values():
        if g.get("attrs", {}).get("media") in ("sfp-plus", "qsfp", "qsfp28"):
            assert g["role"] == "traffic"


@pytest.mark.parametrize("name", DEVICES)
def test_the_rows_are_two_upper_even_lower_odd(name):
    d = load_device(name)
    y = {number(p["id"]): p["at"][1] for p in cages(d, "sfp-ganged", "qsfp-ganged")}
    pairs = [(n, n + 1) for n in sorted(y) if n % 2 == 0]
    assert len(pairs) == len(y) // 2
    assert all(y[a] < y[b] for a, b in pairs)


def test_48s_access_ports_stand_in_four_blocks_of_six_columns_with_the_qsfp28_block_to_the_right():
    d = load_device("qfx5110-48s")
    xs = sorted({p["at"][0] for p in cages(d, "sfp-ganged")})
    assert len(xs) == 24
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if abs(s - 14.25) < 0.02]) == 20
    assert len([s for s in steps if s > 14.3]) == 3, "three gutters between four blocks"
    assert min(p["at"][0] for p in cages(d, "qsfp-ganged")) > max(xs)


def test_32q_ports_stand_in_four_blocks_of_four_columns_on_the_registry_pitch():
    xs = sorted({p["at"][0] for p in cages(load_device("qfx5110-32q"), "qsfp-ganged")})
    assert len(xs) == 16
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if abs(s - 19.0) < 0.02]) == 12
    assert len([s for s in steps if s > 19.1]) == 3, "three gutters between four blocks"


def lamps(dev):
    return {p["id"]: p for p in placements(dev, "front")
            if ref_name(p["ref"]) in ("led-dot", "led-arrow-sm")}


def test_48s_lamps_follow_tables_5_to_7_two_an_sfp_plus_port_and_four_a_qsfp28_port():
    ids = lamps(load_device("qfx5110-48s"))
    for n in range(48):
        assert f"led-port-{n}" in ids and f"led-port-{n}-status" in ids
    for n in range(48, 52):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= set(ids)
    assert len(ids) == 96 + 16
    for lamp in ids.values():
        assert lamp["for"].startswith("port-")


def test_32q_lamps_follow_table_8_four_a_port():
    ids = lamps(load_device("qfx5110-32q"))
    for n in range(32):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= set(ids)
    assert len(ids) == 128
    for lamp in ids.values():
        assert lamp["for"].startswith("port-")


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_carries_the_esd_terminal_the_grandmaster_jack_and_the_two_clock_outputs(name):
    """Figures 14 and 15: callout 1 the ESD terminal, 2 the RJ-45 grandmaster clock jack, the two coaxial outputs."""
    by_id = {p["id"]: p for p in placements(load_device(name), "front")}
    assert ref_name(by_id["esd-front-jack"]["ref"]) == "esd-jack"
    assert by_id["esd-front-jack"]["group"] == "esd"
    assert ref_name(by_id["gm"]["ref"]) == "rj45"
    assert by_id["gm"]["attrs"]["role"] == "timing"
    for pid, signal in (("out-pps", "1PPS"), ("out-10m", "10 MHz")):
        assert ref_name(by_id[pid]["ref"]) == "sma"
        assert by_id[pid]["attrs"]["signal"] == signal


def test_the_photograph_not_the_drawing_orders_the_clock_outputs_on_the_48s():
    """The 48S photograph prints PPS OUT under the left jack; the guide's figure 14 letters them the other way."""
    by_id = {p["id"]: p for p in placements(load_device("qfx5110-48s"), "front")}
    assert by_id["out-pps"]["at"][0] < by_id["out-10m"]["at"][0]


def test_the_32q_has_10m_out_left_of_pps_out_as_figure_15_and_the_photograph_print_it():
    by_id = {p["id"]: p for p in placements(load_device("qfx5110-32q"), "front")}
    assert by_id["out-10m"]["at"][0] < by_id["out-pps"]["at"][0]


# --- the rear ----------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_the_four_chassis_lamps_the_console_usb_reset_and_three_management_ports(name):
    """Figure 17: status LEDs, the second C0 (SFP), C1 (SFP, em1), console, C0 (RJ-45, em0), reset, USB."""
    d = load_device(name)
    by_id = {p["id"]: p for p in placements(d, "rear")}
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn", "console", "usb",
            "mgmt-c0", "mgmt-c1", "mgmt-c0-sfp"} <= set(by_id)
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert by_id["mgmt-c0"]["attrs"]["speed"] == "1g"
    for pid in ("mgmt-c1", "mgmt-c0-sfp"):
        assert ref_name(by_id[pid]["ref"]) == "sfp-ganged"
        assert by_id[pid]["attrs"]["role"] == "mgmt"


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_says_the_model_and_leaves_the_logo_to_a_zone(name):
    rear = load_device(name)["views"]["rear"]
    texts = [s.get("text", "") for s in rear["silkscreen"]]
    assert "QFX5110" in texts and "RUNNING JUNOS" in texts
    assert not [t for t in texts if "JUNIPER" in t.upper() or "NETWORKS" in t.upper()]
    assert [r["id"] for r in rear["regions"]] == ["logo-zone"]


@pytest.mark.parametrize("name", DEVICES)
def test_five_fan_slots_and_two_supply_slots_numbered_as_the_guide_numbers_them(name):
    """Fan slots 0 to 4 left to right (Cooling System); two supplies at the right."""
    b = {x["id"]: x for x in bays(load_device(name), "rear")}
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{n}" for n in range(5)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] < b["psu-1"]["at"][0]
    assert b["psu-0"]["at"][0] > b["fan-4"]["at"][0]


@pytest.mark.parametrize("name", DEVICES)
def test_the_fan_slots_are_numbered_on_the_chassis(name):
    silk = {s["for"]: s["text"] for s in load_device(name)["views"]["rear"]["silkscreen"]
            if s.get("text", "").isdigit() and str(s.get("for", "")).startswith(("fan-", "psu-"))}
    assert silk == {f"fan-{n}": str(n) for n in range(5)} | {"psu-0": "0", "psu-1": "1"}


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_variant_is_an_orderable_configuration_with_its_part_number(name):
    cfgs = load_device(name)["configurations"]
    assert set(cfgs) == set(VARIANTS[name])
    for cid, (part, *_rest) in VARIANTS[name].items():
        assert cfgs[cid]["kind"] == "orderable"
        assert set(cfgs[cid]["part-numbers"]) == {part}


@pytest.mark.parametrize("name", DEVICES)
def test_the_default_is_ac_front_to_back(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def seated(dev, cid):
    """bay id -> component name, as the configuration leaves it (default where unstated); '' is an open bay."""
    cfg = dev["configurations"][cid]
    out = {}
    for b in bays(dev, "rear"):
        ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
        out[b["id"]] = ref_name(ref) if ref else ""
    return out


@pytest.mark.parametrize("name,cid", SEATED_CASES)
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(name, cid):
    d = load_device(name)
    _part, psu, fan, airflow, feed = VARIANTS[name][cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(5)} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == feed


def test_the_spare_32q_chassis_shows_every_bay_open():
    """Table 3: QFX5110-32Q-CHAS ships without supplies or fan modules, which are ordered separately."""
    d = load_device("qfx5110-32q")
    assert set(seated(d, "chas").values()) == {""}
    assert len(seated(d, "chas")) == 7
    assert "chas" not in load_device("qfx5110-48s")["configurations"], "Table 3 has no chassis-only 48S"


@pytest.mark.parametrize("name", DEVICES)
def test_a_bay_accepts_the_modules_the_guide_lists(name):
    for b in bays(load_device(name), "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        assert got == (set(FAN[name]) if b["id"].startswith("fan-") else PSUS), b["id"]
        assert ref_name(b["default"]) in got


@pytest.mark.parametrize("name", DEVICES)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    for b in bays(load_device(name), "rear"):
        for ref in b["accepts"]:
            c = load_component(ref_name(ref))["size"]
            assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3)
            assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3)


# --- the field-replaceable units, reused -------------------------------------

@pytest.mark.parametrize("part", sorted(PSUS))
def test_a_supply_is_the_650w_unit_the_guide_names(part):
    attrs = load_component(part)["attrs"]
    assert attrs["model"] == MODEL[part]
    assert attrs["power-output-w"] == 650


@pytest.mark.parametrize("part", ALL_FANS)
def test_a_fan_module_is_the_juniper_unit_for_this_model_and_airflow(part):
    """Table 11: QFX5110-48S-FANAFI, -48S-FANAFO, -32Q-FANAFI and -32Q-FANAFO."""
    attrs = load_component(part)["attrs"]
    assert attrs["model"] == part.upper()
    assert attrs["airflow"] == ("front-to-back" if part.endswith("afo") else "back-to-front")


@pytest.mark.parametrize("name", DEVICES)
def test_no_qfx5110_chassis_seats_the_fan_module_of_another_model(name):
    """Guide p. 44: only the replacement fan modules designed for the product number."""
    other = {f for n, fans in FAN.items() if n != name for f in fans}
    text = (DEV / name / "device.yaml").read_text()
    assert not any(f"juniper/{f}@" in text for f in other)
    assert "juniper/qfx5110-fanafo@" not in text and "juniper/qfx5110-fanafi@" not in text


@pytest.mark.parametrize("front,back", [
    (AFO_AC, AFI_AC), (AFO_DC, AFI_DC), FAN["qfx5110-48s"], FAN["qfx5110-32q"],
])
def test_the_back_to_front_unit_has_a_blue_handle_and_the_front_to_back_a_gold_one(front, back):
    """Tables 11, 13 and 18: AFO (port-to-FRU) is Juniper Gold, AFI (FRU-to-port) is Juniper Azure Blue."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    r, g, bl = (int(handle(back)[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    r, g, bl = (int(handle(front)[i:i + 2], 16) for i in (1, 3, 5))
    assert r > bl and g > bl, "gold is not blue"


def test_the_family_adds_four_fan_modules_and_the_supplies_are_reused():
    """The shared QFX5120 pair stays; each QFX5110 model has its own pair, and no supply is added."""
    names = {p.name for p in COMP.glob("qfx5110-*")}
    assert names == {"qfx5110-fanafo", "qfx5110-fanafi", *ALL_FANS}


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name,cid", CASES)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name, cid):
    part = VARIANTS[name][cid][0]
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 1.0


def test_no_other_juniper_qfx5110_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5110-*.yaml")}
    want = {v[0] for per in VARIANTS.values() for v in per.values()}
    assert got == want


@pytest.mark.parametrize("name", DEVICES)
def test_the_export_for_the_default_names_the_interfaces_by_the_printed_numbers(name):
    part = VARIANTS[name]["ac-f2b"][0]
    doc = yaml.safe_load((EXPORTS / "netbox/device-types/Juniper" / f"{part}.yaml").read_text())
    names = [i["name"] for i in doc["interfaces"]]
    n_ports = 52 if name == "qfx5110-48s" else 32
    assert sum(bool(re.fullmatch(r"port-\d+", n)) for n in names) == n_ports
