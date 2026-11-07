"""The Juniper EX8200 chassis, from the EX8208 and EX8216 Switch Hardware Guides (both PDFs dated 2020-12-16).

One device per chassis: `juniper/ex8208` (14 U, eight line card slots) and `juniper/ex8216` (21 U, sixteen
line card slots). Their orders are `orderable` configurations, and the line cards are a family left out: every
line card slot shows its cover panel.

What the guides and the datasheets fix, and so what these tests hold:
  EX8208 Table 7    the envelope: 24.25 in high, 17.25 in wide, 20 in deep
  EX8216 Table 7    the envelope: 36.5 in high, 17.3 in wide, 26.5 in deep without the FRUs
  EX8208 Table 11   eight line card slots (0 to 7), SRE0, SF and SRE1; six power supply slots; one fan tray
  EX8216 Tables 11-13  two RE slots, sixteen line card slots, six power supply slots, two fan trays, and
                    eight SF slots (SF7 to SF0) on the rear
  Tables 5          what each shipping order seats
  Datasheets        the order codes (1000261-022-EN and 1000283-021-EN, both June 2015)
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVS = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

ORDERS = {
    "ex8208": {"base-ac": "EX8208-BASE-AC", "base-ac3": "EX8208-BASE-AC3", "redundant-ac": "EX8208-REDUND-AC",
               "redundant-dc": "EX8208-REDUND-DC", "chas": "EX8208-CHAS-S"},
    "ex8216": {"base-ac": "EX8216-BASE-AC", "redundant-ac": "EX8216-REDUND-AC",
               "redundant-ac2": "EX8216-REDUND-AC2", "redundant-dc": "EX8216-REDUND-DC", "chas": "EX8216-CHAS-S"},
}
RU = {"ex8208": 14, "ex8216": 21}


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
    """bay id -> component name, or '' for an open bay, as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for view in ("front", "rear"):
        for b in bays(dev, view):
            ref = (cfg.get("bays") or {}).get(b["id"], b.get("default"))
            out[b["id"]] = ref_name(ref) if ref else ""
    return out


def silk_text(dev, view):
    return {s.get("text") for s in dev["views"][view].get("silkscreen") or [] if s.get("text")}


# --- the envelope ------------------------------------------------------------

def test_the_ex8208_envelope_is_table_7():
    ch = load_device("ex8208")["chassis"]
    assert ch["ru"] == 14
    assert ch["height"] == pytest.approx(24.25 * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(17.25 * INCH, abs=0.1)       # the 19 in of the guide has the brackets
    assert ch["depth"] == pytest.approx(20 * INCH, abs=0.1)
    assert ch["airflow"] == "side"


def test_the_ex8216_envelope_is_table_7():
    ch = load_device("ex8216")["chassis"]
    assert ch["ru"] == 21
    assert ch["height"] == pytest.approx(36.5 * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(17.3 * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(26.5 * INCH, abs=0.1)        # without the FRUs; 29 in with them
    assert ch["airflow"] == "side"


@pytest.mark.parametrize("name", ["ex8208", "ex8216"])
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


@pytest.mark.parametrize("name,model", [("ex8208", "EX8208"), ("ex8216", "EX8216")])
def test_the_device_is_named_as_the_guide_prints_it(name, model):
    d = load_device(name)
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == model
    assert d["portfolio"] == {"line": "EX Series", "family": "EX8200"}
    assert d["chassis"].get("mount", "rack") == "rack"


# --- the slots, per face -----------------------------------------------------

def test_ex8208_front_has_eight_line_card_slots_two_sre_slots_one_sf_slot_six_supply_slots_and_the_fan_tray():
    d = load_device("ex8208")
    b = {x["id"]: x for x in bays(d, "front")}
    assert sorted(b) == sorted([f"lc{n}" for n in range(8)] + ["sre0", "sf", "sre1", "fan"] + [f"psu{n}" for n in range(6)])
    order = ["lc0", "lc1", "lc2", "lc3", "sre0", "sf", "sre1", "lc4", "lc5", "lc6", "lc7"]
    ys = [b[i]["at"][1] for i in order]
    assert ys == sorted(ys), "Table 11: 0-3, SRE0, SF, SRE1, then 4-7 down the front"
    pitch = {round(b - a, 1) for a, b in zip(ys, ys[1:])}
    assert pitch == {38.2}
    assert len({b[i]["at"][0] for i in order}) == 1
    px = [b[f"psu{n}"]["at"][0] for n in range(6)]
    assert px == sorted(px) and len({round(b - a, 1) for a, b in zip(px, px[1:])}) == 1, "PSU 0 to 5 left to right"
    assert b["fan"]["at"][0] < b["lc0"]["at"][0], "the fan tray runs down the left of the front"
    assert max(b[f"psu{n}"]["at"][1] for n in range(6)) > b["lc7"]["at"][1], "the supplies are at the bottom"
    assert d["views"]["rear"].get("components") is None


def test_ex8216_front_has_two_re_slots_sixteen_line_card_slots_six_supply_slots_and_two_fan_trays():
    d = load_device("ex8216")
    b = {x["id"]: x for x in bays(d, "front")}
    assert sorted(b) == sorted([f"lc{n}" for n in range(16)] + ["re0", "re1", "fan0", "fan1"] + [f"psu{n}" for n in range(6)])
    order = ["re0", "re1"] + [f"lc{n}" for n in range(16)]
    ys = [b[i]["at"][1] for i in order]
    assert ys == sorted(ys), "Table 11: RE0, RE1 and then the line cards 0 to 15 down the front"
    assert b["fan0"]["at"][1] < b["fan1"]["at"][1], "the top fan tray reads the inner column, the bottom one the outer"
    assert b["fan0"]["size"] == b["fan1"]["size"], "the two trays are identical and interchangeable (guide)"
    assert b["lc6"]["at"][1] + b["lc6"]["size"]["h"] <= b["fan1"]["at"][1] + 40.0
    px = [b[f"psu{n}"]["at"][0] for n in range(6)]
    assert px == sorted(px)


def test_ex8216_rear_has_eight_sf_slots_numbered_sf7_to_sf0_from_the_left():
    d = load_device("ex8216")
    b = {x["id"]: x for x in bays(d, "rear")}
    assert sorted(b) == sorted(f"sf{n}" for n in range(8))
    xs = [b[f"sf{n}"]["at"][0] for n in range(7, -1, -1)]
    assert xs == sorted(xs), "Table 13: SF7 to SF0 from left to right"
    assert {f"SF{n}" for n in range(8)} <= silk_text(d, "rear")


def test_the_slot_numbers_are_printed_on_the_fan_tray_not_on_the_chassis():
    """Figure 8 (EX8208) and Figure 12 (EX8216): the slot labels are on the fan tray's own face."""
    assert not any(s.get("text") in {"0", "1", "SRE0", "SF", "SRE1", "RE0", "RE1"}
                   for n in ("ex8208", "ex8216") for s in load_device(n)["views"]["front"].get("silkscreen") or [])
    svg8 = (COMP / "ex8208-fan/v1/skins/default.svg").read_text()
    for t in ("SRE0", "SF", "SRE1", "EX8208 FAN"):
        assert f">{t}<" in svg8
    svg16 = (COMP / "ex8216-fan/v1/skins/default.svg").read_text()
    for t in ("RE0", "RE1", "EX8216 FAN"):
        assert f">{t}<" in svg16


@pytest.mark.parametrize("name", ["ex8208", "ex8216"])
def test_the_front_carries_the_lcd_the_two_buttons_the_three_status_lamps_and_the_esd_point(name):
    d = load_device(name)
    p = {x["id"]: x for x in placements(d, "front")}
    assert {"btn-menu", "btn-enter", "led-alm", "led-sys", "led-mst", "esd-front-jack"} <= set(p)
    assert ref_name(p["btn-menu"]["ref"]) == "ex8200-lcd-button" and p["btn-menu"]["skin"] == "menu"
    assert p["btn-enter"]["skin"] == "enter"
    assert [p[i]["states"][1]["name"] for i in ("led-alm", "led-sys", "led-mst")] == ["major", "operating", "primary"]
    assert {"ALM", "SYS", "MST", d["model"]} <= silk_text(d, "front")
    lcd = [x for x in d["views"]["front"]["panel"]["decor"] if x.get("id") == "lcd"]
    assert len(lcd) == 1 and lcd[0]["kind"] == "display"


@pytest.mark.parametrize("name", ["ex8208", "ex8216"])
def test_no_logo_is_drawn_and_its_place_is_reserved(name):
    d = load_device(name)
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"]["regions"])
    for view in d["views"].values():
        words = " ".join(s.get("text", "") for s in view.get("silkscreen") or []).upper()
        assert "JUNIPER" not in words and "NETWORKS" not in words


def test_the_ports_of_the_re_and_sre_modules_are_the_figures():
    """Figure 16 / Figure 21: reset, USB, AUX, console and management on one face, with four lamps."""
    for name, part in (("ex8208-sre320", "EX8208-SRE320"), ("ex8216-re320", "EX8216-RE320")):
        c = load_component(name)
        by_id = {p["id"]: p for p in c["parts"]}
        assert ref_name(by_id["usb"]["ref"]) == "usb-a"
        assert ref_name(by_id["mgmt"]["ref"]) == "rj45-eth"
        assert ref_name(by_id["aux"]["ref"]) == "rj45" and ref_name(by_id["con"]["ref"]) == "rj45"
        assert by_id["con"]["attrs"]["media"] == "rj45-serial"
        assert ref_name(by_id["reset"]["ref"]) == "reset-button"
        assert {"led-on", "led-st", "led-ms", "led-sf"} == {k for k in c["elements"] if k.startswith("led-")}
        assert [v["part"] for v in c["part-numbers"].values()] == [part]
        assert c["class"] == "supervisor" and c["attrs"]["power-draw-max-w"] in (200, 100)


def test_module_power_figures_are_the_component_power_tables():
    assert load_component("ex8208-sre320")["attrs"]["power-draw-max-w"] == 200      # Table 57
    assert load_component("ex8208-sf320")["attrs"]["power-draw-max-w"] == 100
    assert load_component("ex8208-fan")["attrs"]["power-draw-max-w"] == 1100        # 300 W at normal speed
    assert load_component("ex8216-re320")["attrs"]["power-draw-max-w"] == 100       # Table 60
    assert load_component("ex8216-sf320")["attrs"]["power-draw-max-w"] == 75
    assert load_component("ex8216-fan")["attrs"]["power-draw-max-w"] == 800         # 190 W at normal speed, per tray


# --- the bays accept what the guide lists ------------------------------------

def test_ex8208_bays_accept_what_tables_4_and_11_list():
    b = {x["id"]: x for x in bays(load_device("ex8208"), "front")}
    for n in range(8):
        assert b[f"lc{n}"]["accepts"] == ["juniper/ex8208-lc-cover@1"], "line cards are left out"
    for s in ("sre0", "sre1"):
        assert b[s]["accepts"] == ["juniper/ex8208-sre320@1"]
    assert b["sf"]["accepts"] == ["juniper/ex8208-sf320@1"]
    assert b["fan"]["accepts"] == ["juniper/ex8208-fan@1"]
    for n in range(6):
        assert sorted(b[f"psu{n}"]["accepts"]) == sorted([
            "juniper/ex8200-pwr-ac2k@1", "juniper/ex8200-pwr-ac3k@1", "juniper/ex8200-pwr-dc2kr@1",
            "juniper/ex8200-psu-cover@1"])


def test_ex8216_bays_accept_what_tables_4_and_11_list():
    b = {x["id"]: x for x in bays(load_device("ex8216"), "front")}
    for n in range(16):
        assert b[f"lc{n}"]["accepts"] == ["juniper/ex8216-lc-cover@1"]
    for s in ("re0", "re1"):
        assert sorted(b[s]["accepts"]) == ["juniper/ex8216-re-cover@1", "juniper/ex8216-re320@1"]
    for f in ("fan0", "fan1"):
        assert b[f]["accepts"] == ["juniper/ex8216-fan@1"]
    for n in range(6):
        assert sorted(b[f"psu{n}"]["accepts"]) == sorted([
            "juniper/ex8200-pwr-ac2k@1", "juniper/ex8200-pwr-ac3k@1", "juniper/ex8200-pwr-dc3kr@1",
            "juniper/ex8200-psu-cover@1"])
    r = {x["id"]: x for x in bays(load_device("ex8216"), "rear")}
    for n in range(8):
        assert r[f"sf{n}"]["accepts"] == ["juniper/ex8216-sf320@1"]


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", ["ex8208", "ex8216"])
def test_each_order_is_an_orderable_configuration_with_its_part_number(name):
    cfgs = load_device(name)["configurations"]
    orderable = {c for c, v in cfgs.items() if v["kind"] == "orderable"}
    assert orderable == set(ORDERS[name])
    for cid, part in ORDERS[name].items():
        assert set(cfgs[cid]["part-numbers"]) == {part}


@pytest.mark.parametrize("name", ["ex8208", "ex8216"])
def test_the_default_is_the_base_chassis(name):
    cfgs = load_device(name)["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["base"]
    assert cfgs["base"]["kind"] == "base" and "part-numbers" not in cfgs["base"]


def _count(s, prefix):
    return sorted(v for k, v in s.items() if k.startswith(prefix) and v)


@pytest.mark.parametrize("cid,psu,sres,psus", [
    ("base", "ex8200-pwr-ac2k", 1, 2), ("base-ac", "ex8200-pwr-ac2k", 1, 2),
    ("base-ac3", "ex8200-pwr-ac3k", 1, 2), ("redundant-ac", "ex8200-pwr-ac2k", 2, 6),
    ("redundant-dc", "ex8200-pwr-dc2kr", 2, 4)])
def test_ex8208_orders_seat_table_5(cid, psu, sres, psus):
    s = seated(load_device("ex8208"), cid)
    assert _count(s, "sre") == ["ex8208-sre320"] * sres
    assert s["sf"] == "ex8208-sf320" and s["fan"] == "ex8208-fan"
    assert [v for k, v in s.items() if k.startswith("psu") and v == psu] == [psu] * psus
    others = {v for k, v in s.items() if k.startswith("psu") and v != psu}
    assert others <= {"ex8200-psu-cover"}
    assert [v for k, v in s.items() if k.startswith("psu") and v == "ex8200-psu-cover"] == \
        ["ex8200-psu-cover"] * (6 - psus)
    assert {v for k, v in s.items() if k.startswith("lc")} == {"ex8208-lc-cover"}
    assert load_component(psu)["attrs"]["airflow"] == "front-to-back"
    assert load_component("ex8208-fan")["attrs"]["airflow"] == "side-to-side"


@pytest.mark.parametrize("cid,psu,res,psus", [
    ("base", "ex8200-pwr-ac3k", 1, 2), ("base-ac", "ex8200-pwr-ac3k", 1, 2),
    ("redundant-ac", "ex8200-pwr-ac3k", 2, 6), ("redundant-ac2", "ex8200-pwr-ac2k", 2, 6),
    ("redundant-dc", "ex8200-pwr-dc3kr", 2, 4)])
def test_ex8216_orders_seat_table_5(cid, psu, res, psus):
    d = load_device("ex8216")
    s = seated(d, cid)
    assert [v for k, v in s.items() if k.startswith("re") and v == "ex8216-re320"] == ["ex8216-re320"] * res
    if res == 1:
        assert s["re1"] == "ex8216-re-cover", "Table 5: one RE module cover panel"
    assert [v for k, v in s.items() if k.startswith("psu") and v == psu] == [psu] * psus
    assert [v for k, v in s.items() if k.startswith("psu") and v == "ex8200-psu-cover"] == \
        ["ex8200-psu-cover"] * (6 - psus)
    assert {s[f"sf{n}"] for n in range(8)} == {"ex8216-sf320"}, "all eight SF modules ship"
    assert {s["fan0"], s["fan1"]} == {"ex8216-fan"}
    assert {v for k, v in s.items() if k.startswith("lc")} == {"ex8216-lc-cover"}
    assert load_component(psu)["attrs"]["airflow"] == "front-to-back"
    assert load_component("ex8216-fan")["attrs"]["airflow"] == "side-to-side"


@pytest.mark.parametrize("name", ["ex8208", "ex8216"])
def test_the_dc_orders_say_dc_and_the_spare_chassis_ships_with_every_bay_open(name):
    cfgs = load_device(name)["configurations"]
    assert cfgs["redundant-dc"]["power"] == "dc"
    assert "power" not in cfgs["base-ac"] or cfgs["base-ac"]["power"] == "ac"
    s = seated(load_device(name), "chas")
    assert all(v == "" for k, v in s.items() if not k.startswith("lc"))
    assert {v for k, v in s.items() if k.startswith("lc")} == {""}


def test_the_dc_supply_part_numbers_are_the_datasheets():
    assert [v["part"] for v in load_component("ex8200-pwr-dc2kr")["part-numbers"].values()] == ["EX8200-PWR-DC2KR"]
    assert [v["part"] for v in load_component("ex8200-pwr-dc3kr")["part-numbers"].values()] == ["EX8200-PWR-DC3KR"]
    assert [v["part"] for v in load_component("ex8200-pwr-ac2k")["part-numbers"].values()] == ["EX8200-PWR-AC2K"]
    assert [v["part"] for v in load_component("ex8200-pwr-ac3k")["part-numbers"].values()] == ["EX8200-PWR-AC3K"]
    assert load_component("ex8200-pwr-ac2k")["attrs"]["power-output-w"] == 2000
    assert load_component("ex8200-pwr-ac2k")["attrs"]["power-output-low-line-w"] == 1200
    assert load_component("ex8200-pwr-ac3k")["attrs"]["power-output-w"] == 3000
    assert load_component("ex8200-pwr-dc2kr")["attrs"]["power-output-w"] == 2000
    assert load_component("ex8200-pwr-dc3kr")["attrs"]["power-output-w"] == 3000


def test_the_ac_supplies_have_the_c20_inlet_and_the_dc_supplies_have_none():
    for n in ("ex8200-pwr-ac2k", "ex8200-pwr-ac3k"):
        assert [ref_name(p["ref"]) for p in load_component(n)["parts"]] == ["c20-inlet"]
    for n in ("ex8200-pwr-dc2kr", "ex8200-pwr-dc3kr"):
        assert "parts" not in load_component(n) or not any(
            ref_name(p["ref"]) == "c20-inlet" for p in load_component(n)["parts"])


def test_line_cards_are_left_out_and_not_built():
    """The EX8200 line cards are a family of their own; none is a component here."""
    for part in ("8xs", "40xs", "48t", "48f", "48pl", "48tl", "2xs-40p", "2xs-40t"):
        assert not list(COMP.glob(f"ex8200-*{part}*")) and not list(COMP.glob(f"ex82*-lc-{part}*"))


# --- the DCIM exports --------------------------------------------------------

@pytest.mark.parametrize("name", ["ex8208", "ex8216"])
def test_the_device_types_export_one_per_orderable_configuration_with_the_guides_height(name):
    for cid, part in ORDERS[name].items():
        for tool in ("netbox", "nautobot"):
            f = EXPORTS / tool / "device-types" / "Juniper" / f"{part}.yaml"
            assert f.exists(), f"{f.name} not exported"
            doc = yaml.safe_load(f.read_text())
            assert doc["u_height"] == RU[name]
            assert doc["model"] == part
            assert doc["manufacturer"] == "Juniper"
    exported = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob(f"EX{name[2:]}-*.yaml")}
    assert exported == set(ORDERS[name].values()), "no export for the unorderable base"
