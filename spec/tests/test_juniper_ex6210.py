"""The Juniper EX6210, from the EX6210 Switch Hardware Guide (published 2020-12-15) and the EX6200 datasheet (Aug 2011).

One device for one front panel: `juniper/ex6210`, ten horizontal slots over four power supply slots, with the fan tray
at the rear. The four shipping orders and the spare chassis are `orderable` configurations. The line cards are a
family of their own and are not modelled: their slots show cover panels.

What the guide and the datasheet fix, and so what these tests hold:
  guide Table 7        the envelope - 24.3 in high, 17.3 in wide (19 in with the brackets), 15.5 in deep; 14 U (the task said 9 U)
  guide Tables 10, 11  ten slots numbered 0 to 9 (4 and 5 take an SRE module or a line card) and four supply slots PSU 0 to PSU 3
  guide Table 5        the four shipping orders, each with one SRE module, one supply, one fan tray and the cover panels
  guide Table 21       the cover panels of the two AC supplies (EX6200-BLNK-PWR-2U and -3U)
  guide Figure 7       the SRE module: four SFP+ uplinks (0 to 3), an SFP and a copper management port, console, USB, reset, LCD
  guide Tables 31, 32  fan tray 300 W, SRE module 100 W
  datasheet            the ordering table: EX6210-CHAS, EX6210-FAN and the part numbers of the modules
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper/ex6210/device.yaml"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

INCH = 25.4

ORDERS = {
    "ac-2500-t": "EX6210-S64-96T-A25",
    "ac-2500-p": "EX6210-S64-96P-A25",
    "ac-5000-p": "EX6210-S64-96P-A50",
    "dc-2100-t": "EX6210-S64-96T-D21",
    "chassis": "EX6210-CHAS",
}

# component -> the Juniper part number it is ordered under (guide Tables 4, 6 and 21, datasheet ordering table)
PART_NUMBER = {
    "ex6200-sre64-4xs": "EX6200-SRE64-4XS",
    "ex6200-pwr-ac2500": "EX6200-PWR-AC2500",
    "ex6200-pwr-ac5000": "EX6200-PWR-AC5000",
    "ex6200-pwr-dc2100": "EX6200-PWR-DC2100",
    "ex6200-blnk-pwr-2u": "EX6200-BLNK-PWR-2U",
    "ex6200-blnk-pwr-3u": "EX6200-BLNK-PWR-3U",
    "ex6210-fan": "EX6210-FAN",
}

TWO_U = ["base", "redundant", "ac-2500-t", "ac-2500-p", "dc-2100-t", "chassis"]


def load():
    return yaml.safe_load(DEV.read_text())


def comp(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def skin(name):
    return (COMP / name / "v1" / "skins" / "default.svg").read_text()


def view_parts(dev, view, key):
    return (dev["views"][view].get("components") or {}).get(key) or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


def bays_in(dev, cid):
    """The bays that exist in a configuration (`only-in` scopes some), front and rear."""
    out = {}
    for view in ("front", "rear"):
        for b in view_parts(dev, view, "bays"):
            if "only-in" not in b or cid in b["only-in"]:
                out[b["id"]] = b
    return out


def seated(dev, cid):
    """bay id -> component name, or '' for an open bay, as the configuration leaves it."""
    cfg = dev["configurations"][cid]
    out = {}
    for bid, b in bays_in(dev, cid).items():
        ref = (cfg.get("bays") or {}).get(bid, b.get("default"))
        out[bid] = ref_name(ref) if ref else ""
    return out


# --- the envelope ------------------------------------------------------------

def test_the_envelope_is_table_7_and_the_body_is_not_the_bracketed_width():
    d = load()
    ch = d["chassis"]
    assert ch["ru"] == 14                                               # guide: "14 rack units (14 U)"; the task's 9 U is not the guide's
    assert ch["height"] == pytest.approx(24.3 * INCH, abs=0.1)          # Table 7
    assert ch["width"] == pytest.approx(17.3 * INCH, abs=0.1)           # Table 7; 19 in is with the front-mounting brackets
    assert ch["depth"] == pytest.approx(15.5 * INCH, abs=0.1)           # Table 7 and Figure 32
    assert ch["airflow"] == "front-to-back"
    assert ch["width"] < 480, "the brackets extend the body to 19 in; they are not drawn"


def test_the_faces_are_sized_from_the_envelope():
    d = load()
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


def test_the_device_is_named_as_the_guide_prints_it():
    d = load()
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == "EX6210"
    assert d["portfolio"] == {"line": "EX Series", "family": "EX6200"}


def test_the_ears_state_the_one_flush_position_the_guide_gives():
    ears = load()["chassis"]["ears"]
    assert [(p["name"], p["at"], p.get("default")) for p in ears["positions"]] == [("flush", 0, True)]
    assert "kits" not in load()["chassis"], "rack kits go in provenance only"


# --- the slots, per face -----------------------------------------------------

def test_front_has_ten_slots_numbered_0_to_9_from_the_top_with_slots_4_and_5_taller():
    d = load()
    slots = {b["id"]: b for b in view_parts(d, "front", "bays") if b["id"].startswith("slot-")}
    assert sorted(slots) == [f"slot-{n}" for n in range(10)]
    ys = [slots[f"slot-{n}"]["at"][1] for n in range(10)]
    assert ys == sorted(ys), "slot 0 is the top"
    tall = {n for n in range(10) if slots[f"slot-{n}"]["size"]["h"] > 50}
    assert tall == {4, 5}
    widths = {b["size"]["w"] for b in slots.values()}
    assert len(widths) == 1, "every slot plate is one width"
    for n in range(10):
        assert slots[f"slot-{n}"]["rel-pos"] == n
        assert slots[f"slot-{n}"]["group"] == ("sre-slots" if n in (4, 5) else "slots")
    printed = {s["text"] for s in d["views"]["front"]["silkscreen"] if s.get("text")}
    assert {str(n) for n in range(10)} <= printed


def test_the_slots_accept_what_guide_table_10_lists_for_them():
    d = load()
    for b in view_parts(d, "front", "bays"):
        if not b["id"].startswith("slot-"):
            continue
        got = {ref_name(r) for r in b["accepts"]}
        n = int(b["id"].split("-")[1])
        if n in (4, 5):
            assert got == {"ex6200-sre64-4xs", "ex6200-sre-cover"}, b["id"]
        else:
            assert got == {"ex6200-lc-cover"}, b["id"]


def test_the_four_supply_slots_are_numbered_from_the_left_and_the_5000_w_set_is_taller():
    d = load()
    b2 = {k: v for k, v in bays_in(d, "base").items() if k.startswith("psu-")}
    b3 = {k: v for k, v in bays_in(d, "ac-5000-p").items() if k.startswith("psu-")}
    assert sorted(b2) == [f"psu-{n}" for n in range(4)]
    assert sorted(b3) == [f"psu-{n}-3u" for n in range(4)]
    for bays_ in (b2, b3):
        xs = [v["at"][0] for _, v in sorted(bays_.items())]
        assert xs == sorted(xs) and [round(b - a, 1) for a, b in zip(xs, xs[1:])] == [108.5] * 3
        assert {v["at"][1] for v in bays_.values()} == {454.5}
    assert {v["size"]["h"] for v in b2.values()} == {101.8}
    assert {v["size"]["h"] for v in b3.values()} == {152.7}


def test_the_supply_slots_accept_the_supplies_and_covers_of_the_guide():
    d = load()
    for cid, want in (("base", {"ex6200-pwr-ac2500", "ex6200-pwr-dc2100", "ex6200-blnk-pwr-2u"}),
                      ("ac-5000-p", {"ex6200-pwr-ac5000", "ex6200-blnk-pwr-3u"})):
        for bid, b in bays_in(d, cid).items():
            if bid.startswith("psu-"):
                assert {ref_name(r) for r in b["accepts"]} == want, bid


def test_the_blank_shelf_stands_under_the_2u_supplies_only_and_is_gone_with_the_5000_w_ones():
    d = load()
    shelf = [p for p in view_parts(d, "front", "placements") if p["id"] == "psu-shelf"][0]
    assert ref_name(shelf["ref"]) == "ex6200-psu-shelf"
    assert "ac-5000-p" not in shelf["only-in"] and set(shelf["only-in"]) == set(TWO_U)
    svg = skin("ex6200-psu-shelf")
    for n in range(4):
        assert f">PSU{n}</text>" in svg, "the slot labels are printed on the shelf"


def test_rear_has_one_vertical_fan_tray_and_the_earthing_pair_at_0_625_in():
    d = load()
    bays = view_parts(d, "rear", "bays")
    assert [b["id"] for b in bays] == ["fan-0"]
    assert [ref_name(r) for r in bays[0]["accepts"]] == ["ex6210-fan"]
    assert bays[0]["size"]["h"] > 4 * bays[0]["size"]["w"] / 2, "a vertical tray"
    inserts = [x for x in d["views"]["rear"]["panel"]["decor"] if x.get("size") == [7.0, 7.0]]
    assert len(inserts) == 2
    assert inserts[1]["at"][0] - inserts[0]["at"][0] == pytest.approx(0.625 * INCH, abs=0.2)   # guide: 0.625 in (15.86 mm)
    assert any(p["ref"].startswith("common/esd-jack") for p in view_parts(d, "rear", "placements"))
    assert any(p["ref"].startswith("common/esd-jack") for p in view_parts(d, "front", "placements"))


def test_no_logo_is_drawn_and_its_place_is_reserved():
    d = load()
    assert any(r["id"] == "logo-zone" for r in d["views"]["front"]["regions"])
    for view in ("front", "rear"):
        words = " ".join(s.get("text", "") for s in d["views"][view].get("silkscreen") or []).upper()
        assert "JUNIPER" not in words and "NETWORKS" not in words and "JUNOS" not in words
    for name in list(PART_NUMBER) + ["ex6200-lc-cover", "ex6200-sre-cover", "ex6200-psu-shelf"]:
        text = skin(name).upper()
        assert "JUNIPER" not in text and "NETWORKS" not in text, name


# --- the SRE module's ports --------------------------------------------------

def test_the_sre_module_has_four_sfp_plus_uplinks_numbered_0_to_3_on_the_registry_pitch():
    c = comp("ex6200-sre64-4xs")
    parts = {p["id"]: p for p in c["parts"]}
    up = [parts[f"uplink-{n}"] for n in range(4)]
    assert {ref_name(p["ref"]) for p in up} == {"sfp-ganged"}
    xs = [p["at"][0] for p in up]
    assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [14.25] * 3
    assert {p["at"][1] for p in up} == {42.4}
    assert c["groups"]["uplink"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert c["groups"]["uplink"]["role"] == "traffic" and c["groups"]["uplink"]["index-origin"] == 0
    svg = skin("ex6200-sre64-4xs")
    for n in range(4):
        assert f">{n}</text>" in svg


def test_the_sre_module_has_the_management_ports_of_figure_7():
    c = comp("ex6200-sre64-4xs")
    parts = {p["id"]: ref_name(p["ref"]) for p in c["parts"]}
    assert parts["mgmt-sfp"] == "sfp" and parts["mgmt-rj45"] == "rj45-eth"
    assert parts["console"] == "rj45" and parts["usb"] == "usb-a" and parts["reset"] == "reset-button"
    by_id = {p["id"]: p for p in c["parts"]}
    assert by_id["console"]["attrs"]["media"] == "rj45-serial"
    assert by_id["mgmt-sfp"]["attrs"]["speed"] == by_id["mgmt-rj45"]["attrs"]["speed"] == "1g"
    assert c["groups"]["mgmt"]["role"] == "management"
    printed = " ".join(skin("ex6200-sre64-4xs").split())
    for word in ("MGMT", "CONSOLE", "RESET", "ALM", "SYS", "MST"):
        assert f">{word}</text>" in printed


def test_the_sre_module_has_two_lamps_per_port_and_the_three_chassis_lamps():
    els = comp("ex6200-sre64-4xs")["elements"]
    lamps = {k for k, e in els.items() if e["class"] == "led"}
    uplink = {f"led-uplink-{n}-{k}" for n in range(4) for k in ("link", "status")}
    assert lamps == uplink | {"led-mgmt-sfp-link", "led-mgmt-sfp-status", "led-alm", "led-sys", "led-mst"}
    assert {k for k, e in els.items() if e["class"] == "button"} == {"btn-menu", "btn-enter"}
    assert els["lcd"]["class"] == "display"


def test_the_sre_module_slot_is_one_bay_with_no_line_card_ports_drawn_on_the_chassis():
    """The ports belong to the module in the bay: the chassis front places no cage and no jack of its own."""
    d = load()
    for p in view_parts(d, "front", "placements") + view_parts(d, "rear", "placements"):
        assert not p["ref"].startswith(("std/sfp", "std/rj45", "common/rj45", "std/usb")), p["id"]


# --- the configurations ------------------------------------------------------

def test_each_order_is_an_orderable_configuration_with_its_part_number():
    cfgs = load()["configurations"]
    assert {c for c, v in cfgs.items() if v["kind"] == "orderable"} == set(ORDERS)
    for cid, part in ORDERS.items():
        assert set(cfgs[cid]["part-numbers"]) == {part}


def test_the_default_is_the_base_chassis_and_the_redundant_build_is_an_illustration():
    cfgs = load()["configurations"]
    assert [c for c, v in cfgs.items() if v.get("default")] == ["base"]
    assert cfgs["base"]["kind"] == "base"
    assert cfgs["redundant"]["kind"] == "example", "no order code names it, so it must not export"


@pytest.mark.parametrize("cid,psu,covers", [
    ("base", "ex6200-pwr-ac2500", "ex6200-blnk-pwr-2u"), ("ac-2500-t", "ex6200-pwr-ac2500", "ex6200-blnk-pwr-2u"),
    ("ac-2500-p", "ex6200-pwr-ac2500", "ex6200-blnk-pwr-2u"), ("dc-2100-t", "ex6200-pwr-dc2100", "ex6200-blnk-pwr-2u")])
def test_the_2u_orders_seat_one_supply_three_covers_one_sre_module_and_one_fan_tray(cid, psu, covers):
    """Tables 5 and 51: one SRE module and its cover panel, one supply and three covers, six line card covers, one fan tray."""
    s = seated(load(), cid)
    assert s["psu-0"] == psu and [s[f"psu-{n}"] for n in (1, 2, 3)] == [covers] * 3
    assert s["slot-4"] == "ex6200-sre64-4xs" and s["slot-5"] == "ex6200-sre-cover"
    assert [v for k, v in s.items() if k.startswith("slot-") and v == "ex6200-lc-cover"] == ["ex6200-lc-cover"] * 8
    assert s["fan-0"] == "ex6210-fan"


def test_the_5000_w_order_seats_the_taller_supply_and_its_3u_covers_and_no_shelf():
    d = load()
    s = seated(d, "ac-5000-p")
    assert s["psu-0-3u"] == "ex6200-pwr-ac5000"
    assert [s[f"psu-{n}-3u"] for n in (1, 2, 3)] == ["ex6200-blnk-pwr-3u"] * 3
    assert not any(k in s for k in ("psu-0", "psu-1", "psu-2", "psu-3"))
    assert s["fan-0"] == "ex6210-fan"


def test_the_dc_order_says_dc_and_the_others_do_not():
    cfgs = load()["configurations"]
    assert cfgs["dc-2100-t"]["power"] == "dc"
    assert load()["chassis"]["power"] == "ac"
    assert not [c for c, v in cfgs.items() if c != "dc-2100-t" and v.get("power") == "dc"]


def test_the_redundant_example_seats_a_second_sre_module_in_slot_5():
    s = seated(load(), "redundant")
    assert s["slot-4"] == s["slot-5"] == "ex6200-sre64-4xs"


def test_the_spare_chassis_leaves_every_bay_open():
    s = seated(load(), "chassis")
    assert set(s.values()) == {""}
    assert len(s) == 15, "ten slots, four supply slots and the fan tray"


def test_there_is_no_airflow_variant_because_the_guide_has_only_front_to_back():
    d = load()
    assert not [c for c, v in d["configurations"].items() if "airflow" in v]
    for name, attr in (("ex6200-pwr-ac2500", "airflow"), ("ex6200-pwr-ac5000", "airflow"),
                       ("ex6200-pwr-dc2100", "airflow"), ("ex6210-fan", "airflow")):
        assert comp(name)["attrs"][attr] == "front-to-back"


def test_the_line_cards_are_listed_as_left_out_by_part_number_and_not_built():
    d = load()
    gap = [g for g in d["gaps"] if g["what"] == "line-cards"][0]
    for part in ("EX6200-48T", "EX6200-48P", "EX6200-48F"):
        assert part in gap["wanted"], part
        assert not (COMP / part.lower()).exists()
    assert not [p for p in COMP.iterdir() if p.name.startswith(("ex6200-48", "ex6210-lc"))]


# --- the field-replaceable units ---------------------------------------------

@pytest.mark.parametrize("name", sorted(PART_NUMBER))
def test_a_unit_is_ordered_under_its_juniper_part_number(name):
    c = comp(name)
    assert c["name"] == name and c["kind"] == "module"
    assert [v["part"] for v in c["part-numbers"].values()] == [PART_NUMBER[name]]


@pytest.mark.parametrize("name", ["ex6200-lc-cover", "ex6200-sre-cover"])
def test_the_line_card_and_sre_covers_name_no_part_number_because_the_guide_names_none(name):
    assert "part-numbers" not in comp(name)


@pytest.mark.parametrize("name,watts", [("ex6200-pwr-ac2500", 2500), ("ex6200-pwr-ac5000", 5000), ("ex6200-pwr-dc2100", 2100)])
def test_a_supply_states_the_power_it_provides_as_an_output(name, watts):
    attrs = comp(name)["attrs"]
    assert attrs["power-output-w"] == watts
    assert not any(k.startswith("power-draw") for k in attrs)


def test_the_ac_supplies_give_half_on_a_low_line():
    assert comp("ex6200-pwr-ac2500")["attrs"]["power-output-low-line-w"] == 1250
    assert comp("ex6200-pwr-ac5000")["attrs"]["power-output-low-line-w"] == 2500


def test_the_fan_tray_and_the_sre_module_state_the_draw_of_table_31():
    assert comp("ex6210-fan")["attrs"]["power-draw-max-w"] == 300
    assert comp("ex6200-sre64-4xs")["attrs"]["power-draw-max-w"] == 100


def test_the_5000_w_supply_has_two_c20_inlets_and_the_2500_w_supply_one():
    two = [p for p in comp("ex6200-pwr-ac5000")["parts"] if "c20-inlet" in p["ref"]]
    one = [p for p in comp("ex6200-pwr-ac2500")["parts"] if "c20-inlet" in p["ref"]]
    assert len(two) == 2 and len(one) == 1                     # guide Table 20: IEC-320-C20, one or two inlets


def test_the_dc_supply_has_no_ac_inlet_and_a_terminal_block():
    c = comp("ex6200-pwr-dc2100")
    assert [p["ref"] for p in c["parts"]] == ["juniper/mx240-dc-pole@1"] * 2    # the studs; no inlet part
    assert c["elements"]["terminals"]["class"] == "terminal"


def test_the_5000_w_cover_is_one_and_a_half_times_the_2u_cover():
    two, three = comp("ex6200-blnk-pwr-2u")["size"], comp("ex6200-blnk-pwr-3u")["size"]
    assert two["w"] == three["w"] and three["h"] == pytest.approx(1.5 * two["h"], abs=0.1)   # "approximately 2 U" and "3 U"


def test_bays_reserve_one_size_for_each_unit_they_accept():
    d = load()
    for cid in ("base", "ac-5000-p"):
        for bid, b in bays_in(d, cid).items():
            for ref in b["accepts"]:
                c = comp(ref_name(ref))["size"]
                assert b["size"]["w"] == pytest.approx(c["w"], abs=0.3), (bid, ref)
                assert b["size"]["h"] == pytest.approx(c["h"], abs=0.3), (bid, ref)


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("part", sorted(ORDERS.values()))
def test_the_dcim_device_types_export_one_per_orderable_configuration_at_14_u(part):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for the device"
        doc = yaml.safe_load(f.read_text())
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part
        assert doc["u_height"] == 14


def test_no_other_ex6210_device_type_export_exists():
    got = {p.stem for p in (EXPORTS / "netbox/device-types/Juniper").glob("EX6210*.yaml")}
    assert got == set(ORDERS.values())


@pytest.mark.parametrize("name", sorted(PART_NUMBER))
def test_each_unit_exports_a_module_type_carrying_its_juniper_part_number(name):
    want = PART_NUMBER[name]
    found = []
    for target in ("netbox", "nautobot"):
        for f in (EXPORTS / target / "module-types" / "Juniper").glob("*.yaml"):
            doc = yaml.safe_load(f.read_text())
            if doc.get("part_number") == want and doc["model"].startswith(want):
                found.append(f.name)
    assert len(found) == 2, found
