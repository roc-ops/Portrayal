"""The Juniper EX4550-32F, EX4550-32T and EX4500-40F, from their hardware guides.

One device per front panel. The EX4550 guide (published 2020-12-15) shows one front panel for the five
32F models of its Table 4 and one for the four 32T models, so each is an `orderable` configuration of
`juniper/ex4550-32f` or `juniper/ex4550-32t`. The EX4500 guide (modified 2017-10-18) shows one front
panel for the eight models of its Table 3, so each is a configuration of `juniper/ex4500-40f`.

What the guides fix, and so what these tests hold:
  EX4550 Table 6    the envelope - 1.72 x 17.35 x 18.50 in, 1RU
  EX4550 Table 4    the models: supply, fan modules and airflow, and the -S that ships without them
  EX4550 Table 17   the fan modules EX4550-FAN-AFI (AIR IN) and EX4550-FAN-AFO (AIR OUT)
  EX4550 Table 20   the supplies JPSU-650W-AC-AFI and -AFO; Table 24 the DC pair
  EX4550 Figures 4 to 6   32 ports in four blocks of four stacked columns, two module slots, three fans
  EX4500 Table 5    the envelope - 3.5 x 17.25 x 21.1 in, 2RU
  EX4500 Table 3    the eight models, their airflow, supply and rear module
  EX4500 Figure 4   40 SFP+ ports in ten blocks of two stacked columns, two uplink slots, console, MGMT, USB
  EX4500 Figure 6   two supplies, a rear module strip and one fan tray
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"
INCH = 25.4

# device -> (width, height, depth in inches, rack units): EX4550 Table 6, EX4500 Table 5
ENVELOPE = {
    "ex4550-32f": (17.35, 1.72, 18.50, 1),
    "ex4550-32t": (17.35, 1.72, 18.50, 1),
    "ex4500-40f": (17.25, 3.5, 21.1, 2),
}
MODELS = {"ex4550-32f": "EX4550-32F", "ex4550-32t": "EX4550-32T", "ex4500-40f": "EX4500-40F"}
FAMILY = {"ex4550-32f": "EX4550", "ex4550-32t": "EX4550", "ex4500-40f": "EX4500"}

# configuration -> (part number, supply, fan unit, airflow). The supplies are the JPSU-650W part numbers
# the library already holds for the EX4600, reused as they are; the fan modules are new.
F_VARIANTS = {
    "ac-f2b": ("EX4550-32F-AFO", "ex4600-jpsu-650-ac-afo", "ex4550-fan-afo", "front-to-back"),
    "ac-b2f": ("EX4550-32F-AFI", "ex4600-jpsu-650-ac-afi", "ex4550-fan-afi", "back-to-front"),
    "dc-f2b": ("EX4550-32F-DC-AFO", "ex4600-jpsu-650-dc-afo", "ex4550-fan-afo", "front-to-back"),
    "dc-b2f": ("EX4550-32F-DC-AFI", "ex4600-jpsu-650-dc-afi", "ex4550-fan-afi", "back-to-front"),
}
T_VARIANTS = {
    "ac-f2b": ("EX4550-32T-AFO", "ex4600-jpsu-650-ac-afo", "ex4550-fan-afo", "front-to-back"),
    "ac-b2f": ("EX4550-32T-AFI", "ex4600-jpsu-650-ac-afi", "ex4550-fan-afi", "back-to-front"),
    "dc-f2b": ("EX4550-32T-DC-AFO", "ex4600-jpsu-650-dc-afo", "ex4550-fan-afo", "front-to-back"),
    "dc-b2f": ("EX4550-32T-DC-AFI", "ex4600-jpsu-650-dc-afi", "ex4550-fan-afi", "back-to-front"),
}
S_SPARE = ("s", "EX4550-32F-S")
# EX4500 Table 3: configuration -> (model, supply, fan tray, rear module, airflow)
E_VARIANTS = {
    "fb": ("EX4500-40F-FB", "ex4500-psu-ac-fb", "ex4500-fan-tray-fb", "ex4500-lb", "front-to-back"),
    "bf": ("EX4500-40F-BF", "ex4500-psu-ac-bf", "ex4500-fan-tray-bf", "ex4500-lb", "back-to-front"),
    "fb-c": ("EX4500-40F-FB-C", "ex4500-psu-ac-fb", "ex4500-fan-tray-fb", "ex4500-lb", "front-to-back"),
    "bf-c": ("EX4500-40F-BF-C", "ex4500-psu-ac-bf", "ex4500-fan-tray-bf", "ex4500-lb", "back-to-front"),
    "dc-c": ("EX4500-40F-DC-C", "ex4500-psu-dc-fb", "ex4500-fan-tray-fb", "ex4500-lb", "front-to-back"),
    "vc1-fb": ("EX4500-40F-VC1-FB", "ex4500-psu-ac-fb", "ex4500-fan-tray-fb", "ex4500-vc1", "front-to-back"),
    "vc1-bf": ("EX4500-40F-VC1-BF", "ex4500-psu-ac-bf", "ex4500-fan-tray-bf", "ex4500-vc1", "back-to-front"),
    "vc1-dc": ("EX4500-40F-VC1-DC", "ex4500-psu-dc-fb", "ex4500-fan-tray-fb", "ex4500-vc1", "front-to-back"),
}
SUPPLIES_4550 = {"ex4600-jpsu-650-ac-afo", "ex4600-jpsu-650-ac-afi", "ex4600-jpsu-650-dc-afo", "ex4600-jpsu-650-dc-afi"}
FANS_4550 = {"ex4550-fan-afo", "ex4550-fan-afi"}
PART_NUMBER = {
    "ex4550-fan-afo": "EX4550-FAN-AFO", "ex4550-fan-afi": "EX4550-FAN-AFI",
    "ex4600-jpsu-650-ac-afo": "JPSU-650W-AC-AFO", "ex4600-jpsu-650-ac-afi": "JPSU-650W-AC-AFI",
    "ex4600-jpsu-650-dc-afo": "JPSU-650W-DC-AFO", "ex4600-jpsu-650-dc-afi": "JPSU-650W-DC-AFI",
}
NEW_4550_COMPONENTS = {"ex4550-fan-afo", "ex4550-fan-afi", "ex4550-psu-cover", "ex4550-em-cover"}
NEW_4500_COMPONENTS = {"ex4500-psu-ac-fb", "ex4500-psu-ac-bf", "ex4500-psu-dc-fb", "ex4500-psu-cover",
                       "ex4500-fan-tray-fb", "ex4500-fan-tray-bf", "ex4500-uplink-cover", "ex4500-lb",
                       "ex4500-vc1", "ex4500-vc-legend"}


def load_device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


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


def seated(dev, cid):
    """bay id -> component name, or '' for an open bay, as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for view in ("front", "rear"):
        for b in bays(dev, view):
            ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
            out[b["id"]] = ref_name(ref) if ref else ""
    return out


def provenance_text(dev):
    return " ".join(str(v.get("note", "")) for v in dev["provenance"].values())


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_the_envelope_is_the_guides_table(name):
    w, h, d, ru = ENVELOPE[name]
    ch = load_device(name)["chassis"]
    assert ch["ru"] == ru
    assert ch["width"] == pytest.approx(w * INCH, abs=0.1)
    assert ch["height"] == pytest.approx(h * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(d * INCH, abs=0.1)


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_the_faces_are_sized_from_the_envelope(name):
    d = load_device(name)
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}
    assert ch["width"] < 480, "the body between the brackets, not the 19 in rack face"


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_the_device_is_named_as_the_guide_prints_it(name):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == MODELS[name]
    assert d["portfolio"] == {"line": "EX Series", "family": FAMILY[name]}


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_no_logo_is_drawn_and_a_zone_is_reserved(name):
    d = load_device(name)
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"]["regions"])
    for view in ("front", "rear"):
        words = " ".join(s.get("text", "") for s in d["views"][view].get("silkscreen") or []).upper()
        assert "JUNIPER" not in words and "NETWORKS" not in words and "JUNOS" not in words


# --- the ports, per face ------------------------------------------------------

def cages(dev, name):
    return [p for p in placements(dev, "front") if ref_name(p["ref"]) == name]


def test_the_32f_has_32_sfp_plus_cages_numbered_0_to_31_in_four_blocks_of_four_columns():
    d = load_device("ex4550-32f")
    c = cages(d, "sfp-ganged")
    assert sorted(number(p["id"]) for p in c) == list(range(32))
    by = {number(p["id"]): p["at"] for p in c}
    assert all(by[2 * k][0] == by[2 * k + 1][0] and by[2 * k][1] < by[2 * k + 1][1] for k in range(16))
    xs = [by[2 * k][0] for k in range(16)]
    gaps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert all(g == 14.25 for i, g in enumerate(gaps) if i % 4 != 3), "the registry's pitch inside a block"
    assert all(g > 14.25 + 5 for i, g in enumerate(gaps) if i % 4 == 3), "a gutter between blocks"
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(32)} <= printed


def test_the_32t_has_32_jacks_numbered_0_to_31_in_four_blocks_of_four_columns():
    d = load_device("ex4550-32t")
    c = cages(d, "rj45-ganged-eth-plain")
    assert sorted(number(p["id"]) for p in c) == list(range(32))
    by = {number(p["id"]): p["at"] for p in c}
    assert all(by[2 * k][0] == by[2 * k + 1][0] and by[2 * k][1] < by[2 * k + 1][1] for k in range(16))
    assert all(p.get("rotate") == 180 for p in c if number(p["id"]) % 2 == 0), "upper row turned 180"
    assert not any(p.get("rotate") for p in c if number(p["id"]) % 2 == 1)
    xs = [by[2 * k][0] for k in range(16)]
    assert len({round(b - a, 2) for i, (a, b) in enumerate(zip(xs, xs[1:])) if i % 4 != 3}) == 1
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(32)} <= printed


def test_the_4500_has_40_sfp_plus_cages_numbered_0_to_39_in_ten_blocks_of_two_columns():
    d = load_device("ex4500-40f")
    c = cages(d, "sfp-ganged")
    assert sorted(number(p["id"]) for p in c) == list(range(40))
    by = {number(p["id"]): p["at"] for p in c}
    assert all(by[2 * k][0] == by[2 * k + 1][0] and by[2 * k][1] < by[2 * k + 1][1] for k in range(20))
    xs = [by[2 * k][0] for k in range(20)]
    gaps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert all(g == 14.25 for i, g in enumerate(gaps) if i % 2 == 0)
    assert all(g > 14.25 + 5 for i, g in enumerate(gaps) if i % 2 == 1)
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text", "").isdigit()}
    assert {str(n) for n in range(40)} <= printed


def test_the_stacked_cages_follow_the_library_convention_upper_upright_lower_turned():
    for name in ("ex4550-32f", "ex4500-40f"):
        for p in cages(load_device(name), "sfp-ganged"):
            assert bool(p.get("rotate")) == (number(p["id"]) % 2 == 1), (name, p["id"])


@pytest.mark.parametrize("name,media,speed", [("ex4550-32f", "sfp-plus", "10g"), ("ex4550-32t", "rj45", "10g"),
                                              ("ex4500-40f", "sfp-plus", "10g")])
def test_the_port_group_says_what_the_ports_are(name, media, speed):
    d = load_device(name)
    first = cages(d, "sfp-ganged" if media == "sfp-plus" else "rj45-ganged-eth-plain")[0]
    g = d["groups"][first["group"]]
    assert g["attrs"] == {"media": media, "speed": speed}
    assert g["role"] == "traffic"


def lamps(dev):
    return {p["id"]: p for p in placements(dev, "front") if ref_name(p["ref"]) == "led-arrow-sm"}


def test_the_lamps_of_the_32f_are_two_triangles_per_port_pointing_at_it():
    """Figure 4 and Tables 14 and 15: a link and activity lamp and a status lamp for each SFP+ port."""
    ls = lamps(load_device("ex4550-32f"))
    for n in range(32):
        for lid in (f"led-port-{n}", f"led-port-{n}-status"):
            assert ls[lid]["for"] == f"port-{n}"
            assert ls[lid]["skin"] == ("up" if n % 2 == 0 else "down")
    assert len(ls) == 64


def test_the_lamps_of_the_32t_are_one_triangle_per_port_for_link_and_activity():
    """Figure 5 and Table 14: a 10GBASE-T port has a link and activity lamp and no status lamp."""
    ls = lamps(load_device("ex4550-32t"))
    assert sorted(ls) == sorted(f"led-port-{n}" for n in range(32))
    assert all(ls[f"led-port-{n}"]["skin"] == ("up" if n % 2 == 0 else "down") for n in range(32))


def test_the_lamps_of_the_4500_are_four_triangles_per_column():
    """Figure 16 and Tables 13 and 14: link and activity and status lamps for each of 40 ports."""
    ls = lamps(load_device("ex4500-40f"))
    assert len(ls) == 80
    for n in range(40):
        assert ls[f"led-port-{n}"]["for"] == ls[f"led-port-{n}-status"]["for"] == f"port-{n}"


@pytest.mark.parametrize("name", ["ex4550-32f", "ex4550-32t"])
def test_the_ex4550_front_carries_the_lcd_the_chassis_lamps_and_the_management_cluster(name):
    d = load_device(name)
    by_id = {p["id"]: p for p in placements(d, "front")}
    assert {"led-alm", "led-sys", "led-mst", "btn-menu", "btn-enter"} <= set(by_id)
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-eth"
    assert ref_name(by_id["console"]["ref"]) == "rj45" and by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert ref_name(by_id["console-mini"]["ref"]) == "ex4300-console-usb-mini"
    assert any(x["id"] == "lcd" for x in d["views"]["front"]["panel"]["decor"])
    text = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text")}
    assert {"ALM", "SYS", "MST", "EX4550", "CON"} <= text
    assert {"M", "G", "T"} <= text, "MGMT is printed with its letters stacked"


def test_the_ex4500_front_has_a_stacked_console_and_management_pair_a_usb_port_and_an_esd_point():
    d = load_device("ex4500-40f")
    by_id = {p["id"]: p for p in placements(d, "front")}
    assert ref_name(by_id["console"]["ref"]) == "rj45-ganged" and by_id["console"]["attrs"]["role"] == "console"
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-ganged-eth"
    assert by_id["console"]["at"][1] < by_id["mgmt"]["at"][1], "CON above MGMT"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    assert ref_name(by_id["esd-front-jack"]["ref"]) == "esd-jack"
    assert {"led-alm", "led-sys", "led-mst", "btn-menu", "btn-enter"} <= set(by_id)
    text = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text")}
    assert {"ALM", "SYS", "MST", "EX4500", "CON", "MGMT"} <= text


# --- the module bays, and the modules the guide names --------------------------

@pytest.mark.parametrize("name", ["ex4550-32f", "ex4550-32t"])
def test_the_ex4550_has_one_module_slot_on_each_panel_with_a_cover_panel(name):
    d = load_device(name)
    front = {b["id"]: b for b in bays(d, "front")}
    rear = {b["id"]: b for b in bays(d, "rear")}
    assert list(front) == ["em-1"] and "em-2" in rear
    for b in (front["em-1"], rear["em-2"]):
        assert [ref_name(r) for r in b["accepts"]] == ["ex4550-em-cover"]
        assert ref_name(b["default"]) == "ex4550-em-cover"
    assert front["em-1"]["size"] == rear["em-2"]["size"]


@pytest.mark.parametrize("name", ["ex4550-32f", "ex4550-32t"])
def test_the_four_modules_the_guide_lists_are_named_and_not_built(name):
    """Table 3 lists four modules. This slice builds no module family, so the bays take the cover alone."""
    text = provenance_text(load_device(name))
    for module in ("EX4550-EM-8XSFP", "EX4550-EM-8XT", "EX4550-EM-2QSFP", "EX4550-VC-128G"):
        assert module in text
    assert not [p.name for p in COMP.iterdir() if p.name.startswith(("ex4550-em-", "ex4550-vc"))
                and p.name != "ex4550-em-cover"]


def test_the_4500_has_two_uplink_slots_with_cover_panels_and_a_rear_slot_for_two_modules():
    d = load_device("ex4500-40f")
    front = {b["id"]: b for b in bays(d, "front")}
    assert sorted(front) == ["uplink-1", "uplink-2"]
    assert front["uplink-1"]["at"][0] < front["uplink-2"]["at"][0]
    for b in front.values():
        assert [ref_name(r) for r in b["accepts"]] == ["ex4500-uplink-cover"]
        assert ref_name(b["default"]) == "ex4500-uplink-cover"
    rear = {b["id"]: b for b in bays(d, "rear")}
    assert {ref_name(r) for r in rear["module-3"]["accepts"]} == {"ex4500-lb", "ex4500-vc1"}
    assert "4-port SFP+" in " ".join(g["wanted"] for g in d["gaps"] if g["what"] == "uplink-modules")


# --- the supplies and the fans ------------------------------------------------

def test_the_ex4550_rear_has_two_supply_slots_and_three_fans_numbered_left_to_right():
    for name in ("ex4550-32f", "ex4550-32t"):
        b = {x["id"]: x for x in bays(load_device(name), "rear")}
        assert sorted(i for i in b if i.startswith("psu-")) == ["psu-0", "psu-1"]
        assert b["psu-0"]["at"][0] < b["psu-1"]["at"][0] < b["em-2"]["at"][0] < b["fan-1"]["at"][0]
        fans = sorted(i for i in b if i.startswith("fan-"))
        assert fans == ["fan-1", "fan-2", "fan-3"]
        assert [b[f]["at"][0] for f in fans] == sorted(b[f]["at"][0] for f in fans)


def test_the_ex4500_rear_has_two_supplies_stacked_a_module_strip_and_one_fan_tray():
    b = {x["id"]: x for x in bays(load_device("ex4500-40f"), "rear")}
    assert sorted(b) == ["fan-tray", "module-3", "psu-0", "psu-1"]
    assert b["psu-1"]["at"][1] < b["psu-0"]["at"][1], "slot 1 above slot 0"
    assert b["psu-0"]["at"][0] == b["psu-1"]["at"][0]
    assert b["module-3"]["at"][1] < b["fan-tray"]["at"][1], "the module strip is over the fan tray"


@pytest.mark.parametrize("name,variants", [("ex4550-32f", F_VARIANTS), ("ex4550-32t", T_VARIANTS)])
def test_each_ex4550_variant_is_an_orderable_configuration_with_its_part_number(name, variants):
    cfgs = load_device(name)["configurations"]
    want = {cid: v[0] for cid, v in variants.items()}
    if name == "ex4550-32f":
        want[S_SPARE[0]] = S_SPARE[1]
    assert {c for c, v in cfgs.items() if v["kind"] == "orderable"} == set(want)
    for cid, part in want.items():
        assert set(cfgs[cid]["part-numbers"]) == {part}
    assert [c for c, v in cfgs.items() if v.get("default")] == ["ac-f2b"]


def test_each_ex4500_model_is_an_orderable_configuration_with_its_model_number():
    cfgs = load_device("ex4500-40f")["configurations"]
    assert {c for c, v in cfgs.items() if v["kind"] == "orderable"} == set(E_VARIANTS)
    for cid, v in E_VARIANTS.items():
        assert set(cfgs[cid]["part-numbers"]) == {v[0]}
    assert [c for c, v in cfgs.items() if v.get("default")] == ["fb"]


@pytest.mark.parametrize("name,variants", [("ex4550-32f", F_VARIANTS), ("ex4550-32t", T_VARIANTS)])
@pytest.mark.parametrize("cid", sorted(F_VARIANTS))
def test_each_ex4550_variant_seats_one_supply_a_cover_and_three_fans_with_matching_airflow(name, variants, cid):
    d = load_device(name)
    _part, psu, fan, airflow = variants[cid]
    s = seated(d, cid)
    assert s["psu-0"] == psu and s["psu-1"] == "ex4550-psu-cover"
    assert {s["fan-1"], s["fan-2"], s["fan-3"]} == {fan}
    assert s["em-1"] == s["em-2"] == "ex4550-em-cover"
    for comp in (psu, fan):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == ("dc" if "dc" in cid else "ac")


def test_the_32f_spare_chassis_ships_with_open_power_and_fan_bays():
    """Table 4: the -S ships without a supply or fan modules; both are ordered separately."""
    s = seated(load_device("ex4550-32f"), "s")
    assert all(s[b] == "" for b in ("psu-0", "psu-1", "fan-1", "fan-2", "fan-3"))
    assert s["em-1"] == s["em-2"] == "ex4550-em-cover"


@pytest.mark.parametrize("name", ["ex4550-32f", "ex4550-32t"])
def test_an_ex4550_bay_accepts_the_units_the_guide_lists(name):
    for b in bays(load_device(name), "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        if b["id"].startswith("fan-"):
            assert got == FANS_4550, b["id"]
        elif b["id"].startswith("psu-"):
            assert got == SUPPLIES_4550 | {"ex4550-psu-cover"}, b["id"]
        assert ref_name(b["default"]) in got


@pytest.mark.parametrize("cid", sorted(E_VARIANTS))
def test_each_ex4500_model_seats_its_supply_fan_tray_and_rear_module_with_matching_airflow(cid):
    d = load_device("ex4500-40f")
    _model, psu, tray, module, airflow = E_VARIANTS[cid]
    s = seated(d, cid)
    assert s["psu-0"] == psu and s["psu-1"] == "ex4500-psu-cover"
    assert s["fan-tray"] == tray and s["module-3"] == module
    assert s["uplink-1"] == s["uplink-2"] == "ex4500-uplink-cover"
    for comp in (psu, tray):
        assert load_component(comp)["attrs"]["airflow"] == airflow
    assert d["configurations"][cid].get("airflow", d["chassis"]["airflow"]) == airflow
    assert d["configurations"][cid].get("power", d["chassis"]["power"]) == ("dc" if "dc" in cid else "ac")


def test_the_vc_legend_is_printed_on_the_vc1_models_only():
    d = load_device("ex4500-40f")
    legend = next(p for p in placements(d, "front") if p["id"] == "vc-legend")
    assert set(legend["only-in"]) == {c for c in E_VARIANTS if c.startswith("vc1-")}


def test_the_bays_reserve_one_size_for_each_unit_they_accept():
    for name in ENVELOPE:
        d = load_device(name)
        for view in ("front", "rear"):
            for b in bays(d, view):
                for ref in b["accepts"]:
                    c = load_component(ref_name(ref))["size"]
                    assert b["size"]["w"] == pytest.approx(c["w"], abs=0.6), (name, b["id"], ref)
                    assert b["size"]["h"] == pytest.approx(c["h"], abs=0.6), (name, b["id"], ref)


# --- the field-replaceable units ----------------------------------------------

def handle_finish(part):
    return load_component(part)["fields"]["handle-finish"]["default"].lower()


def rgb(hexcolour):
    return tuple(int(hexcolour[i:i + 2], 16) for i in (1, 3, 5))


@pytest.mark.parametrize("part", sorted(NEW_4550_COMPONENTS | NEW_4500_COMPONENTS))
def test_a_new_unit_is_a_component_of_its_family_and_names_what_it_is_for(part):
    c = load_component(part)
    assert c["name"] == part
    assert part.startswith(("ex4550-", "ex4500-"))
    text = " ".join(c["description"].split())
    assert "EX4550" in text or "EX4500" in text


@pytest.mark.parametrize("part", sorted(FANS_4550))
def test_an_ex4550_fan_module_is_ordered_under_its_juniper_part_number(part):
    c = load_component(part)
    assert [v["part"] for v in c["part-numbers"].values()] == [PART_NUMBER[part]]
    assert c["attrs"]["power-draw-typical-w"] == 4.8 and c["attrs"]["power-draw-max-w"] == 16.8


def test_the_supplies_are_the_ex4600_components_with_the_same_part_numbers_and_none_is_added_twice():
    for part, pn in PART_NUMBER.items():
        if part.startswith("ex4600-jpsu"):
            assert [v["part"] for v in load_component(part)["part-numbers"].values()] == [pn]
    assert not [p.name for p in COMP.iterdir() if p.name.startswith("ex4550-jpsu")]
    for part in ("ex4600-jpsu-650-ac-afo", "ex4600-jpsu-650-ac-afi", "ex4600-jpsu-650-dc-afo", "ex4600-jpsu-650-dc-afi"):
        assert load_component(part)["attrs"]["power-output-w"] == 650


def test_the_ex4550_back_to_front_fan_has_a_blue_handle_and_the_front_to_back_an_orange_one():
    f, b = rgb(handle_finish("ex4550-fan-afo")), rgb(handle_finish("ex4550-fan-afi"))
    assert f[0] > f[2] and f[0] > f[1], "orange: red is the dominant channel"
    assert b[2] > b[0] and b[2] > b[1], "blue: blue is the dominant channel"
    assert load_component("ex4550-fan-afo")["attrs"]["airflow"] == "front-to-back"
    assert load_component("ex4550-fan-afi")["attrs"]["airflow"] == "back-to-front"


@pytest.mark.parametrize("part,word", [("ex4550-fan-afo", "AIR OUT"), ("ex4550-fan-afi", "AIR IN")])
def test_an_ex4550_fan_module_prints_its_airflow_label(part, word):
    svg = (COMP / part / "v1/skins/default.svg").read_text()
    assert f">{word}</text>" in svg


def test_the_ex4500_lever_is_green_for_front_to_back_and_orange_for_back_to_front():
    """The guide: green is front-to-back airflow, orange is back-to-front; the lever matches the fan tray label."""
    green = [rgb(handle_finish(p)) for p in ("ex4500-psu-ac-fb", "ex4500-psu-dc-fb")]
    orange = rgb(handle_finish("ex4500-psu-ac-bf"))
    assert all(g[1] > g[0] and g[1] > g[2] for g in green)
    assert orange[0] > orange[2] and orange[0] > orange[1]
    fb = (COMP / "ex4500-fan-tray-fb/v1/skins/default.svg").read_text()
    bf = (COMP / "ex4500-fan-tray-bf/v1/skins/default.svg").read_text()
    assert ">EXHAUST</text>" in fb and ">INTAKE</text>" in bf


@pytest.mark.parametrize("part", ["ex4500-psu-ac-fb", "ex4500-psu-ac-bf", "ex4500-psu-dc-fb"])
def test_an_ex4500_supply_states_the_power_it_provides_as_an_output(part):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == 1200
    assert not any(k.startswith("power-draw") for k in attrs)


def test_the_ex4500_ac_supply_has_a_c19_appliance_inlet_and_the_dc_supply_two_terminals():
    ac = load_component("ex4500-psu-ac-fb")
    assert [ref_name(p["ref"]) for p in ac["parts"]] == ["c20-inlet"]
    dc = load_component("ex4500-psu-dc-fb")
    assert {"term-neg", "term-pos"} <= set(dc["elements"])


def test_the_ex4500_supplies_are_not_the_ex4600_ones():
    """Different power (1000 and 1200 W), a C19 inlet and no Juniper part number in the guide."""
    for part in ("ex4500-psu-ac-fb", "ex4500-psu-ac-bf", "ex4500-psu-dc-fb", "ex4500-fan-tray-fb", "ex4500-fan-tray-bf"):
        assert "part-numbers" not in load_component(part)


# --- the DCIM export ----------------------------------------------------------

def parts_of(variants, extra=()):
    return [v[0] for v in variants.values()] + list(extra)


@pytest.mark.parametrize("part,u_height", [(p, 1.0) for p in parts_of(F_VARIANTS, [S_SPARE[1]])]
                         + [(p, 1.0) for p in parts_of(T_VARIANTS)] + [(v[0], 2.0) for v in E_VARIANTS.values()])
def test_the_dcim_device_types_export_one_per_orderable_configuration(part, u_height):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for the device"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == u_height


def test_no_other_ex4500_or_ex4550_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("EX45*.yaml")}
    assert got == set(parts_of(F_VARIANTS, [S_SPARE[1]])) | set(parts_of(T_VARIANTS)) | {v[0] for v in E_VARIANTS.values()}


@pytest.mark.parametrize("part", sorted(FANS_4550))
def test_each_ex4550_fan_module_exports_a_module_type_carrying_its_part_number(part):
    found = []
    for target in ("netbox", "nautobot"):
        for f in (EXPORTS / target / "module-types" / "Juniper").glob("*.yaml"):
            doc = yaml.safe_load(f.read_text())
            if doc.get("part_number") == PART_NUMBER[part]:
                found.append(f.name)
    assert len(found) == 2, found
