"""The Juniper EX9250 line, from the EX9251 and EX9253 Switch Hardware Guides (both published 2022-11-30).

One device per front panel: `juniper/ex9251` (1RU, fixed) and `juniper/ex9253` (3RU, two Routing Engine
slots and two line card slots). Their orders are `orderable` configurations: the AC and DC EX9251 and its
spare chassis, and the four EX9253 orders (base and redundant, AC and DC) and its spare chassis.

What the guides and the datasheet fix, and so what these tests hold:
  EX9251 Table 4    the envelope - 1.72 in high, 18.5 in deep; the datasheet's Table 5 gives the 17.6 in body
  EX9251 Figure 1   4 QSFP28 ports (0/0 to 0/3), 8 SFP+ ports (1/0 to 1/7), the GM/PTP cage, and the service ports
  EX9251 Tables 1-3 the two models, their supplies and fan trays, and the spare chassis
  EX9253 Table 5    the envelope - 5.21 in (3 U) high, 30 in deep; the specifications page gives the 17.4 in body
  EX9253 Table 3    the four orders, their Routing Engines, supplies and blank panels
  EX9253 Figures 1-3 two Routing Engine slots (RE0, RE1), two line card slots (MPC0, MPC1), six supplies and four fans
  Datasheet         the ordering table: part numbers of the supplies, the fan trays, the blanks and the Routing Engine
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVS = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4


def load_device(name):
    return yaml.safe_load((DEVS / name / "device.yaml").read_text())


def load_component(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


def seated(dev, cid):
    """bay id -> component name or '' for an empty bay, as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for view in ("front", "rear"):
        for b in bays(dev, view):
            ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
            out[b["id"]] = ref_name(ref) if ref else ""
    return out


def silk_text(dev, view):
    return {s.get("text") for s in dev["views"][view].get("silkscreen") or [] if s.get("text")}


# the orders: configuration -> part number
EX9251_ORDERS = {"ac": "EX9251-8X4C", "dc": "EX9251-8X4C-DC", "chas": "EX9251-CHAS"}
EX9253_ORDERS = {"base-ac": "EX9253-BASE-AC", "base-dc": "EX9253-BASE-DC", "red-ac": "EX9253-RED-AC",
                 "red-dc": "EX9253-RED-DC", "chas": "EX9253-CHAS-3RU"}


# --- the envelope ------------------------------------------------------------

def test_the_ex9251_envelope_is_table_4_and_the_datasheet_body():
    ch = load_device("ex9251")["chassis"]
    assert ch["ru"] == 1
    assert ch["height"] == pytest.approx(1.72 * INCH, abs=0.1)       # guide Table 4
    assert ch["depth"] == pytest.approx(18.5 * INCH, abs=0.1)        # guide Table 4, without the handles
    assert ch["width"] == pytest.approx(17.6 * INCH, abs=0.1)        # datasheet Table 5; the guide's 19 in has the brackets
    assert ch["airflow"] == "front-to-back"


def test_the_ex9253_envelope_is_table_5_and_the_specifications_page_body():
    ch = load_device("ex9253")["chassis"]
    assert ch["ru"] == 3
    assert ch["height"] == pytest.approx(5.21 * INCH, abs=0.1)       # guide Table 5, 13.23 cm
    assert ch["depth"] == pytest.approx(30 * INCH, abs=0.1)          # guide Table 5, without the handles
    assert ch["width"] == pytest.approx(17.4 * INCH, abs=0.1)        # specifications page, 44.2 cm
    assert ch["airflow"] == "front-to-back"
    assert ch["weight-kg"] == pytest.approx(22.68)                   # chassis without any FRU


@pytest.mark.parametrize("name", ["ex9251", "ex9253"])
def test_the_faces_are_sized_from_the_envelope_and_the_front_is_the_body(name):
    d = load_device(name)
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}
    assert d["views"]["front"]["size"]["w"] < 480, "the brackets extend the body to 19 in; they are not drawn"


@pytest.mark.parametrize("name,model", [("ex9251", "EX9251"), ("ex9253", "EX9253")])
def test_the_device_is_named_as_the_guide_prints_it(name, model):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == model
    assert d["portfolio"] == {"line": "EX Series", "family": "EX9250"}


# --- the ports, per face -----------------------------------------------------

def test_ex9251_front_has_4_qsfp28_and_8_sfp_plus_cages_numbered_as_printed():
    d = load_device("ex9251")
    by_ref = {}
    for p in placements(d, "front"):
        by_ref.setdefault(ref_name(p["ref"]), []).append(p)
    q = sorted(p["id"] for p in by_ref["qsfp-ganged"])
    s = sorted(p["id"] for p in by_ref["sfp-ganged"])
    assert q == [f"port-0-{n}" for n in range(4)]
    assert s == [f"port-1-{n}" for n in range(8)]
    printed = silk_text(d, "front")
    assert {"0/0", "0/1", "0/2", "0/3"} <= printed
    assert {f"1/{n}" for n in range(8)} <= printed


def test_ex9251_sfp_plus_cages_sit_in_four_columns_with_the_even_port_above_the_odd():
    d = load_device("ex9251")
    at = {p["id"]: p["at"] for p in placements(d, "front") if ref_name(p["ref"]) == "sfp-ganged"}
    for c in range(4):
        up, down = at[f"port-1-{2 * c}"], at[f"port-1-{2 * c + 1}"]
        assert up[0] == down[0] and up[1] < down[1]
    xs = [at[f"port-1-{2 * c}"][0] for c in range(4)]
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [14.25] * 3, "the registry's 14.25 mm pitch"
    q = sorted(p["at"][0] for p in placements(d, "front") if ref_name(p["ref"]) == "qsfp-ganged")
    assert [round(b - a, 2) for a, b in zip(q, q[1:])] == [19.0] * 3, "the registry's 19.0 mm pitch"
    assert max(q) < min(xs), "the QSFP28 ports are left of the SFP+ block"


def test_ex9251_groups_say_what_the_ports_are():
    g = load_device("ex9251")["groups"]
    assert g["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}
    assert g["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert g["qsfp28"]["role"] == g["sfp-plus"]["role"] == "traffic"


def test_ex9251_has_the_service_ports_of_figure_1():
    d = load_device("ex9251")
    by_id = {p["id"]: p for p in placements(d, "front")}
    assert ref_name(by_id["gm-ptp"]["ref"]) == "sfp"
    assert ref_name(by_id["mgmt"]["ref"]) == "rj45-eth"
    for jack in ("bits", "con", "tod"):
        assert ref_name(by_id[jack]["ref"]) == "rj45"
    assert by_id["con"]["attrs"]["media"] == "rj45-serial"
    assert by_id["tod"]["attrs"]["media"] == "rj45-tod"
    assert ref_name(by_id["usb"]["ref"]) == "usb-a"
    smb = sorted(i for i, p in by_id.items() if ref_name(p["ref"]) == "smb")
    assert smb == ["clk-10mhz-in", "clk-10mhz-out", "clk-1pps-in", "clk-1pps-out"]
    printed = silk_text(d, "front")
    assert {"GM/PTP", "MGMT", "BITS", "CON", "ToD", "10MHz", "1PPS", "IN", "OUT", "RESET", "OFFLINE"} <= printed


def test_ex9251_lamps_follow_figures_4_to_8_and_table_7():
    d = load_device("ex9251")
    ids = {p["id"] for p in placements(d, "front") if p["ref"].startswith(("common/led-dot", "common/led-arrow"))}
    qsfp = {f"led-port-0-{n}-{k}" for n in range(4) for k in range(4)}
    sfp = {f"led-port-1-{n}" for n in range(8)}
    status = {"led-ok-fail", "led-online", "led-alm", "led-ssd1", "led-ssd0", "led-bits-act", "led-bits-link"}
    assert ids == qsfp | sfp | status
    printed = silk_text(d, "front")
    assert {"OK/FAIL", "ONLINE", "ALM", "SSD1", "SSD0"} <= printed


@pytest.mark.parametrize("name", ["ex9251", "ex9253"])
def test_no_logo_is_drawn_and_its_place_is_reserved(name):
    d = load_device(name)
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"]["regions"])
    for view in ("front", "rear"):
        words = " ".join(s.get("text", "") for s in d["views"][view].get("silkscreen") or []).upper()
        assert "JUNIPER" not in words and "NETWORKS" not in words and "JUNOS" not in words


def test_ex9251_rear_has_three_fan_slots_and_two_supply_slots_numbered_from_the_left():
    d = load_device("ex9251")
    b = {x["id"]: x for x in bays(d, "rear")}
    assert sorted(b) == ["fan-0", "fan-1", "fan-2", "psu-0", "psu-1"]
    assert b["fan-0"]["at"][0] < b["fan-1"]["at"][0] < b["fan-2"]["at"][0] < b["psu-0"]["at"][0] < b["psu-1"]["at"][0]
    ids = {p["id"] for p in placements(d, "rear")}
    assert {"led-fan-0", "led-fan-1", "led-fan-2", "esd-rear-jack", "ground-screw-0", "ground-screw-1"} <= ids
    g0, g1 = (p["at"] for p in placements(d, "rear") if p["id"] in ("ground-screw-0", "ground-screw-1"))
    assert g1[0] - g0[0] == pytest.approx(16.0, abs=0.1), "two holes at 16 mm centres (guide, Grounding Points)"


def test_ex9253_has_two_routing_engine_slots_over_two_line_card_slots():
    d = load_device("ex9253")
    b = {x["id"]: x for x in bays(d, "front")}
    assert sorted(b) == ["mpc-0", "mpc-1", "re-0", "re-1"]
    assert b["re-0"]["at"][0] < b["re-1"]["at"][0] and b["re-0"]["at"][1] == b["re-1"]["at"][1]
    assert b["re-0"]["at"][1] < b["mpc-1"]["at"][1] < b["mpc-0"]["at"][1], "MPC1 is above MPC0"
    assert b["mpc-0"]["size"] == b["mpc-1"]["size"]
    assert any(ref_name(p["ref"]) == "esd-jack" for p in placements(d, "front"))


def test_ex9253_rear_has_six_supply_slots_and_four_fan_trays_between_them():
    d = load_device("ex9253")
    b = {x["id"]: x for x in bays(d, "rear")}
    assert sorted(b) == [f"fan-{n}" for n in range(4)] + [f"psm-{n}" for n in range(6)]
    left = [b[f"psm-{n}"]["at"] for n in (0, 2, 4)]
    right = [b[f"psm-{n}"]["at"] for n in (1, 3, 5)]
    assert len({a[0] for a in left}) == 1 and len({a[0] for a in right}) == 1
    assert [a[1] for a in left] == sorted(a[1] for a in left)
    fans = [b[f"fan-{n}"]["at"][0] for n in range(4)]
    assert fans == sorted(fans) and max(left[0][0] for _ in (0,)) < min(fans) and max(fans) < right[0][0]
    assert {"PSM0", "PSM1", "PSM2", "PSM3", "PSM4", "PSM5"} <= silk_text(d, "rear")


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name,orders", [("ex9251", EX9251_ORDERS), ("ex9253", EX9253_ORDERS)])
def test_each_order_is_an_orderable_configuration_with_its_part_number(name, orders):
    cfgs = load_device(name)["configurations"]
    orderable = {c for c, v in cfgs.items() if v["kind"] == "orderable"}
    assert orderable == set(orders)
    for cid, part in orders.items():
        assert set(cfgs[cid]["part-numbers"]) == {part}


@pytest.mark.parametrize("name", ["ex9251", "ex9253"])
def test_the_default_is_the_base_chassis_with_ac_power(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["base"]
    assert cfgs["base"]["kind"] == "base"


@pytest.mark.parametrize("cid,psu", [("base", "ex4600-jpsu-650-ac-afo"), ("ac", "ex4600-jpsu-650-ac-afo"),
                                     ("dc", "ex4600-jpsu-650-dc-afo")])
def test_ex9251_orders_seat_two_supplies_and_three_fan_trays(cid, psu):
    s = seated(load_device("ex9251"), cid)
    assert {s["psu-0"], s["psu-1"]} == {psu}
    assert {s[f"fan-{n}"] for n in range(3)} == {"ex9251-fan-1ru"}
    assert load_component(psu)["attrs"]["airflow"] == "front-to-back"
    assert load_component("ex9251-fan-1ru")["attrs"]["airflow"] == "front-to-back"


def test_ex9251_supplies_are_reused_from_the_ex4600_by_part_number():
    """The guide's Table 2 names JPSU-650W-DC-AFO and an AC AFO 650 W supply; the library has both."""
    assert [v["part"] for v in load_component("ex4600-jpsu-650-dc-afo")["part-numbers"].values()] == ["JPSU-650W-DC-AFO"]
    assert not (COMP / "ex9251-jpsu-650-dc-afo").exists()
    assert not (COMP / "ex9251-jpsu-650-ac-afo").exists()


def test_ex9251_spare_chassis_ships_with_open_supply_and_fan_bays():
    s = seated(load_device("ex9251"), "chas")
    assert all(s[b] == "" for b in ("psu-0", "psu-1", "fan-0", "fan-1", "fan-2"))


def test_ex9251_single_supply_example_covers_the_second_slot_with_the_blank_panel():
    d = load_device("ex9251")
    s = seated(d, "single-psu")
    assert s["psu-0"] == "ex4600-jpsu-650-ac-afo" and s["psu-1"] == "jnp-pwr-blnk-1"
    assert d["configurations"]["single-psu"]["kind"] == "example"


@pytest.mark.parametrize("cid,re_count,psu,count", [
    ("base", 1, "ex9253-jnp-pwr1600-ac", 3), ("base-ac", 1, "ex9253-jnp-pwr1600-ac", 3),
    ("base-dc", 1, "ex9253-jnp-pwr1100-dc", 3), ("red-ac", 2, "ex9253-jnp-pwr1600-ac", 4),
    ("red-dc", 2, "ex9253-jnp-pwr1100-dc", 4)])
def test_ex9253_orders_seat_the_guides_routing_engines_supplies_and_four_fan_trays(cid, re_count, psu, count):
    """Table 3 and Table 32: base is one RE and three supplies, redundant two REs and four; four fan trays."""
    s = seated(load_device("ex9253"), cid)
    assert sorted(v for k, v in s.items() if k.startswith("re-") and v == "ex9253-re") == ["ex9253-re"] * re_count
    other_re = [v for k, v in s.items() if k.startswith("re-") and v != "ex9253-re"]
    assert all(v == "ex9253-re-blnk" for v in other_re) and len(other_re) == 2 - re_count
    psus = [v for k, v in s.items() if k.startswith("psm-")]
    assert psus.count(psu) == count
    assert all(v in (psu, "ex9253-psu-blank") for v in psus), "AC and DC are never mixed"
    assert [s[f"fan-{n}"] for n in range(4)] == ["ex9253-fan-3ru"] * 4
    assert s["mpc-0"] == s["mpc-1"] == "ex9253-lc-blnk", "line cards are ordered separately"


def test_ex9253_spare_chassis_has_every_bay_open():
    s = seated(load_device("ex9253"), "chas")
    assert set(s.values()) == {""}
    assert len(s) == 14


def test_the_bays_accept_the_units_the_guides_list():
    d = load_device("ex9251")
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        if b["id"].startswith("fan-"):
            assert got == {"ex9251-fan-1ru"}
        else:
            assert got == {"ex4600-jpsu-650-ac-afo", "ex4600-jpsu-650-dc-afo", "jnp-pwr-blnk-1"}
    d = load_device("ex9253")
    for b in bays(d, "front"):
        got = {ref_name(r) for r in b["accepts"]}
        assert got == ({"ex9253-re", "ex9253-re-blnk"} if b["id"].startswith("re-") else {"ex9253-lc-blnk"})
    for b in bays(d, "rear"):
        got = {ref_name(r) for r in b["accepts"]}
        if b["id"].startswith("fan-"):
            assert got == {"ex9253-fan-3ru"}
        else:
            assert got == {"ex9253-jnp-pwr1600-ac", "ex9253-jnp-pwr1100-dc", "ex9253-psu-blank"}


@pytest.mark.parametrize("name", ["ex9251", "ex9253"])
def test_bays_reserve_one_size_for_each_unit_they_accept(name):
    d = load_device(name)
    for view in ("front", "rear"):
        for b in bays(d, view):
            for ref in b["accepts"]:
                c = load_component(ref_name(ref))["size"]
                assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3), (b["id"], ref)
                assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3), (b["id"], ref)


# --- the field-replaceable units ---------------------------------------------

# component -> the Juniper part number it is ordered under (guide Tables 3 and 4, datasheet ordering table)
PART_NUMBER = {
    "ex9251-fan-1ru": "JNP-FAN-1RU", "jnp-pwr-blnk-1": "JNP-PWR-BLNK-1",
    "ex9253-fan-3ru": "JNP-FAN-3RU", "ex9253-jnp-pwr1600-ac": "JNP-PWR1600-AC",
    "ex9253-jnp-pwr1100-dc": "JNP-PWR1100-DC", "ex9253-re": "EX9253-RE",
    "ex9253-re-blnk": "EX9253-RE-BLNK", "ex9253-lc-blnk": "EX9253-LC-BLNK",
}


@pytest.mark.parametrize("part", sorted(PART_NUMBER))
def test_a_unit_is_ordered_under_its_juniper_part_number(part):
    c = load_component(part)
    assert c["name"] == part and c["kind"] == "module"
    assert [v["part"] for v in c["part-numbers"].values()] == [PART_NUMBER[part]]


def test_the_ex9253_psu_blank_names_no_part_number_because_the_guide_names_none():
    c = load_component("ex9253-psu-blank")
    assert "part-numbers" not in c
    assert "no part number" in " ".join(c["description"].split())


@pytest.mark.parametrize("part,watts", [("ex9253-jnp-pwr1600-ac", 1600), ("ex9253-jnp-pwr1100-dc", 1100)])
def test_an_ex9253_supply_states_the_power_it_provides_as_an_output(part, watts):
    attrs = load_component(part)["attrs"]
    assert attrs["power-output-w"] == watts
    assert not any(k.startswith("power-draw") for k in attrs)


def test_the_ex9253_ac_supply_gives_800_w_on_a_low_line():
    assert load_component("ex9253-jnp-pwr1600-ac")["attrs"]["power-output-low-line-w"] == 800


def test_the_ex9253_fan_tray_and_routing_engine_state_the_draw_of_table_13():
    fan, re_ = load_component("ex9253-fan-3ru")["attrs"], load_component("ex9253-re")["attrs"]
    assert (fan["power-draw-typical-w"], fan["power-draw-max-w"]) == (20, 95)
    assert (re_["power-draw-typical-w"], re_["power-draw-max-w"]) == (58, 65)


def test_a_fan_tray_is_labelled_air_out_and_front_to_back():
    """Both guides: front-to-back (AIR OUT) airflow only, and the tray says so."""
    for part in ("ex9251-fan-1ru", "ex9253-fan-3ru"):
        assert load_component(part)["attrs"]["airflow"] == "front-to-back"
        svg = (COMP / part / "v1/skins/default.svg").read_text()
        assert ">AIR</text>" in svg and ">OUT</text>" in svg


def test_the_ex9251_fan_tray_face_is_the_square_of_figure_10():
    assert load_component("ex9251-fan-1ru")["size"] == {"w": 41.7, "h": 41.7}


def test_the_ex9253_routing_engine_has_the_ports_of_figure_6():
    c = load_component("ex9253-re")
    parts = {p["id"]: ref_name(p["ref"]) for p in c["parts"]}
    assert {"usb", "mgmt", "con", "tod", "bits", "mhz-out", "pps-out", "mhz-in", "pps-in"} <= set(parts)
    assert parts["usb"] == "usb-a" and parts["mgmt"] == "rj45-eth"
    assert [i for i, n in parts.items() if n == "smb"] == ["mhz-out", "pps-out", "mhz-in", "pps-in"]
    assert {"led-ssd0", "led-ssd1", "led-mst", "led-alm", "led-ok-fail", "led-online", "reset", "offline"} <= set(c["elements"])


def test_the_ex9253_dc_supply_has_two_terminals():
    c = load_component("ex9253-jnp-pwr1100-dc")
    assert sorted(n for n, e in c["elements"].items() if e["class"] == "screw") == ["term-a", "term-b"]


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("part,u", [(p, 1.0) for p in EX9251_ORDERS.values()] + [(p, 3.0) for p in EX9253_ORDERS.values()])
def test_the_dcim_device_types_export_one_per_orderable_configuration(part, u):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for the device"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == u


def test_no_other_ex9250_device_type_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("EX925*.yaml")}
    assert got == set(EX9251_ORDERS.values()) | set(EX9253_ORDERS.values())


@pytest.mark.parametrize("part", sorted(p for p in PART_NUMBER))
def test_each_unit_exports_a_module_type_carrying_its_juniper_part_number(part):
    want = PART_NUMBER[part]
    found = []
    for target in ("netbox", "nautobot"):
        for f in (EXPORTS / target / "module-types" / "Juniper").glob("*.yaml"):
            doc = yaml.safe_load(f.read_text())
            if doc.get("part_number") == want and doc["model"].startswith(want):
                found.append(f.name)
    assert len(found) == 2, found
