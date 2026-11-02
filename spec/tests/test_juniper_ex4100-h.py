"""The Juniper EX4100-H-12MP, -24MP and -24F, from the EX4100-H Switch Hardware Guide (published 2026-10-01).

One device per front panel: the three models share no front (a 12-jack upright box, a 24-jack 1RU box and a 24-cage
1RU box). The 24MP and 24F share their rear (two supply slots) but not their supplies, and the 12MP has no slot at
all: its two supplies are separate boxes wired to connectors on its front.

What the guide fixes, and so what these tests hold:
  Tables 9, 11, 13, 14        the envelope of each model
  Tables 8, 10, 12            the model number of each switch (the guide names no switch SKU for a DC build)
  Tables 23 to 25, 27, 28,
  33 to 36                    the supply model numbers, their output power and the slot each model has
  Figures 1, 3 and 5          the ports, their count and numbering, and what else is on the front
  Figures 4 and 6             what is on the rear, and the slot and blank
  Table 7                     how the 12MP mounts: a desktop box by default, with four other kits that the library
                              cannot say (one mount value per device), recorded as a gap
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/juniper"
COMP = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

# Tables 9, 11, 13 (centimetres as printed) and the figures
MODELS = {
    "ex4100-h-12mp": {"part": "EX4100-H-12MP", "w": 111.7, "h": 152.4, "d": 134.0, "kg": 2.37, "ru": None,
                      "jacks": 12, "cages": 0, "u": 0.0},
    "ex4100-h-24mp": {"part": "EX4100-H-24MP", "w": 439.0, "h": 43.3, "d": 379.9, "kg": 6.92, "ru": 1,
                      "jacks": 24, "cages": 0, "u": 1.0},
    "ex4100-h-24f": {"part": "EX4100-H-24F", "w": 439.0, "h": 43.3, "d": 379.9, "kg": 8.07, "ru": 1,
                     "jacks": 0, "cages": 24, "u": 1.0},
}
DEVICES = sorted(MODELS)
RACK = ["ex4100-h-24f", "ex4100-h-24mp"]
# Tables 24, 25, 34 and 35 (model numbers), 27 and 28 (output power), 15 (weight)
PSUS = {
    "ex4100-h-24mp": {"ac": ("ex4100-h-jpsu-340w-ac", "JPSU-H-340W-AC", 340), "dc": ("ex4100-h-24mp-dc-psu", "EX4100-H-24MP-DC-PSU", 340)},
    "ex4100-h-24f": {"ac": ("ex4100-h-jpsu-90w-ac", "JPSU-H-90W-AC", 90), "dc": ("ex4100-h-24f-dc-psu", "EX4100-H-24F-DC-PSU", 90)},
}


def load_device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def load_component(name):
    return yaml.safe_load((COMP / name / "v1/contract.yaml").read_text())


def placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def bays(dev, view):
    return (dev["views"][view].get("components") or {}).get("bays") or []


def by_id(dev, view):
    return {p["id"]: p for p in placements(dev, view)}


def silk_texts(dev, view):
    return [s.get("text") for s in dev["views"][view].get("silkscreen") or [] if s.get("text")]


def prov(d):
    return " ".join(" ".join(str(v.get("note", v) if isinstance(v, dict) else v) for v in d["provenance"].values()).split())


# --- the envelope ------------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_envelope_is_the_guides_table(name):
    m = MODELS[name]
    ch = load_device(name)["chassis"]
    # abs=0.05 pins the centimetre figures: the inch-derived 43.18 mm height and 134.6 mm depth fail it
    assert ch["width"] == pytest.approx(m["w"], abs=0.05)
    assert ch["height"] == pytest.approx(m["h"], abs=0.05)
    assert ch["depth"] == pytest.approx(m["d"], abs=0.05)
    assert ch["weight-kg"] == pytest.approx(m["kg"], abs=0.01)
    if m["ru"]:
        assert ch["ru"] == m["ru"] and ch.get("mount", "rack") == "rack"
    else:
        assert "ru" not in ch


def test_the_12mp_mounts_as_a_desktop_box_the_guides_default():
    d = load_device("ex4100-h-12mp")
    assert d["chassis"]["mount"] == "desktop"
    gap = next(g for g in d["gaps"] if g["what"] == "mounting-kits")
    note = " ".join(gap["note"].split())
    for kit in ("EX4100-H-12-DRK", "EX4100-H-12-MMK", "EX4100-H-12-RMK", "EX4100-H-12-WMK", "EX4100-H-12-RM-DRK"):
        assert kit in note
    assert kit_refs(d) == []


@pytest.mark.parametrize("name", RACK)
def test_the_rack_models_mount_flush_in_two_posts(name):
    ch = load_device(name)["chassis"]
    assert [p["name"] for p in ch["ears"]["positions"]] == ["flush"]
    assert ch["ears"]["positions"][0]["default"] is True
    # the guide gives no rack depth, preset or rail depth for EX4100-H-2P-RMK, -4P-RMK or -4P-TL-RMK, so no kit is listed
    assert kit_refs(load_device(name)) == []


def kit_refs(dev):
    return [k["ref"] for k in dev["chassis"].get("kits", [])]


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


# --- the front ports, per face ------------------------------------------------

def test_the_12mp_has_twelve_jacks_numbered_from_zero_as_printed_with_the_even_number_on_the_left():
    d = load_device("ex4100-h-12mp")
    pl = by_id(d, "front")
    for i in range(12):
        p = pl[f"port-{i}"]
        assert p["ref"] == "common/rj45-ganged-eth@1" and p["rel-pos"] == i
        assert p["group"] == ("rj45-mg" if i < 4 else "rj45-gbe")
        # contacts toward the middle of the face: the left column turned 90, the right 270
        assert p["rotate"] == (90 if i % 2 == 0 else 270)
    assert not [k for k in pl if k.startswith("port-") and int(k[5:]) >= 12]
    for i in range(0, 12, 2):
        assert pl[f"port-{i}"]["at"][0] < pl[f"port-{i + 1}"]["at"][0]
        assert pl[f"port-{i}"]["at"][1] == pl[f"port-{i + 1}"]["at"][1]
    texts = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
             if str(s.get("for", "")).startswith("port-") and s.get("text")}
    assert texts == {f"port-{i}": str(i) for i in range(12)}
    g = d["groups"]
    assert g["rj45-mg"]["attrs"]["speed"] == "2.5g" and g["rj45-gbe"]["attrs"]["speed"] == "1g"
    assert g["rj45-mg"]["attrs"]["poe"].startswith("802.3bt") and g["rj45-gbe"]["attrs"]["poe"].startswith("802.3bt")


def test_the_12mp_cages_are_four_in_one_column_uplink_over_vcp():
    pl = by_id(load_device("ex4100-h-12mp"), "front")
    cages = [pl[i] for i in ("uplink-0", "uplink-1", "vcp-0", "vcp-1")]
    assert {c["ref"] for c in cages} == {"std/sfp-ganged@1"}
    assert {c["rotate"] for c in cages} == {90}
    assert len({c["at"][0] for c in cages}) == 1
    ys = [c["at"][1] for c in cages]
    assert ys == sorted(ys)
    assert [round(b - a, 2) for a, b in zip(ys, ys[1:])] == [14.25] * 3
    assert [pl[f"led-{g}-{i}-{s}"]["group"] for g in ("uplink", "vcp") for i in (0, 1) for s in "ab"] == \
        ["uplink-leds"] * 4 + ["vcp-leds"] * 4


def test_the_24mp_has_24_jacks_in_two_shells_with_the_even_number_on_top():
    d = load_device("ex4100-h-24mp")
    pl = by_id(d, "front")
    for i in range(24):
        p = pl[f"port-{i}"]
        assert p["ref"] == "common/rj45-ganged-eth@1" and p["rel-pos"] == i
        assert p["group"] == ("rj45-mg" if i < 8 else "rj45-gbe")
        assert p.get("rotate") == (180 if i % 2 == 0 else None)
    assert not [k for k in pl if k.startswith("port-") and int(k[5:]) >= 24]
    xs = sorted({p["at"][0] for k, p in pl.items() if k.startswith("port-")})
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert len(xs) == 12 and steps.count(13.97) == 10 and max(steps) > 20   # one gutter between the shells
    texts = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
             if str(s.get("for", "")).startswith("port-") and s.get("text")}
    assert texts == {f"port-{i}": str(i) for i in range(24)}
    g = d["groups"]
    assert g["rj45-mg"]["attrs"]["speed"] == "2.5g" and g["rj45-gbe"]["attrs"]["speed"] == "1g"
    shells = [x for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "jack-shell"]
    assert len([s for s in shells if s["id"] in ("shell-1", "shell-2")]) == 2


def test_the_24f_has_24_sfp_cages_in_two_banks_with_the_even_number_on_top():
    d = load_device("ex4100-h-24f")
    pl = by_id(d, "front")
    for i in range(24):
        p = pl[f"port-{i}"]
        assert p["ref"] == "std/sfp-ganged@1" and p["rel-pos"] == i and p["group"] == "sfp"
        assert p.get("rotate") == (None if i % 2 == 0 else 180)
    assert not [k for k in pl if k.startswith("port-") and int(k[5:]) >= 24]
    assert len([k for k in pl if k.startswith("led-sfp-")]) == 48
    texts = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
             if str(s.get("for", "")).startswith("port-") and s.get("text")}
    assert texts == {f"port-{i}": str(i) for i in range(24)}
    xs = sorted({p["at"][0] for k, p in pl.items() if k.startswith("port-")})
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert len(xs) == 12 and steps.count(14.7) == 10 and steps[5] > 19   # one gutter between the banks
    assert d["groups"]["sfp"]["attrs"] == {"media": "sfp", "speed": "1g"}
    assert "poe" not in d["groups"]["sfp"]["attrs"]


@pytest.mark.parametrize("name", RACK)
def test_the_24_port_models_have_two_groups_of_four_cages_two_by_two(name):
    pl = by_id(load_device(name), "front")
    for prefix in ("vcp", "uplink"):
        cages = [pl[f"{prefix}-{i}"] for i in range(4)]
        assert {c["ref"] for c in cages} == {"std/sfp-ganged@1"}
        assert [c["rel-pos"] for c in cages] == [0, 1, 2, 3]
        assert {c["group"] for c in cages} == {prefix}
        for col in range(2):
            upper, lower = cages[2 * col], cages[2 * col + 1]
            assert upper["at"][0] == lower["at"][0] and upper["at"][1] < lower["at"][1]
            assert not upper.get("rotate") and lower.get("rotate") == 180
        assert cages[2]["at"][0] - cages[0]["at"][0] == pytest.approx(14.25)
        assert len([i for i in pl if i.startswith(f"led-{prefix}-")]) == 8
    assert pl["uplink-0"]["at"][0] > pl["vcp-3"]["at"][0]


@pytest.mark.parametrize("name", DEVICES)
def test_the_front_has_the_guides_lamps_console_button_alarm_and_management_ports(name):
    d = load_device(name)
    pl = by_id(d, "front")
    assert {"led-sys", "led-alm", "led-mst", "led-cld", "led-spd", "led-dx", "led-en",
            "led-in0", "led-in1", "led-out", "led-psu-0", "led-psu-1"} <= set(pl)
    # the PoE lamp is not fitted to a model with no PoE ports (the note under Figure 19)
    assert ("led-poe" in pl) == (name != "ex4100-h-24f")
    assert pl["btn-mode"]["ref"] == "juniper/ex4100-h-mode-button@1"
    assert pl["btn-reset"]["ref"] == "common/reset-button@1"
    assert pl["usb-c"]["ref"] == "std/usb-c@1" and pl["usb-c"]["attrs"]["role"] == "console"
    assert pl["alarm"]["ref"] == "juniper/ex4100-h-alarm-connector@1"
    assert pl["usb"]["ref"] == "std/usb-a@1"
    assert pl["mgmt"]["ref"] in ("common/rj45-eth@1", "common/rj45-ganged-eth@1")
    assert pl["console-rj45"]["ref"] in ("std/rj45@2", "std/rj45-ganged@2")
    assert pl["console-rj45"]["attrs"]["role"] == "console"
    legends = set(silk_texts(d, "front"))
    assert {"SYS", "ALM", "MST", "CLD", "SPD", "DX", "EN", "CON", "RESET", "GND", "IN 0", "IN 1", "NO", "COM", "NC",
            "OUT", "PSU 0", "PSU 1", "EX4100-H"} <= legends
    assert ("POE" in legends) == (name != "ex4100-h-24f")
    assert ("MG PoE++" in legends) == (name != "ex4100-h-24f") and ("24F" in legends) == (name == "ex4100-h-24f")


def test_the_12mp_has_two_psu_connectors_not_supply_bays_and_an_earthing_pair():
    d = load_device("ex4100-h-12mp")
    pl = by_id(d, "front")
    assert pl["psu-0"]["ref"] == pl["psu-1"]["ref"] == "juniper/ex4100-h-psu-connector@1"
    assert pl["psu-0"]["at"][1] < pl["psu-1"]["at"][1]
    for view in d["views"]:
        assert not bays(d, view)
    decor = {x["id"]: x for x in d["views"]["front"]["panel"]["decor"]}
    # the two holes (15.8 mm apart, the 5/8 in lug pitch) are one placed pair of bare M5 holes, stood on end, inside the rings
    assert pl["ground-pair"]["ref"] == "common/ground-hole-pair-5-8-m5@1" and pl["ground-pair"]["rotate"] == 90
    assert not {"earth-hole-1", "earth-hole-2"} & set(decor)
    assert {decor["earth-ring-1"]["kind"], decor["earth-ring-2"]["kind"]} == {"earth-boss"}
    note = " ".join(next(g for g in d["gaps"] if g["what"] == "external-power-supplies")["note"].split())
    assert "JPSU-H-340W-E-AC" in note and "EX4100-H-12MP-DC-PSU" in note


@pytest.mark.parametrize("name", RACK)
def test_the_24_port_models_have_twelve_terminals_behind_the_door_for_two_supply_sections(name):
    d = load_device(name)
    pads = [p for p in placements(d, "front") if p["ref"] == "juniper/ex4100-h-terminal-pad@1"]
    assert len(pads) == 12 and {p["group"] for p in pads} == {"power-input"}
    ids = {p["id"] for p in pads}
    assert ids == {f"psu-{s}-{t}" for s in (0, 1) for t in ("l", "n", "g-ac", "dc-plus", "dc-minus", "g-dc")}
    texts = silk_texts(d, "front")
    for t in ("L", "N", "G", "DC+", "DC-"):
        assert texts.count(t) >= 2


# --- the rear ----------------------------------------------------------------

@pytest.mark.parametrize("name", RACK)
def test_the_rear_has_two_supply_bays_with_the_blank_over_the_second(name):
    d = load_device(name)
    bb = {b["id"]: b for b in bays(d, "rear")}
    assert list(bb) == ["psu-0", "psu-1"]
    ac, dc = PSUS[name]["ac"][0], PSUS[name]["dc"][0]
    assert bb["psu-0"]["accepts"] == [f"juniper/{ac}@1", f"juniper/{dc}@1"]
    assert bb["psu-0"]["default"] == f"juniper/{ac}@1"
    assert set(bb["psu-1"]["accepts"]) == {f"juniper/{ac}@1", f"juniper/{dc}@1", "juniper/ex4100-h-psu-blank@1"}
    assert bb["psu-1"]["default"] == "juniper/ex4100-h-psu-blank@1"
    assert {b["group"] for b in bb.values()} == {"psus"}
    assert d["groups"]["psus"]["attrs"]["redundancy"] == "n+1"
    pl = by_id(d, "rear")
    assert pl["esd-rear"]["ref"] == "common/esd-jack@1"
    decor = {x["id"]: x for x in d["views"]["rear"]["panel"]["decor"]}
    assert pl["ground-pair"]["ref"] == "common/ground-hole-pair-5-8-m5@1" and pl["ground-pair"]["rotate"] == 90
    assert not {"earth-hole-1", "earth-hole-2"} & set(decor)
    assert {"lock-slot", "earth-plate"} <= set(decor)


def test_the_24f_rear_is_the_24mps_turned_end_for_end():
    mp, f = load_device("ex4100-h-24mp"), load_device("ex4100-h-24f")
    mp_b = {b["id"]: b for b in bays(mp, "rear")}
    f_b = {b["id"]: b for b in bays(f, "rear")}
    assert mp_b["psu-0"]["at"][0] > 40 and f_b["psu-0"]["at"][0] < 20
    assert by_id(mp, "rear")["esd-rear"]["at"][0] < 30 and by_id(f, "rear")["esd-rear"]["at"][0] > 380


def test_the_12mp_rear_is_a_vented_plate_between_two_plates_with_mounting_holes():
    d = load_device("ex4100-h-12mp")
    decor = d["views"]["rear"]["panel"]["decor"]
    assert len([x for x in decor if x.get("kind") == "screw"]) == 6
    assert len([x for x in decor if x.get("kind") == "mounting-hole"]) == 4
    assert any(x.get("pattern") == "vent" for x in decor)
    assert not bays(d, "rear")


# --- the supplies and the blank ------------------------------------------------

@pytest.mark.parametrize("name", RACK)
def test_each_supply_is_the_guides_model_with_its_output_power_and_no_airflow(name):
    for kind, (comp, part, watts) in PSUS[name].items():
        c = load_component(comp)
        assert c["class"] == "psu" and c["kind"] == "module"
        assert part in c["part-numbers"] and c["attrs"]["power-output-w"] == watts
        assert "airflow" not in c["attrs"] and "fanless" in c["attrs"]["cooling"]
        assert c["attrs"]["role"] == ("ac-power-supply" if kind == "ac" else "dc-power-supply")
        assert c["size"]["h"] == 39.5
        # the handle is the photograph's green, not Juniper's orange or blue airflow handles
        assert any(f["color"] == "#a2dd35" for f in c["relief"]["features"])
        assert "led-out-ok" in c["elements"]


def test_the_ac_and_dc_340w_supplies_differ_by_the_labels_and_ten_millimetres_of_depth():
    ac, dc = load_component("ex4100-h-jpsu-340w-ac"), load_component("ex4100-h-24mp-dc-psu")
    assert ac["size"] == dc["size"]
    assert dc["body"]["depth"] - ac["body"]["depth"] == 10.0
    assert "AC INPUT" in (COMP / "ex4100-h-jpsu-340w-ac/v1/skins/default.svg").read_text()
    assert "DC INPUT" in (COMP / "ex4100-h-24mp-dc-psu/v1/skins/default.svg").read_text()


# --- the configurations ------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_each_model_has_one_orderable_configuration_with_the_guides_model_number(name):
    d = load_device(name)
    orderable = {k: v for k, v in d["configurations"].items() if v["kind"] == "orderable"}
    assert len(orderable) == 1
    (key, cfg), = orderable.items()
    assert cfg["default"] is True
    assert set(cfg["part-numbers"]) == {MODELS[name]["part"]}


@pytest.mark.parametrize("name", RACK)
def test_the_dc_build_is_an_example_because_the_guide_names_no_switch_sku(name):
    d = load_device(name)
    cfgs = d["configurations"]
    assert list(cfgs) == ["ac", "dc"]
    assert cfgs["dc"]["kind"] == "example" and cfgs["dc"]["power"] == "dc" and cfgs["ac"]["power"] == "ac"
    assert "part-numbers" not in cfgs["dc"]
    assert cfgs["dc"]["bays"] == {"psu-0": f"juniper/{PSUS[name]['dc'][0]}@1", "psu-1": "juniper/ex4100-h-psu-blank@1"}
    assert "bays" not in cfgs["ac"]
    assert "dc-build-sku" in {g["what"] for g in d["gaps"]}


def test_the_12mp_has_one_configuration():
    d = load_device("ex4100-h-12mp")
    assert list(d["configurations"]) == ["std"]


# --- the DCIM export ---------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_dcim_device_types_export_one_per_orderable_configuration(name):
    part = MODELS[name]["part"]
    for target in ("netbox", "nautobot"):
        files = sorted((EXPORTS / target / "device-types" / "Juniper").glob(f"{part}*.yaml"))
        assert [f.name for f in files] == [f"{part}.yaml"], f"{target}: {part} should export exactly one device type"
        doc = yaml.safe_load(files[0].read_text())
        assert doc["manufacturer"] == "Juniper" and doc["model"] == part
        assert doc["u_height"] == MODELS[name]["u"]
        # the two supply slots of a rack model are module bays; the 12MP has none
        assert [b["position"] for b in doc.get("module-bays") or []] == ([] if name == "ex4100-h-12mp" else ["psu-0", "psu-1"])
        if name == "ex4100-h-12mp":
            # the two PSU connectors land the external supplies' DC outputs
            assert [(p["name"], p["type"]) for p in doc["power-ports"]] == [("psu-0", "dc-terminal"), ("psu-1", "dc-terminal")]
            assert len(doc["interfaces"]) == 17


# --- the logo, the sources and the components --------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_vendor_wordmark_is_a_reserved_zone_not_text(name):
    d = load_device(name)
    drawn = [t.upper() for t in silk_texts(d, "front")]
    assert not any("JUNIPER" in t for t in drawn) and "NETWORKS" not in drawn and "MIST AI" not in drawn
    zones = [r for r in d["views"]["front"].get("regions") or [] if r.get("id") == "logo-zone"]
    assert len(zones) == 1
    assert zones[0]["size"]["w"] >= 20 and zones[0]["size"]["h"] >= 6


@pytest.mark.parametrize("name", DEVICES)
def test_the_sources_are_cited_and_the_gaps_recorded(name):
    d = load_device(name)
    text = prov(d)
    assert "EX4100-H Switch Hardware Guide" in text and "published 2026-10-01" in text
    ref = d["references"][0]
    assert ref["url"].endswith("/ex4100-h/ex4100-h.pdf") and len(ref["sha256"]) == 64
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4100-H"}
    assert d["manufacturer"] == "Juniper" and d["model"] == MODELS[name]["part"]
    gaps = {g["what"] for g in d["gaps"]}
    assert "label-plates" in gaps and "ground-pair-pitch" in gaps and "ground-hole-seat" not in gaps
    # the studio photograph and the guide's figure were both looked at, and the drawing's conflicts are said
    assert "studio photographs" in text


def test_the_340w_ac_supply_is_drawn_with_the_photographs_ac_label_not_the_guides_dc_one():
    skin = (COMP / "ex4100-h-jpsu-340w-ac/v1/skins/default.svg").read_text()
    assert ">AC INPUT<" in skin
    assert ">DC INPUT<" not in skin


def test_the_12mp_label_prints_two_hazard_icons():
    front = load_device("ex4100-h-12mp")["views"]["front"]
    box = next(d for d in front["panel"]["decor"] if d["id"] == "hazard-box")
    x0, x1 = box["at"][0], box["at"][0] + box["size"][0]
    y0, y1 = box["at"][1], box["at"][1] + box["size"][1]
    icons = [m for m in front["silkscreen"] if m.get("id") in ("hazard-triangle", "hazard-hand")]
    inside = [m for m in icons if x0 < m["at"][0] < x1 and y0 < m["at"][1] < y1]
    assert {m["id"] for m in inside} >= {"hazard-triangle", "hazard-hand"}
    # one on each half of the yellow label
    assert min(m["at"][0] for m in inside) < (x0 + x1) / 2 < max(m["at"][0] for m in inside)


def test_the_guides_table_68_48mp_is_named_and_not_modelled():
    assert not (DEV / "ex4100-h-48mp").exists()
    assert "EX4100-H-48MP" in prov(load_device("ex4100-h-24mp"))


def test_this_slice_adds_these_components_and_no_other():
    names = sorted(p.name for p in COMP.glob("ex4100-h-*"))
    assert names == ["ex4100-h-24f-dc-psu", "ex4100-h-24mp-dc-psu", "ex4100-h-alarm-connector",
                     "ex4100-h-jpsu-340w-ac", "ex4100-h-jpsu-90w-ac", "ex4100-h-mode-button",
                     "ex4100-h-psu-blank", "ex4100-h-psu-connector", "ex4100-h-terminal-pad"]
