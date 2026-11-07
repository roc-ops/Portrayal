"""The Juniper QFX5100-24Q and QFX5100-96S, from the QFX5100 Switch Hardware Guide (2023-02-26).

One device per front panel. The 24Q has 24 QSFP+ cages and two expansion module bays, the 96S 96 SFP+
cages and 8 QSFP+ cages in a 2RU box, so they are two devices. Each one's power, airflow and
management-port variants are `orderable` configurations of it, because the guide shows one panel for
all of them. The 48SH and 48TH have the 48S's and the 48T's panel and are configurations of those two
devices (test_juniper_qfx5100.py), so they are not repeated here. The 24Q-AA has a double-wide module
bay and a different panel, and is not modelled.

What the guide fixes, and so what these tests hold:
  Table 3    the envelope - 1.72 x 17.36 x 20.48 in, 1RU (24Q); 3.46 x 17.36 x 22.44 in, 2RU (96S)
  Table 1    the variants and their part numbers
  Table 13   the AC supplies (650 W for the 24Q, 850 W for the 96S), their airflow and handle colour; the
             datasheet's ordering table names the DC supplies
  Table 19   the fan modules (QFX5100-FAN-* and QFX5100-96S-FAN*), their airflow and colour
  Table 4    the 24Q port lamps: four for a QSFP+ port; Tables 8 to 10 those of the 96S
  figures 11, 16, 21, 22   the ports, their count and numbering, the fan end and the management panel
  the datasheet's ordering table   QFX-EM-4Q, EX4600-EM-8F and the QFX5100-EM-BLNK blank for the 24Q's bays
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

# Table 3: height, width, depth in inches, and the rack units
ENVELOPE_IN = {
    "qfx5100-24q": {"h": 1.72, "w": 17.36, "d": 20.48, "ru": 1},
    "qfx5100-96s": {"h": 3.46, "w": 17.36, "d": 22.44, "ru": 2},
}
DEVICES = sorted(ENVELOPE_IN)

# Table 1 and the datasheet's ordering table: configuration -> (part number, supply, fan, airflow, feed)
P650 = "qfx5100-jpsu-650w"
VARIANTS = {
    "qfx5100-24q": {
        "ac-f2b": ("QFX5100-24Q-AFO", f"{P650}-ac-afo", "qfx5100-fan-afo", "front-to-back", "ac"),
        "ac-b2f": ("QFX5100-24Q-AFI", f"{P650}-ac-afi", "qfx5100-fan-afi", "back-to-front", "ac"),
        "dc-f2b": ("QFX5100-24Q-DC-AFO", f"{P650}-dc-afo", "qfx5100-fan-afo", "front-to-back", "dc"),
        "dc-b2f": ("QFX5100-24Q-DC-AFI", f"{P650}-dc-afi", "qfx5100-fan-afi", "back-to-front", "dc"),
        # the three-management-port models (Table 1)
        "ac-3mgmt-f2b": ("QFX5100-24Q-3AFO", f"{P650}-ac-afo", "qfx5100-fan-afo", "front-to-back", "ac"),
        "ac-3mgmt-b2f": ("QFX5100-24Q-3AFI", f"{P650}-ac-afi", "qfx5100-fan-afi", "back-to-front", "ac"),
        "dc-3mgmt-f2b": ("QFX5100-24Q-D-3AFO", f"{P650}-dc-afo", "qfx5100-fan-afo", "front-to-back", "dc"),
        "dc-3mgmt-b2f": ("QFX5100-24Q-D-3AFI", f"{P650}-dc-afi", "qfx5100-fan-afi", "back-to-front", "dc"),
    },
    "qfx5100-96s": {
        "ac-f2b": ("QFX5100-96S-AFO", "jpsu-850w-ac-afo", "qfx5100-96s-fanafo", "front-to-back", "ac"),
        "ac-b2f": ("QFX5100-96S-AFI", "jpsu-850w-ac-afi", "qfx5100-96s-fanafi", "back-to-front", "ac"),
        "dc-f2b": ("QFX5100-96S-DC-AFO", "qfx5200-jpsu-850w-dc-afo", "qfx5100-96s-fanafo", "front-to-back", "dc"),
        "dc-b2f": ("QFX5100-96S-DC-AFI", "qfx5200-jpsu-850w-dc-afi", "qfx5100-96s-fanafi", "back-to-front", "dc"),
    },
}
CASES = [(n, c) for n in sorted(VARIANTS) for c in VARIANTS[n]]
# Table 1: the models with three management ports (a second SFP, C0, above C1)
THREE_PORT = {"ac-3mgmt-f2b", "ac-3mgmt-b2f", "dc-3mgmt-f2b", "dc-3mgmt-b2f"}
FAN_COUNT = {"qfx5100-24q": 5, "qfx5100-96s": 3}
FANS = {
    "qfx5100-24q": {"qfx5100-fan-afo", "qfx5100-fan-afi"},
    "qfx5100-96s": {"qfx5100-96s-fanafo", "qfx5100-96s-fanafi"},
}
PSUS = {
    "qfx5100-24q": {f"{P650}-ac-afo", f"{P650}-ac-afi", f"{P650}-dc-afo", f"{P650}-dc-afi"},
    "qfx5100-96s": {"jpsu-850w-ac-afo", "jpsu-850w-ac-afi", "qfx5200-jpsu-850w-dc-afo", "qfx5200-jpsu-850w-dc-afi"},
}
NEW_FANS = sorted(FANS["qfx5100-96s"])
MODEL = {  # the part number the guide and the datasheet print for the new components
    "qfx5100-96s-fanafo": "QFX5100-96S-FANAFO", "qfx5100-96s-fanafi": "QFX5100-96S-FANAFI",
}
# the datasheet's ordering table: the modules of the 24Q's bays and the part each part number is filed under
MODULES = {
    "ex4600-em-4q": "QFX-EM-4Q",
    "ex4600-em-8f": "EX4600-EM-8F",
    "ex4600-em-blnk": "QFX5100-EM-BLNK",
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


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_table_3(name):
    ch = load_device(name)["chassis"]
    want = ENVELOPE_IN[name]
    assert ch["ru"] == want["ru"]
    assert ch["height"] == pytest.approx(want["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(want["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(want["d"] * INCH, abs=0.1)


def test_the_96s_is_a_2ru_box_twice_the_height_of_the_24q():
    """Table 3 gives the 96S 3.46 in and the 24Q 1.72 in; they are not one row of figures."""
    q, s = load_device("qfx5100-24q")["chassis"], load_device("qfx5100-96s")["chassis"]
    assert s["height"] == pytest.approx(2 * q["height"], abs=0.6)
    assert s["depth"] - q["depth"] == pytest.approx(1.96 * INCH, abs=0.1)


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
    """The mounting brackets are not in Table 3's 17.36 in, so the body is what is drawn."""
    assert load_device(name)["views"]["front"]["size"]["w"] < 480


@pytest.mark.parametrize("name", DEVICES)
def test_the_names_are_as_printed_and_the_portfolio_is_the_family(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == name.upper()
    assert d["portfolio"] == {"line": "QFX Series", "family": "QFX5100"}
    assert d["chassis"]["airflow"] == "front-to-back"
    assert d["chassis"]["power"] == "ac"


# --- the ports, per face -----------------------------------------------------

def cages(dev, *names):
    return [p for p in placements(dev, "front") if ref_name(p["ref"]) in names]


def lamps(dev):
    return {p["id"]: p for p in placements(dev, "front")
            if ref_name(p["ref"]) in ("led-dot", "led-arrow-sm")}


def printed(dev):
    return {s["text"] for s in dev["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}


def test_24q_has_24_qsfp_plus_cages_numbered_0_to_23():
    d = load_device("qfx5100-24q")
    qsfp = cages(d, "qsfp-ganged")
    assert sorted(number(p["id"]) for p in qsfp) == list(range(24))
    assert len(cages(d, "qsfp-ganged", "sfp-ganged", "rj45-ganged-eth-plain")) == 24
    assert d["groups"]["qsfp-plus"]["attrs"] == {"media": "qsfp", "speed": "40g"}
    assert d["groups"]["qsfp-plus"]["role"] == "traffic"


def test_24q_prints_no_numeral_beside_its_fixed_ports():
    """The photograph prints none (the module ports' numerals resolve in it); the guide numbers 0 to 23."""
    assert not printed(load_device("qfx5100-24q"))


def test_24q_ports_stand_in_four_groups_of_three_columns_in_two_rows():
    d = load_device("qfx5100-24q")
    qsfp = cages(d, "qsfp-ganged")
    xs = sorted({p["at"][0] for p in qsfp})
    assert len(xs) == 12
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if abs(s - 19.25) < 0.02]) == 8
    assert len([s for s in steps if s > 19.3]) == 3, "three gutters between four groups"
    y = {number(p["id"]): p["at"][1] for p in qsfp}
    assert all(y[2 * c] < y[2 * c + 1] for c in range(12)), "the upper port of a column is the even one"
    # the lower cage is turned 180, the library's stack convention
    assert {p.get("rotate", 0) for p in qsfp if number(p["id"]) % 2 == 0} == {0}
    assert {p.get("rotate", 0) for p in qsfp if number(p["id"]) % 2 == 1} == {180}


def test_24q_lamps_follow_table_4_four_a_qsfp_plus_port():
    ids = lamps(load_device("qfx5100-24q"))
    for n in range(24):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= set(ids)
    assert len(ids) == 24 * 4
    for lamp in ids.values():
        assert lamp["for"].startswith("port-")


def test_24q_bays_are_two_expansion_bays_at_the_right_of_the_port_panel():
    """Figure 11, callout 3: expansion module bays with cover panels (2)."""
    d = load_device("qfx5100-24q")
    b = bays(d, "front")
    assert [x["id"] for x in b] == ["em-0", "em-1"]
    assert b[0]["at"][0] < b[1]["at"][0]
    assert b[0]["at"][0] > max(p["at"][0] for p in cages(d, "qsfp-ganged"))
    assert d["groups"]["expansion"]["term"] == "Bay"


def test_96s_has_96_sfp_plus_and_8_qsfp_plus_cages_numbered_as_printed():
    d = load_device("qfx5100-96s")
    sfp, qsfp = cages(d, "sfp-ganged"), cages(d, "qsfp-ganged")
    assert sorted(number(p["id"]) for p in sfp) == list(range(0, 96))
    assert sorted(number(p["id"]) for p in qsfp) == list(range(96, 104))
    assert not cages(d, "rj45-ganged-eth-plain")
    assert {str(n) for n in range(104)} <= printed(d)
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert d["groups"]["qsfp-plus"]["attrs"] == {"media": "qsfp", "speed": "40g"}


def test_96s_ports_stand_in_two_bands_of_24_columns_in_blocks_of_six_upper_even():
    d = load_device("qfx5100-96s")
    sfp = cages(d, "sfp-ganged")
    xs = sorted({p["at"][0] for p in sfp})
    assert len(xs) == 24
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert len([s for s in steps if abs(s - 14.25) < 0.02]) == 20
    assert len([s for s in steps if s > 14.3]) == 3, "three gutters between four blocks"
    ys = sorted({p["at"][1] for p in sfp})
    assert len(ys) == 4, "two rows in each of two bands"
    y = {number(p["id"]): p["at"][1] for p in sfp}
    assert all(y[2 * c] < y[2 * c + 1] for c in range(48)), "the upper port of a column is the even one"
    assert max(p["at"][0] for p in sfp) < min(p["at"][0] for p in cages(d, "qsfp-ganged"))


def test_96s_qsfp_plus_ports_run_down_two_columns_in_two_pairs():
    d = load_device("qfx5100-96s")
    q = {number(p["id"]): p["at"] for p in cages(d, "qsfp-ganged")}
    assert q[96][0] == q[97][0] == q[100][0] == q[101][0] < q[98][0] == q[99][0] == q[102][0] == q[103][0]
    assert q[96][1] < q[97][1] < q[100][1] < q[101][1]
    assert q[98][1] == q[96][1] and q[99][1] == q[97][1]


def test_96s_lamps_two_an_sfp_plus_port_and_four_a_qsfp_plus_port():
    ids = lamps(load_device("qfx5100-96s"))
    for n in range(96):
        assert f"led-port-{n}" in ids and f"led-port-{n}-status" in ids
    for n in range(96, 104):
        assert f"led-port-{n}" in ids
        assert {f"led-port-{n}-lane-{k}" for k in (2, 3, 4)} <= set(ids)
    assert len([i for i in ids if i.startswith("led-port-")]) == 96 * 2 + 8 * 4
    for lamp in ids.values():
        if lamp["id"].startswith("led-port-"):
            assert lamp["for"].startswith("port-")


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_carries_the_esd_terminal(name):
    """Figures 11 and 16, callout 1."""
    by_id = {p["id"]: p for p in placements(load_device(name), "front")}
    assert ref_name(by_id["esd-front-jack"]["ref"]) == "esd-jack"
    assert by_id["esd-front-jack"]["group"] == "esd"


# --- the rear ----------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_has_the_four_chassis_lamps_the_console_usb_reset_and_management(name):
    """Figures 22 and 23: status LEDs, em1 SFP (C1), reset, em0 RJ-45 (C0), console, USB."""
    d = load_device(name)
    by_id = {p["id"]: p for p in placements(d, "rear")}
    assert {"led-alm", "led-sys", "led-mst", "led-id", "reset-btn", "console", "usb",
            "mgmt-c0", "mgmt-c1"} <= set(by_id)
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged"
    assert by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert by_id["mgmt-c0"]["attrs"]["speed"] == "1g"
    assert by_id["mgmt-c1"]["attrs"]["role"] == "mgmt"
    assert "mgmt-c0-sfp" not in by_id


def test_the_96s_management_panel_sits_in_the_lower_half_of_the_2ru_face():
    """Figure 21: the panel is the 1U panel, placed against the bottom edge of the 88 mm face."""
    d = load_device("qfx5100-96s")
    h = d["chassis"]["height"]
    assert all(p["at"][1] > h / 2 for p in placements(d, "rear") if p["id"] in ("led-alm", "mgmt-c1", "usb"))


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_says_the_model_and_leaves_the_logo_to_a_zone(name):
    d = load_device(name)
    rear = d["views"]["rear"]
    texts = [s.get("text", "") for s in rear["silkscreen"]]
    assert d["model"] in texts
    assert not [t for t in texts if "JUNIPER" in t.upper() or "NETWORKS" in t.upper()]
    assert [r["id"] for r in rear["regions"]] == ["logo-zone"]


def test_the_24q_chip_also_prints_the_operating_system_and_the_96s_does_not():
    """Figure 22 and the 24Q photograph print RUNNING JUNOS; Figures 21 and 23 print only QFX5100-96S."""
    texts = {n: [s.get("text", "") for s in load_device(n)["views"]["rear"]["silkscreen"]] for n in DEVICES}
    assert "RUNNING JUNOS" in texts["qfx5100-24q"]
    assert "RUNNING JUNOS" not in texts["qfx5100-96s"]


@pytest.mark.parametrize("name", DEVICES)
def test_fan_slots_and_two_supply_slots_numbered_as_the_guide_numbers_them(name):
    """Fan slots 0 to 4 (1U) or 0 to 2 (2U) left to right; two supplies at the right."""
    b = {x["id"]: x for x in bays(load_device(name), "rear")}
    n = FAN_COUNT[name]
    fans = sorted(i for i in b if i.startswith("fan-"))
    assert fans == [f"fan-{k}" for k in range(n)]
    assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)
    assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
    assert b["psu-0"]["at"][0] > b[f"fan-{n - 1}"]["at"][0]


def test_the_24q_supplies_stand_side_by_side_and_the_96s_supplies_one_above_the_other():
    """Figure 21 numbers the 96S supplies 1 above and 0 below."""
    q = {x["id"]: x for x in bays(load_device("qfx5100-24q"), "rear")}
    assert q["psu-0"]["at"][0] < q["psu-1"]["at"][0] and q["psu-0"]["at"][1] == q["psu-1"]["at"][1]
    s = {x["id"]: x for x in bays(load_device("qfx5100-96s"), "rear")}
    assert s["psu-0"]["at"][0] == s["psu-1"]["at"][0]
    assert s["psu-1"]["at"][1] < s["psu-0"]["at"][1]
    assert s["psu-0"]["at"][1] > load_device("qfx5100-96s")["chassis"]["height"] / 2


def test_24q_has_a_three_port_rear_panel_for_the_3afo_models_and_the_96s_has_none():
    d = load_device("qfx5100-24q")
    assert d["views"]["rear-3mgmt"]["face"] == "rear"
    assert "mgmt-c0-sfp" in {p["id"] for p in placements({"views": {"rear": d["views"]["rear-3mgmt"]}}, "rear")}
    assert "rear-3mgmt" not in load_device("qfx5100-96s")["views"]


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_variant_is_an_orderable_configuration_with_its_part_number(name):
    cfgs = load_device(name)["configurations"]
    orderable = {c for c, v in cfgs.items() if v["kind"] == "orderable"}
    assert orderable == set(VARIANTS[name])
    for cid, (part, *_rest) in VARIANTS[name].items():
        assert set(cfgs[cid]["part-numbers"]) == {part}


@pytest.mark.parametrize("name", DEVICES)
def test_the_default_is_ac_front_to_back(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def seated(dev, cid):
    """bay id -> component name, as the configuration leaves it (default where unstated)."""
    cfg = dev["configurations"][cid]
    return {b["id"]: ref_name((cfg.get("bays") or {}).get(b["id"], b.get("default")))
            for b in bays(dev, "rear")}


@pytest.mark.parametrize("name,cid", CASES)
def test_each_configuration_seats_its_supply_and_fan_module_with_matching_airflow(name, cid):
    d = load_device(name)
    _part, psu, fan, airflow, feed = VARIANTS[name][cid]
    s = seated(d, cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(FAN_COUNT[name])} == {fan}
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == feed


@pytest.mark.parametrize("cid", sorted(VARIANTS["qfx5100-24q"]))
def test_24q_variants_wear_the_management_panel_table_1_gives_them(cid):
    """Two ports for the -AFO, -AFI and DC models; three (a second SFP, C0, above C1) for -3AFO, -3AFI, -D-3AFO, -D-3AFI."""
    d = load_device("qfx5100-24q")
    rear = d["configurations"][cid].get("views", {}).get("rear", "rear")
    ids = {p["id"] for p in placements({"views": {"rear": d["views"][rear]}}, "rear")}
    assert ("mgmt-c0-sfp" in ids) == (cid in THREE_PORT)
    assert {"mgmt-c0", "mgmt-c1", "console", "usb"} <= ids


def test_the_two_rear_panels_of_the_24q_seat_the_same_modules():
    d = load_device("qfx5100-24q")
    a = {x["id"] for x in bays(d, "rear")}
    b = {x["id"] for x in d["views"]["rear-3mgmt"]["components"]["bays"]}
    assert a == b


@pytest.mark.parametrize("name", DEVICES)
def test_a_rear_bay_accepts_the_modules_the_guide_lists(name):
    for b in bays(load_device(name), "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        assert got == (FANS[name] if b["id"].startswith("fan-") else PSUS[name]), b["id"]
        assert ref_name(b["default"]) in got


@pytest.mark.parametrize("name", DEVICES)
def test_bays_reserve_one_size_for_each_module_they_accept(name):
    d = load_device(name)
    for view, bs in (("rear", bays(d, "rear")), ("front", bays(d, "front"))):
        for b in bs:
            for ref in b["accepts"]:
                ns = ref.split("/")[0]
                c = yaml.safe_load((ROOT / "library/components" / ns / ref_name(ref) / "v1" / "contract.yaml").read_text())["size"]
                assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3), (view, b["id"], ref)
                assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3), (view, b["id"], ref)


# --- the expansion bays of the 24Q -------------------------------------------

def test_each_24q_bay_accepts_the_modules_the_guide_lists_and_ships_with_the_cover_panel():
    """Figures 6 and 7 and the datasheet: QFX-EM-4Q, EX4600-EM-8F and the QFX5100-EM-BLNK blank."""
    for b in bays(load_device("qfx5100-24q"), "front"):
        assert {ref_name(r) for r in b["accepts"]} == set(MODULES)
        assert ref_name(b["default"]) == "ex4600-em-blnk"


@pytest.mark.parametrize("module,part", sorted(MODULES.items()))
def test_the_modules_are_the_libraries_own_and_carry_the_part_number_the_datasheet_prints(module, part):
    c = load_component(module)
    assert [v["part"] for v in c["part-numbers"].values()] == [part]


def test_the_em_4q_module_description_says_it_is_the_one_the_qfx5100_takes():
    assert "QFX5100" in " ".join(load_component("ex4600-em-4q")["description"].split())


def test_the_pfa_module_is_not_modelled_because_only_the_24q_aa_takes_it():
    """Section on the 24Q-AA: the double-wide QFX-PFA-4Q is for the -AA only, which has its own panel."""
    assert not (DEV / "qfx5100-24q-aa").exists()
    assert not any("pfa" in p.name for p in COMP.iterdir())
    for b in bays(load_device("qfx5100-24q"), "front"):
        assert not any("pfa" in r for r in b["accepts"])


@pytest.mark.parametrize("cid,module", [("em-4q", "ex4600-em-4q"), ("em-8f", "ex4600-em-8f")])
def test_an_illustration_seats_a_module_in_each_bay_and_is_not_an_order_code(cid, module):
    cfg = load_device("qfx5100-24q")["configurations"][cid]
    assert cfg["kind"] == "example"
    assert "part-numbers" not in cfg
    assert {ref_name(v) for v in cfg["bays"].values()} == {module}
    assert set(cfg["bays"]) == {"em-0", "em-1"}


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("part", NEW_FANS)
def test_a_96s_fan_is_named_for_its_family_and_carries_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and part.startswith("qfx5100-96s-")
    assert c["attrs"]["model"] == MODEL[part]
    assert c["kind"] == "module"
    assert c["class"] == "fan"


@pytest.mark.parametrize("part", NEW_FANS)
def test_a_96s_fan_is_described_as_the_unit_and_names_the_model_that_takes_it(part):
    text = " ".join(load_component(part)["description"].split())
    assert "hot-removable" in text
    assert "QFX5100-96S" in text
    assert load_component(part)["attrs"]["power-absent"] == "not-published"


def test_the_96s_fan_is_a_different_part_from_the_1ru_fan_and_about_twice_its_height():
    one, two = load_component("qfx5100-fan-afo")["size"], load_component("qfx5100-96s-fanafo")["size"]
    assert two["h"] == pytest.approx(2 * one["h"], abs=0.5)
    assert two["w"] > 1.9 * one["w"]


def test_the_96s_back_to_front_fan_has_a_blue_handle_and_the_front_to_back_a_gold_one():
    """Table 19: AFO (port-to-FRU) is Juniper Gold, AFI (FRU-to-port) is Juniper Azure Blue."""
    def handle(part):
        feats = load_component(part)["relief"]["features"]
        return next(f for f in feats if f["node"] in ("latch", "handle"))["color"]
    f, b = handle("qfx5100-96s-fanafo"), handle("qfx5100-96s-fanafi")
    assert f.lower() == "#e8731f"
    r, g, bl = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    assert bl > r and bl > g, "blue is the dominant channel"
    assert load_component("qfx5100-96s-fanafo")["attrs"]["airflow"] == "front-to-back"
    assert load_component("qfx5100-96s-fanafi")["attrs"]["airflow"] == "back-to-front"


@pytest.mark.parametrize("part", NEW_FANS)
def test_a_96s_fan_prints_its_direction_as_the_guide_labels_it(part):
    """Table 19: AIR OUT on the gold module, AIR IN on the blue one."""
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    word = "OUT" if part.endswith("afo") else "IN"
    assert f">{word}</text>" in svg and ">AIR</text>" in svg


@pytest.mark.parametrize("part", sorted(PSUS["qfx5100-96s"]))
def test_the_96s_supplies_are_the_850_w_units_reused_by_part_number(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 850
    assert attrs["model"] == "JPSU-850W-" + part.split("850w-")[1].upper()
    assert attrs["airflow"] == ("front-to-back" if part.endswith("afo") else "back-to-front")


@pytest.mark.parametrize("part", sorted(PSUS["qfx5100-24q"]))
def test_the_24q_supplies_are_the_650_w_units_of_the_48s_reused_by_part_number(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 650
    assert attrs["model"] == "JPSU-650W-" + part.split("650w-")[1].upper()


def test_no_component_added_here_copies_a_part_the_library_already_holds_under_the_same_number():
    """Reuse first: the 24Q adds no component, and the 96S adds only the two fan modules."""
    added = {p.name for p in COMP.iterdir() if p.name.startswith("qfx5100-96s")}
    assert added == set(NEW_FANS)


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
        assert doc["u_height"] == float(ENVELOPE_IN[name]["ru"])


def test_the_export_holds_the_orderable_parts_of_each_device_and_no_illustration():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5100-24Q*.yaml")}
    assert got == {v[0] for v in VARIANTS["qfx5100-24q"].values()}
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("QFX5100-96S*.yaml")}
    assert got == {v[0] for v in VARIANTS["qfx5100-96s"].values()}
