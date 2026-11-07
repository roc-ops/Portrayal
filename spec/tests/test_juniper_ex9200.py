"""The Juniper EX9204, EX9208 and EX9214, from the three EX Switch Hardware Guides (published 2025-08-12, 2025-07-28 and 2025-07-28)
and the EX9200 Ethernet Switch Datasheet (1000432-022-EN, Aug 2022).

One device per chassis: `juniper/ex9204`, `ex9208` and `ex9214`. Base, redundant, AC, DC, bundle and spare (-CHAS) builds are
`orderable` configurations of the one device, because the guides draw one front panel for each chassis. The EX9200 line cards are a
family of their own and are not modelled: their slots show blank panels.

What the guides and the datasheet fix, and so what these tests hold:
  guide Table 7        the envelope: height, width, depth
  datasheet Table 7    the rack units (5, 8 and 16 U)
  guide Table 5        each configuration's Switch Fabric generation and count, Routing Engine generation and count, supply type and count
  datasheet ordering   the spare chassis EX92xx-CHAS3-S, EX9200-LC-SF-BLANK, the supplies, the fan trays and the air filters, by part number
  guide Figures 9-12   the craft interface of each chassis, and the slots it numbers
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"
INCH = 25.4

# model -> (rack units, height in, width in, depth in, slot bays in left-to-right or top-to-bottom order, airflow of the chassis)
CHASSIS = {
    "ex9204": (5, 8.7, 17.5, 24.5, ["lc2", "lc1", "sf1-lc0", "sf0"], "side"),
    "ex9208": (8, 14.0, 17.5, 24.5, ["lc5", "lc4", "lc3", "lc2", "lc1", "lc0", "sf1", "sf0"], "side"),
    "ex9214": (16, 27.8, 17.5, 31.08,
               ["lc0", "lc1", "lc2", "lc3", "lc4", "lc5", "sf0", "sf1", "sf2-lc6", "lc7", "lc8", "lc9", "lc10", "lc11"], "front-to-back"),
}

# configuration id -> (part numbers, Switch Fabric, count, Routing Engine, count, supply kind, count)   (guide Table 5, datasheet ordering table)
CONFIGS = {
    "ex9204": {
        "base3c-ac": (["EX9204-BASE3C-AC"], "ex9200-sf3", 1, "ex9200-re2", 1, "ac", 2),
        "red3c-ac": (["EX9204-RED3C-AC"], "ex9200-sf3", 2, "ex9200-re2", 2, "ac", 4),
        "red3c-dc": (["EX9204-RED3C-DC"], "ex9200-sf3", 2, "ex9200-re2", 2, "dc", 2),
        "base3b-ac": (["EX9204-BASE3B-AC"], "ex9200-sf2", 1, "ex9200-re2", 1, "ac", 2),
        "base3b-ac-t": (["EX9204-BASE3B-AC-T"], "ex9200-sf2", 1, "ex9200-re2", 1, "ac", 2),
        "ac-bnd2": (["EX9204-AC-BND2"], "ex9200-sf2", 1, "ex9200-re2", 1, "ac", 2),
        "red3b-ac": (["EX9204-RED3B-AC"], "ex9200-sf2", 2, "ex9200-re2", 2, "ac", 4),
        "red3b-ac-t": (["EX9204-RED3B-AC-T"], "ex9200-sf2", 2, "ex9200-re2", 2, "ac", 4),
        "red3b-dc": (["EX9204-RED3B-DC"], "ex9200-sf2", 2, "ex9200-re2", 2, "dc", 4),
        "base3a-ac": (["EX9204-BASE3A-AC"], "ex9200-sf2", 1, "ex9200-re", 1, "ac", 2),
        "ac-bnd1": (["EX9204-AC-BND1"], "ex9200-sf2", 1, "ex9200-re", 1, "ac", 2),
        "redund3a-ac": (["EX9204-REDUND3A-AC"], "ex9200-sf2", 2, "ex9200-re", 2, "ac", 2),
        "redund3a-dc": (["EX9204-REDUND3A-DC"], "ex9200-sf2", 2, "ex9200-re", 2, "dc", 2),
        "base-ac": (["EX9204-BASE-AC"], "ex9200-sf", 1, "ex9200-re", 1, "ac", 2),
        "redund-ac": (["EX9204-REDUND-AC"], "ex9200-sf", 2, "ex9200-re", 2, "ac", 4),
        "redund-dc": (["EX9204-REDUND-DC"], "ex9200-sf", 2, "ex9200-re", 2, "dc", 2),
    },
    "ex9208": {
        "base3c-ac": (["EX9208-BASE3C-AC"], "ex9200-sf3", 1, "ex9200-re2", 1, "ac", 3),
        "red3c-ac": (["EX9208-RED3C-AC"], "ex9200-sf3", 2, "ex9200-re2", 2, "ac", 4),
        "red3c-dc": (["EX9208-RED3C-DC"], "ex9200-sf3", 2, "ex9200-re2", 2, "dc", 4),
        "base3b-ac": (["EX9208-BASE3B-AC"], "ex9200-sf2", 1, "ex9200-re2", 1, "ac", 3),
        "base3b-ac-t": (["EX9208-BASE3B-AC-T"], "ex9200-sf2", 1, "ex9200-re2", 1, "ac", 3),
        "red3b-ac": (["EX9208-RED3B-AC"], "ex9200-sf2", 2, "ex9200-re2", 2, "ac", 4),
        "red3b-ac-t": (["EX9208-RED3B-AC-T"], "ex9200-sf2", 2, "ex9200-re2", 2, "ac", 4),
        "red3b-dc": (["EX9208-RED3B-DC"], "ex9200-sf2", 2, "ex9200-re2", 2, "dc", 4),
        "base3a-ac": (["EX9208-BASE3A-AC"], "ex9200-sf2", 1, "ex9200-re", 1, "ac", 3),
        "redund3a-ac": (["EX9208-REDUND3A-AC"], "ex9200-sf2", 2, "ex9200-re", 2, "ac", 4),
        "redund3a-dc": (["EX9208-REDUND3A-DC"], "ex9200-sf2", 2, "ex9200-re", 2, "dc", 4),
        "base-ac": (["EX9208-BASE-AC"], "ex9200-sf", 1, "ex9200-re", 1, "ac", 3),
        "redund-ac": (["EX9208-REDUND-AC"], "ex9200-sf", 2, "ex9200-re", 2, "ac", 4),
        "redund-dc": (["EX9208-REDUND-DC"], "ex9200-sf", 2, "ex9200-re", 2, "dc", 4),
    },
    "ex9214": {
        "base3c-ac": (["EX9214-BASE3C-AC"], "ex9200-sf3", 3, "ex9200-re2", 1, "ac", 2),
        "red3c-ac": (["EX9214-RED3C-AC"], "ex9200-sf3", 3, "ex9200-re2", 2, "ac", 4),
        "red3c-dc": (["EX9214-RED3C-DC"], "ex9200-sf3", 3, "ex9200-re2", 2, "dc", 4),
        "base3b-ac": (["EX9214-BASE3B-AC"], "ex9200-sf2", 2, "ex9200-re2", 1, "ac", 3),
        "base3b-ac-t": (["EX9214-BASE3B-AC-T"], "ex9200-sf2", 2, "ex9200-re2", 1, "ac", 3),
        "red3b-ac": (["EX9214-RED3B-AC"], "ex9200-sf2", 3, "ex9200-re2", 2, "ac", 4),
        "red3b-ac-t": (["EX9214-RED3B-AC-T"], "ex9200-sf2", 3, "ex9200-re2", 2, "ac", 4),
        "red-3b-ac": (["EX9214-RED-3B-AC"], "ex9200-sf2", 3, "ex9200-re2", 2, "ac", 4),
        "red3b-dc": (["EX9214-RED3B-DC"], "ex9200-sf2", 3, "ex9200-re2", 2, "dc", 4),
        "base3a-ac": (["EX9214-BASE3A-AC"], "ex9200-sf2", 2, "ex9200-re", 1, "ac", 3),
        "redund3a-ac": (["EX9214-REDUND3A-AC"], "ex9200-sf2", 3, "ex9200-re", 2, "ac", 4),
        "redund3a-dc": (["EX9214-REDUND3A-DC"], "ex9200-sf2", 3, "ex9200-re", 2, "dc", 4),
        "base3-ac": (["EX9214-BASE3-AC"], "ex9200-sf", 2, "ex9200-re", 1, "ac", 3),
        "redund3-dc": (["EX9214-REDUND3-DC"], "ex9200-sf", 3, "ex9200-re", 2, "dc", 4),
        "redund3-ac": (["EX9214-REDUND3-AC"], "ex9200-sf", 3, "ex9200-re", 2, "ac", 4),
    },
}
SPARE = {"ex9204": "EX9204-CHAS3-S", "ex9208": "EX9208-CHAS3-S", "ex9214": "EX9214-CHAS3-S"}

PSU = {
    "ex9204": {"ac": "ex9200-pwr-mx480-2520-ac", "dc": "ex9200-pwr-mx480-2400-dc"},
    "ex9208": {"ac": "ex9200-pwr-mx480-2520-ac", "dc": "ex9200-pwr-mx480-2400-dc"},
    "ex9214": {"ac": "ex9214-pwr-mx960-4100-ac", "dc": "ex9214-pwr-mx960-4100-dc"},
}
# the datasheet's ordering table: component -> the spare part number it is ordered under
SPARE_PART = {
    "ex9200-lc-sf-blank": "EX9200-LC-SF-BLANK",
    "ex9200-pwr-mx480-2520-ac": "PWR-MX480-2520-AC-S",
    "ex9200-pwr-mx480-2400-dc": "PWR-MX480-2400-DC-S",
    "ex9214-pwr-mx960-4100-ac": "PWR-MX960-4100-AC-S",
    "ex9214-pwr-mx960-4100-dc": "PWR-MX960-4100-DC-S",
    "ex9214-ffantray-mx960-hc": "FFANTRAY-MX960-HC-S",
    "ex9214-fltr-kit-mx960": "FLTR-KIT-MX960-S",
}
# reused from the MX line, by the part number the datasheet names for the EX chassis
REUSED = {
    "ex9204": {"fan-tray": ("mx240-fan-tray", "FANTRAY-MX240-HC"), "air-filter": ("mx240-air-filter", "MX240 Air Filter")},
    "ex9208": {"fan-tray": ("mx480-fan-tray", "MX480 High-Capacity Fan Tray"), "air-filter": ("mx480-air-filter", "MX480 Air Filter")},
}
LINE_CARDS = ["EX9200-2C-8XS", "EX9200-4QS", "EX9200-6QS", "EX9200-MPC", "EX9200-10XS-MIC", "EX9200-20F-MIC", "EX9200-40T-MIC",
              "EX9200-12QS", "EX9200-15C", "EX9200-32XS", "EX9200-40T", "EX9200-40F", "EX9200-40F-M", "EX9200-40XS"]
MODELS = sorted(CHASSIS)


def load(model):
    return yaml.safe_load((DEVICES / model / "device.yaml").read_text())


def comp(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def skin(name):
    return (COMP / name / "v1" / "skins" / "default.svg").read_text()


def parts(dev, view, key):
    return (dev["views"][view].get("components") or {}).get(key) or []


def ref_name(ref):
    return ref.split("/")[-1].split("@")[0]


def bays(dev):
    return {b["id"]: b for view in ("front", "rear") for b in parts(dev, view, "bays")}


def seated(dev, cid):
    """bay path -> component name, '' for an open bay. A module's own bay (`sf0/re`) takes its default unless the configuration says."""
    cfg = dev["configurations"][cid]
    over = cfg.get("bays") or {}
    out = {}
    for bid, b in bays(dev).items():
        ref = over[bid] if bid in over else b.get("default")
        out[bid] = ref_name(ref) if ref else ""
        if ref:
            for inner, ib in (comp(ref_name(ref)).get("bays") or {}).items():
                path = f"{bid}/{inner}"
                iref = over[path] if path in over else ib.get("default")
                out[path] = ref_name(iref) if iref else ""
    return out


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("model", MODELS)
def test_the_envelope_is_table_7_and_the_rack_units_are_the_datasheets(model):
    ru, h, w, d, _, airflow = CHASSIS[model]
    ch = load(model)["chassis"]
    assert ch["ru"] == ru
    assert ch["height"] == pytest.approx(h * INCH, abs=0.2)
    assert ch["width"] == pytest.approx(w * INCH, abs=0.2)
    assert ch["depth"] == pytest.approx(d * INCH, abs=0.2)
    assert ch["airflow"] == airflow
    assert ch["height"] <= ru * 44.45 + 0.1, "the body fits its rack units"
    assert ch["width"] < 480, "the mounting flanges are not drawn"


@pytest.mark.parametrize("model", MODELS)
def test_the_faces_are_sized_from_the_envelope(model):
    d = load(model)
    ch = d["chassis"]
    for view in ("front", "rear"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["height"]}
    for view in ("top", "bottom"):
        assert d["views"][view]["size"] == {"w": ch["width"], "h": ch["depth"]}
    for view in ("left", "right"):
        assert d["views"][view]["size"] == {"w": ch["depth"], "h": ch["height"]}


@pytest.mark.parametrize("model", MODELS)
def test_the_device_is_named_as_the_guide_prints_it(model):
    d = load(model)
    assert d["manufacturer"] == "Juniper" and d["model"] == model.upper()
    assert d["portfolio"] == {"line": "EX Series", "family": "EX9200"}


# --- the slots and ports, per face -------------------------------------------

@pytest.mark.parametrize("model", MODELS)
def test_front_has_the_guides_slots_in_order_and_each_prints_its_number(model):
    d = load(model)
    want = CHASSIS[model][4]
    slots = [b for b in parts(d, "front", "bays") if b["id"] in want]
    assert [b["id"] for b in slots] == want
    along = 0 if model == "ex9214" else 1
    pos = [b["at"][along] for b in slots]
    assert pos == sorted(pos), "the slots run top to bottom (left to right on the EX9214)"
    assert len({tuple(sorted(b["size"].items())) for b in slots}) == 1, "every slot reserves the one card envelope"
    printed = {s["for"]: s["text"] for s in d["views"]["front"].get("silkscreen") or [] if s.get("for") in want}
    if model != "ex9214":      # the EX9214 prints its slot numbers on the craft interface and the cards, not on the chassis
        assert set(printed) == set(want)


@pytest.mark.parametrize("model", MODELS)
def test_every_line_card_slot_takes_the_blank_and_no_mx_card(model):
    d = load(model)
    for b in parts(d, "front", "bays"):
        if b["id"].startswith("lc"):
            assert [ref_name(r) for r in b["accepts"]] == ["ex9200-lc-sf-blank"], b["id"]
            assert ref_name(b["default"]) == "ex9200-lc-sf-blank"


@pytest.mark.parametrize("model", MODELS)
def test_the_switch_fabric_slots_take_the_three_generations_and_the_shared_slot_also_the_blank(model):
    d = load(model)
    fabrics = {"ex9200-sf3", "ex9200-sf2", "ex9200-sf"}
    for b in parts(d, "front", "bays"):
        if b["id"].startswith("sf"):
            got = {ref_name(r) for r in b["accepts"]}
            shared = b["id"] in ("sf1-lc0", "sf2-lc6") or (model == "ex9208" and b["id"] == "sf1")
            assert got == fabrics | ({"ex9200-lc-sf-blank"} if shared else set()), b["id"]


@pytest.mark.parametrize("name,xge,clock", [("ex9200-sf", 1, "ext-clk"), ("ex9200-sf2", 1, "ext-clk"), ("ex9200-sf3", 2, "ext-clk")])
def test_a_switch_fabric_module_has_its_xge_ports_and_one_rj45_clock_port(name, xge, clock):
    c = comp(name)
    by_id = {p["id"]: p for p in c["parts"]}
    cages = [p for p in c["parts"] if p["id"].startswith("xge-")]
    assert len(cages) == xge and {ref_name(p["ref"]) for p in cages} == {"sfp"}
    assert ref_name(by_id[clock]["ref"]) == "rj45"
    assert c["groups"]["xge"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert [p["at"][0] for p in cages] == sorted(p["at"][0] for p in cages)
    if xge == 2:
        assert cages[1]["at"][0] - cages[0]["at"][0] >= 14.5, "two cages do not overlap"
    assert list(c["bays"]) == ["re"]
    want = {"ex9200-sf": {"ex9200-re"}, "ex9200-sf2": {"ex9200-re", "ex9200-re2"}, "ex9200-sf3": {"ex9200-re", "ex9200-re2"}}[name]
    assert {ref_name(r) for r in c["bays"]["re"]["accepts"]} == want


@pytest.mark.parametrize("name,jacks,usb", [("ex9200-re", ["aux", "console", "ethernet"], 1), ("ex9200-re2", ["aux", "console", "mgmt"], 2)])
def test_a_routing_engine_has_aux_console_and_management_jacks_and_its_usb_ports(name, jacks, usb):
    c = comp(name)
    by_id = {p["id"]: p for p in c["parts"]}
    xs = [by_id[j]["at"][0] for j in jacks]
    assert xs == sorted(xs) and len(set(xs)) == 3, "AUX, CONSOLE and the Ethernet jack read left to right"
    assert ref_name(by_id[jacks[0]]["ref"]) == ref_name(by_id[jacks[1]]["ref"]) == "rj45"
    assert by_id[jacks[0]]["attrs"]["media"] == by_id[jacks[1]]["attrs"]["media"] == "rj45-serial"
    assert len([p for p in c["parts"] if ref_name(p["ref"]) == "usb-a"]) == usb
    assert c["groups"]["mgmt"]["role"] == "management"
    for word in ("AUX", "CONSOLE"):
        assert f">{word}</text>" in skin(name)


@pytest.mark.parametrize("model", MODELS)
def test_the_supply_bays_are_numbered_pem0_to_pem3_left_to_right_and_print_their_legends(model):
    d = load(model)
    pems = [b for b in parts(d, "rear", "bays") if b["id"].startswith("pem")]
    assert [b["id"] for b in pems] == ["pem0", "pem1", "pem2", "pem3"]
    xs = [b["at"][0] for b in pems]
    assert xs == sorted(xs) and len({b["at"][1] for b in pems}) == 1
    assert [b["rel-pos"] for b in pems] == [0, 1, 2, 3]
    legends = {s["for"]: s["text"].replace(" ", "") for s in d["views"]["rear"]["silkscreen"] if s["for"].startswith("pem")}
    assert legends == {f"pem{n}": f"PEM{n}" for n in range(4)}
    for a, b in zip(pems, pems[1:]):
        assert a["at"][0] + a["size"]["w"] <= b["at"][0] + 0.01, "the supply bays do not overlap"


def test_the_ex9214_has_four_chassis_c20_inlets_one_per_supply():
    d = load("ex9214")
    inlets = [p for p in parts(d, "rear", "placements") if p["id"].startswith("inlet-")]
    assert [p["id"] for p in inlets] == ["inlet-0", "inlet-1", "inlet-2", "inlet-3"]
    assert {ref_name(p["ref"]) for p in inlets} == {"c20-inlet"}
    assert [p["for"] for p in inlets] == ["pem0", "pem1", "pem2", "pem3"]


@pytest.mark.parametrize("model", ["ex9204", "ex9208"])
def test_the_rear_has_the_earthing_pair_at_0_625_in_and_two_esd_points(model):
    d = load(model)
    stud = [p for p in parts(d, "rear", "placements") if p["id"] == "ground-studs"][0]
    assert ref_name(stud["ref"]) == "mx-ground-stud-pair-5-8"
    assert comp("mx-ground-stud-pair-5-8")["size"]["w"] == pytest.approx(15.875 + 7.0, abs=0.01)   # guide: 0.625 in (15.86 mm) centres
    cut = [c for c in d["views"]["rear"]["panel"]["cutouts"] if c["id"].startswith("ground-stud")]
    assert abs(cut[1]["at"][1] - cut[0]["at"][1]) == pytest.approx(0.625 * INCH, abs=0.1)
    esd = [p for view in ("front", "rear") for p in parts(d, view, "placements") if ref_name(p["ref"]) == "esd-jack"]
    assert len(esd) == 2


# --- the craft interfaces ----------------------------------------------------

@pytest.mark.parametrize("model,slot_pairs", [("ex9204", 4), ("ex9208", 8), ("ex9214", 14)])
def test_each_craft_interface_has_the_lamps_the_guide_names(model, slot_pairs):
    els = comp(f"{model}-craft")["elements"]
    leds = {k for k, e in els.items() if e["class"] == "led"}
    slot_leds = [k for k in leds if k.startswith("led-slot-") or k.startswith(("led-sf0-", "led-sf1-", "led-lc"))]
    assert len(slot_leds) == 2 * slot_pairs
    assert {"led-alarm-minor", "led-alarm-major"} <= leds
    assert {f"led-pem{n}-{k}" for n in range(4) for k in ("ok", "fail")} <= leds
    assert {"led-re0-master", "led-re0-online", "led-re0-offline", "led-re1-master", "led-re1-online", "led-re1-offline"} <= leds
    assert els["led-alarm-minor"]["states"][0]["name"] == "yellow" and els["led-alarm-major"]["states"][0]["name"] == "red"
    assert model.upper() in skin(f"{model}-craft")


@pytest.mark.parametrize("model", MODELS)
def test_no_logo_is_drawn_and_its_place_is_reserved(model):
    d = load(model)
    craft = comp(f"{model}-craft")
    assert "logo-zone" in craft["elements"] and "logo-zone-2" in craft["elements"]
    assert 'id="logo-zone"' in skin(f"{model}-craft")
    names = [f"{model}-craft"] + [n for n in SPARE_PART if (COMP / n).exists()] + ["ex9200-sf", "ex9200-sf2", "ex9200-sf3", "ex9200-re", "ex9200-re2"]
    for n in names:
        text = skin(n).upper()
        assert "JUNIPER" not in text and "NETWORKS" not in text and ">JUNOS<" not in text, n
    for view in ("front", "rear"):
        words = " ".join(s.get("text", "") for s in d["views"][view].get("silkscreen") or []).upper()
        assert "JUNIPER" not in words and "NETWORKS" not in words


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("model", MODELS)
def test_every_order_in_table_5_and_the_spare_chassis_is_an_orderable_configuration_with_its_part_numbers(model):
    cfgs = load(model)["configurations"]
    orderable = {c: sorted(v["part-numbers"]) for c, v in cfgs.items() if v["kind"] == "orderable"}
    want = {c: sorted(v[0]) for c, v in CONFIGS[model].items()}
    want["chassis"] = [SPARE[model]]
    assert orderable == want
    base = [c for c, v in cfgs.items() if v["kind"] == "base"]
    assert base == ["base"] and cfgs["base"]["default"] is True and "part-numbers" not in cfgs["base"]
    names = [p for v in orderable.values() for p in v]
    assert len(names) == len(set(names)), "a part number belongs to one configuration"


@pytest.mark.parametrize("model", MODELS)
def test_each_configuration_seats_the_generation_and_the_counts_of_its_table_5_row(model):
    d = load(model)
    for cid, (_, sf, nsf, re_, nre, kind, npsu) in CONFIGS[model].items():
        s = seated(d, cid)
        fabrics = [v for k, v in s.items() if "/" not in k and v.startswith("ex9200-sf")]
        engines = [v for k, v in s.items() if k.endswith("/re") and v]
        supplies = [v for k, v in s.items() if k.startswith("pem") and v]
        assert fabrics == [sf] * nsf, (cid, fabrics)
        assert engines == [re_] * nre, (cid, engines)
        assert supplies == [PSU[model][kind]] * npsu, (cid, supplies)
        assert d["configurations"][cid]["power"] == kind


@pytest.mark.parametrize("model", MODELS)
def test_the_blanks_stand_in_the_slots_the_orders_leave_empty(model):
    d = load(model)
    for cid in CONFIGS[model]:
        s = seated(d, cid)
        for bid in CHASSIS[model][4]:
            if bid.startswith("lc"):
                assert s[bid] == "ex9200-lc-sf-blank", (cid, bid)
    s = seated(d, "base")
    assert [v for k, v in s.items() if k.startswith("lc")] == ["ex9200-lc-sf-blank"] * len([b for b in CHASSIS[model][4] if b.startswith("lc")])


@pytest.mark.parametrize("model", MODELS)
def test_a_dc_build_seats_dc_supplies_only_and_an_ac_build_ac_only(model):
    d = load(model)
    for cid, (*_, kind, _n) in CONFIGS[model].items():
        kinds = {v for k, v in seated(d, cid).items() if k.startswith("pem") and v}
        assert kinds == {PSU[model][kind]}, cid


@pytest.mark.parametrize("model", MODELS)
def test_the_spare_chassis_leaves_every_removable_bay_open_and_keeps_the_craft_interface_where_the_guide_has_it(model):
    s = seated(load(model), "chassis")
    bare = {k: v for k, v in s.items() if "/" not in k}
    assert {k for k, v in bare.items() if v} == {"craft"}
    assert all(v == "" for k, v in bare.items() if k != "craft")


@pytest.mark.parametrize("model", MODELS)
def test_the_cooling_and_supplies_state_matching_airflow(model):
    d = load(model)
    chassis = d["chassis"]["airflow"]
    for bid, b in bays(d).items():
        if bid.startswith("fan"):
            air = comp(ref_name(b["default"]))["attrs"]["airflow"]
            want = "side-to-side" if chassis == "side" else "front-to-back"
            assert air.startswith(want), (bid, air)
    if model != "ex9214":
        for kind in ("ac", "dc"):
            assert comp(PSU[model][kind])["attrs"]["airflow"].startswith("front-to-back")
    assert not [c for c, v in d["configurations"].items() if "airflow" in v], "the guides give one airflow per chassis"


@pytest.mark.parametrize("model", ["ex9204", "ex9208"])
def test_the_fan_tray_and_air_filter_are_the_mx_parts_the_datasheet_names_for_the_chassis(model):
    d = load(model)
    b = bays(d)
    for bay, (name, model_attr) in REUSED[model].items():
        assert [ref_name(r) for r in b[bay]["accepts"]] == [name]
        assert comp(name)["attrs"]["model"] == model_attr
        assert not (COMP / f"{model}-{bay}").exists()


def test_the_ex9214_fan_trays_and_air_filter_are_new_parts_because_the_mx960_has_none():
    d = load("ex9214")
    b = bays(d)
    assert [ref_name(b[k]["default"]) for k in ("fan-upper", "fan-lower")] == ["ex9214-ffantray-mx960-hc"] * 2
    assert ref_name(b["air-filter"]["default"]) == "ex9214-fltr-kit-mx960"
    assert comp("ex9214-ffantray-mx960-hc")["attrs"]["fans"] == 6
    assert not [p for p in COMP.iterdir() if p.name in ("mx960-fan-tray", "mx960-air-filter")]


@pytest.mark.parametrize("name", sorted(SPARE_PART))
def test_a_unit_is_ordered_under_the_part_number_the_datasheet_names(name):
    c = comp(name)
    assert c["kind"] == "module"
    assert [v["part"] for v in c["part-numbers"].values()] == [SPARE_PART[name]]
    assert "model" not in (c.get("attrs") or {}), "a module states its code in part-numbers, not in attrs.model"


@pytest.mark.parametrize("name,output", [("ex9200-pwr-mx480-2520-ac", 2400), ("ex9200-pwr-mx480-2400-dc", 2400),
                                         ("ex9214-pwr-mx960-4100-ac", 4100), ("ex9214-pwr-mx960-4100-dc", 4100)])
def test_a_supply_states_the_power_it_provides_as_an_output(name, output):
    attrs = comp(name)["attrs"]
    assert attrs["power-output-w"] == output
    assert not any(k.startswith("power-draw") for k in attrs)


@pytest.mark.parametrize("name,watts", [("ex9200-sf", 150), ("ex9200-sf2", 155), ("ex9200-re", 90), ("ex9200-re2", 90)])
def test_the_host_modules_state_the_draw_of_table_24(name, watts):
    assert comp(name)["attrs"]["power-draw-max-w"] == watts


def test_the_sf3_draw_is_the_highest_per_ambient_figure_and_the_typical_one_is_table_24s():
    a = comp("ex9200-sf3")["attrs"]
    assert (a["power-draw-max-w"], a["power-draw-typical-w"]) == (425, 245)


def test_the_two_mx_supply_families_the_ex_guides_do_not_name_are_not_reused():
    """The EX9204 and EX9208 supplies are the 2520 W AC and 2400 W DC ones; the 1590 W normal-capacity MX supplies are other parts."""
    for model in ("ex9204", "ex9208"):
        for b in parts(load(model), "rear", "bays"):
            if b["id"].startswith("pem"):
                assert not [r for r in b["accepts"] if ref_name(r) in ("mx240-psu-ac", "mx480-psu-ac", "mx240-psu-dc")]


# --- the left-out family -----------------------------------------------------

@pytest.mark.parametrize("model", MODELS)
def test_the_line_cards_are_listed_as_left_out_by_part_number_and_not_built(model):
    gap = [g for g in load(model)["gaps"] if g["what"] == "line-cards"][0]
    for part in LINE_CARDS:
        assert part in gap["wanted"], part
    assert not [p for p in COMP.iterdir() if p.name.startswith(("ex9200-40", "ex9200-32", "ex9200-12", "ex9200-15", "ex9200-6qs",
                                                                 "ex9200-4qs", "ex9200-2c", "ex9200-mpc", "ex9200-10xs", "ex9200-20f"))]


# --- the DCIM export ---------------------------------------------------------

def _orders():
    for model in MODELS:
        ru = CHASSIS[model][0]
        for part in [p for v in CONFIGS[model].values() for p in v[0]] + [SPARE[model]]:
            yield pytest.param(model, part, ru, id=part)


@pytest.mark.parametrize("model,part,ru", list(_orders()))
def test_the_dcim_device_types_export_one_per_orderable_part_number_at_the_rack_units_of_the_chassis(model, part, ru):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "device-types" / "Juniper" / f"{part}.yaml"
        assert f.exists(), f"{f} is missing - run dcim_export.py for the device"
        doc = yaml.safe_load(f.read_text())
        assert doc["u_height"] == ru
        assert doc["manufacturer"] == "Juniper"
        assert doc["model"] == part and doc["slug"] == "juniper-" + part.lower()


def test_the_base_configuration_exports_no_device_type():
    for target in ("netbox", "nautobot"):
        names = {p.stem for m in MODELS for p in (EXPORTS / target / "device-types" / "Juniper").glob(f"{m.upper()}-*.yaml")}
        assert not {m.upper() for m in MODELS} & names
        expected = {p for m in MODELS for p in [q for v in CONFIGS[m].values() for q in v[0]] + [SPARE[m]]}
        assert names == expected


@pytest.mark.parametrize("name", sorted(SPARE_PART))
def test_the_module_types_export_under_the_datasheets_part_numbers(name):
    for target in ("netbox", "nautobot"):
        f = EXPORTS / target / "module-types" / "Juniper" / f"{SPARE_PART[name]}.yaml"
        assert f.exists(), f
        assert yaml.safe_load(f.read_text())["part_number"] == SPARE_PART[name]
