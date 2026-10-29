"""The Cisco Catalyst 2960-S family: what each model's own guide states, held in the library.

Read from the Catalyst 2960-S Switch Hardware Installation Guide (OL-19732-04): Table 1-1 for the
models, the front and rear figures of chapter 1, and the appendix's specification tables 1-2 and 1-3
(the appendix restarts its table numbers). Each device is checked against the row of its own model.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
COMPONENTS = ROOT / "library/components/cisco"
EXPORTS = ROOT / "library/exports"

BLANK = "cisco/c2960s-flexstack-blank@1"


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def component(name):
    return yaml.safe_load((COMPONENTS / name / "v1" / "contract.yaml").read_text())


def placements(d, view):
    return d["views"][view]["components"].get("placements") or []


def bays(d, view="rear"):
    return {b["id"]: b for b in d["views"][view]["components"].get("bays") or []}


def ports(d, group):
    return [p for p in placements(d, "front") if p.get("group") == group]


def by_id(d, view):
    return {p["id"]: p for p in placements(d, view)}


# --- the WS-C2960S-48FPD-L: Table 1-1, Figure 1-1, spec Table 1-2 ----------------------


def test_48fpd_envelope_is_spec_table_1_2():
    """H x D x W 1.75 x 15.19 x 17.5 in (4.45 x 38.6 x 44.5 cm), applies to all PoE switches."""
    c = device("ws-c2960s-48fpd")["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (444.5, 44.45, 386.0, 1)
    assert c["weight-kg"] == 5.89  # 13 lb (5.89 kg), the 48FPD-L's own row
    assert c["power"] == "ac"


def test_48fpd_front_has_forty_eight_rj45_numbered_as_printed_and_two_sfp_plus():
    """Table 1-1: 48 10/100/1000 PoE+ ports and 2 SFP+ module slots, numbered 49 and 50 (PDF p5 note)."""
    d = device("ws-c2960s-48fpd")
    rj45 = ports(d, "rj45")
    assert [p["id"] for p in rj45] == [f"port-{n}" for n in range(1, 49)]
    assert {p["ref"] for p in rj45} == {"std/rj45-ganged@2"}
    sfp = {p["id"]: p for p in ports(d, "sfp-plus")}
    assert set(sfp) == {"port-49", "port-50"}
    assert {p["ref"] for p in sfp.values()} == {"std/sfp@1"}
    # "The first member of the pair (port 1) is above the second member (port 2)."
    assert rj45[0]["at"][0] == rj45[1]["at"][0] and rj45[0]["at"][1] < rj45[1]["at"][1]


def test_48fpd_front_has_the_usb_and_console_ports_the_figure_names():
    """Figure 1-1 callouts 4 to 7: USB Type A, USB mini-Type B console, RJ-45 console, Ethernet management."""
    d = device("ws-c2960s-48fpd")
    p = by_id(d, "front")
    assert p["usb-a"]["ref"] == "std/usb-a@1"
    assert p["console-usb"]["ref"] == "std/mini-usb@1"
    assert p["console-usb"]["attrs"]["role"] == "console"
    assert p["console"]["attrs"]["media"] == "rj45-serial"
    assert p["mgmt"]["attrs"]["media"] == "rj45"
    assert not any(g["what"] == "usb-console-jack" for g in d.get("gaps", []))


def test_48fpd_front_lamps_are_the_guides_switch_leds():
    """Figure 1-7: System, RPS, Master, Status, Duplex, Speed, Stack and PoE lamps."""
    d = device("ws-c2960s-48fpd")
    lamps = {p["id"] for p in placements(d, "front") if p.get("group") in ("leds", "mode-leds")}
    assert {"led-system", "led-rps", "led-master", "led-stat", "led-duplx", "led-speed",
            "led-stack", "led-poe"} <= lamps


def test_48fpd_rear_has_the_flexstack_slot_seating_its_blank_by_default():
    """Figures 1-10/1-11: the slot has a cover, removed only to fit the module (PDF p31)."""
    d = device("ws-c2960s-48fpd")
    b = bays(d)
    assert set(b) == {"flexstack-slot"}
    assert b["flexstack-slot"]["accepts"] == [BLANK]
    assert b["flexstack-slot"]["default"] == BLANK


def test_the_flexstack_blank_has_no_invented_part_number():
    c = component("c2960s-flexstack-blank")
    assert "part-numbers" not in c
    assert c["class"] == "blank"
    assert c["attrs"]["model"] == "FlexStack slot blank cover"


def test_48fpd_power_is_built_in_with_a_chassis_inlet_and_no_supply_bay():
    d = device("ws-c2960s-48fpd")
    assert not [b for b in bays(d) if b.startswith("psu")]
    inlet = by_id(d, "rear")["ac-inlet"]
    assert inlet["ref"] == "std/c14-inlet@1"


def decor(d, view):
    return {x["id"]: x for x in d["views"][view]["panel"].get("decor") or [] if x.get("id")}


def gaps(d):
    return {g["what"]: g for g in d.get("gaps") or []}


def path_points(svg_text, node_id):
    """The vertices of an absolute `M x y L x y ... Z` path, in the order the path draws them."""
    import re
    m = re.search(r'<path id="%s" d="([^"]+)"' % node_id, svg_text)
    assert m, f"no path {node_id}"
    nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", m.group(1))]
    return list(zip(nums[0::2], nums[1::2]))


def test_48fpd_rps_connector_is_chassis_art_with_a_gap():
    d = device("ws-c2960s-48fpd")
    assert {"rps-plate", "rps-shroud", "rps-housing"} <= set(decor(d, "rear"))
    assert "rps-connector-part" in gaps(d)


# --- colour: the NetBox stencil's own sampled values, and a declared gap where no source has the face ---


def test_48fpd_chassis_colour_is_the_stencils_sampled_charcoal_panel():
    """Median of 3600 px of plain panel, box (435,30)-(480,110) of the 48FPD-L stencil: #404040."""
    assert device("ws-c2960s-48fpd")["chassis"]["color"] == "#404040"


def test_48fpd_front_paints_the_teal_bezel_and_surrounds_with_their_sampled_fills():
    dc = decor(device("ws-c2960s-48fpd"), "front")
    teal = "#255e6d"
    for i in ("bezel-top", "bezel-bottom", "bezel-left", "bezel-right", "legend-band", "usb-surround",
              "console-usb-surround", "mode-button"):
        assert dc[i]["fill"] == teal, i
    assert dc["console-surround"]["fill"] == "#bad4d7"
    assert dc["lamp-block"]["fill"] == "#404040"
    assert {dc[f"poe-strip-{n}"]["fill"] for n in range(1, 5)} == {"#ffff99"}


def test_48fpd_front_outlines_each_block_of_twelve_each_sfp_cage_and_the_management_jack_in_yellow():
    """Figure 1-1 (PDF p4, printed 1-2) frames the jack blocks in yellow; the stencil's 48FPD-L shows them white."""
    dc = decor(device("ws-c2960s-48fpd"), "front")
    blocks = [dc[f"jack-block-outline-{n}"] for n in range(1, 5)]
    assert [b["at"][0] for b in blocks] == [20.66, 110.06, 199.46, 288.86]
    assert {b["stroke"] for b in blocks + [dc["sfp-outline-1"], dc["sfp-outline-2"], dc["mgmt-outline"]]} == {"#ffff99"}


def test_48fpd_silkscreen_on_the_dark_face_is_inked_light_from_the_chassis_silk_colour():
    d = device("ws-c2960s-48fpd")
    assert d["chassis"]["silk"] == "#ffffff"
    silk = {s["id"]: s for s in d["views"]["front"]["silkscreen"] if s.get("id")}
    for i in ("silk-model", "silk-console", "silk-sfp", "silk-mode", "silk-syst", "silk-poe"):
        assert "fill" not in silk[i] or silk[i]["fill"] in ("#ffffff", "#f2f2f2", "#bbd5d8"), i
    # the port numerals above the jacks stand on yellow tags and stay dark; the SFP+ numbers stand on the panel
    assert silk["silk-49"]["fill"] == "#ffffff" and silk["silk-50"]["fill"] == "#ffffff"


def test_48fpd_colour_provenance_names_the_file_box_count_and_method():
    note = device("ws-c2960s-48fpd")["provenance"]["colour"]
    assert note["confidence"] == "estimated"
    text = note["note"]
    for needle in ("cisco-ws-c2960s-48fpd-l.front.png", "(435,30,480,110)", "3600", "#404040", "#255e6d",
                   "median", "community", "Figure 1-1"):
        assert needle in text, needle


def test_48fpd_rear_colour_is_a_declared_gap_because_the_photograph_is_another_models():
    d = device("ws-c2960s-48fpd")
    g = gaps(d)["faceplate-colour"]
    assert g["scope"] == ["rear"]
    assert "#3f4447" in g["wanted"] and "8-4A" in g["wanted"]
    assert d["chassis"]["color"] != "#d3d4d1", "that is the 4948E's colour"


# --- the RPS connector: two rows of eleven in a shroud, on a plate with two screws ---------------------


def test_48fpd_rps_connector_has_twenty_two_pins_in_two_rows_of_eleven_at_the_measured_pitch():
    dc = decor(device("ws-c2960s-48fpd"), "rear")
    pins = [v for k, v in dc.items() if k.startswith("rps-pin-")]
    assert len(pins) == 22
    xs = sorted({p["at"][0] for p in pins})
    ys = sorted({p["at"][1] for p in pins})
    assert len(xs) == 11 and len(ys) == 2
    assert abs((xs[-1] - xs[0]) / 10 - 4.17) < 0.01 and abs(ys[1] - ys[0] - 4.03) < 0.01
    assert dc["rps-plate"]["at"] == [285.0, 21.4] and dc["rps-plate"]["size"] == [72.8, 22.6]
    assert dc["rps-shroud"]["at"] == [298.4, 24.0] and dc["rps-shroud"]["size"] == [48.2, 11.3]
    assert {dc["rps-screw-l"]["at"][0], dc["rps-screw-r"]["at"][0]} == {293.3, 348.8}


def test_48fpd_rps_connector_is_drawn_open_with_its_two_label_plates():
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "rear")
    assert "rps-cover" not in dc
    assert dc["rps-rating-strip"]["at"] == [297.7, 17.9]
    assert dc["warning-label"]["at"] == [294.0, 5.9]
    assert "drawn open" in d["provenance"]["rear"]["note"]
    assert "7" in d["provenance"]["rear"]["note"] and "Figure 1-10" in d["provenance"]["rear"]["note"]


def test_48fpd_rear_carries_the_inlet_surround_the_fan_hexagons_and_the_pan_head_screws():
    dc = decor(device("ws-c2960s-48fpd"), "rear")
    assert dc["inlet-surround"]["at"] == [387.6, 8.3] and dc["inlet-surround"]["size"] == [29.3, 22.5]
    fan = dc["fan-exhaust"]
    assert fan["pattern"] == "vent" and fan["pattern-pitch"] == [17.72, 10.22]
    assert fan["at"] == [158.1, 13.2] and fan["size"] == [52.5, 27.3]
    # the fourth, at 7.3 mm, is on the module's flange and is drawn in the cover's skin
    assert [dc[f"rear-screw-{n}"]["at"][0] for n in range(1, 4)] == [108.0, 270.8, 433.0]
    assert dc["rating-label"]["at"] == [351.0, 6.1] and dc["rating-label"]["size"] == [32.7, 13.4]


# --- the FlexStack slot and its cover: the module's outline as photographed -------------------------


BLANK_OUTLINE = [(0.0, 0.0), (92.4, 0.0), (92.7, 21.1), (103.3, 31.7), (103.3, 39.0), (10.9, 39.0), (10.9, 19.3),
                 (0.0, 10.6)]


def test_flexstack_blank_outline_is_the_photographed_module_frame_with_its_two_slopes():
    skin = (COMPONENTS / "c2960s-flexstack-blank/v1/skins/default.svg").read_text()
    assert path_points(skin, "plate") == BLANK_OUTLINE
    c = component("c2960s-flexstack-blank")
    assert c["size"] == {"w": 103.3, "h": 39.0, "d": 3.0}
    assert c["relief"]["features"][0] == {**c["relief"]["features"][0], "node": "plate", "shape": True}


def test_flexstack_blank_standin_colour_is_declared_and_claims_no_source():
    c = component("c2960s-flexstack-blank")
    note = c["provenance"]["colour"]
    assert "stand-in" in note and "no source" in note.lower()
    assert c["body"]["color"] == "#393e41"


def test_48fpd_flexstack_bay_is_the_modules_bounding_box_in_the_photograph():
    bay = bays(device("ws-c2960s-48fpd"))["flexstack-slot"]
    assert bay["at"] == [2.6, 1.8] and bay["size"] == {"w": 103.3, "h": 39.0}


def test_48fpd_attrs_come_from_its_own_row_of_spec_table_1_2():
    a = device("ws-c2960s-48fpd")["attrs"]["power"]
    assert a["power-input-ac"].startswith("100 to 240 VAC") and "9 to 4 A" in a["power-input-ac"]
    assert "-52 V" in a["rps-input"].replace("–", "-") and "15 A" in a["rps-input"]
    assert a["power-consumption-w"] == 129
    assert a["heat-dissipation-btu-hr"] == 440
    assert a["poe-budget-w"] == 740


def test_48fpd_configurations_carry_the_one_sku_and_seat_the_blank():
    d = device("ws-c2960s-48fpd")
    cfg = d["configurations"]
    assert cfg["ac"]["kind"] == "base" and cfg["ac"]["default"] is True
    orderable = {k: v for k, v in cfg.items() if v["kind"] == "orderable"}
    assert {k: set(v["part-numbers"]) for k, v in orderable.items()} == {"ws-c2960s-48fpd-l": {"WS-C2960S-48FPD-L"}}
    assert orderable["ws-c2960s-48fpd-l"]["bays"] == {"flexstack-slot": BLANK}


def test_48fpd_ears_default_to_the_front_mounting_position():
    """Figures 1-12 and 1-13: front, mid and rear positions; none dimensioned."""
    ears = device("ws-c2960s-48fpd")["chassis"]["ears"]
    names = {p["name"]: p for p in ears["positions"]}
    assert set(names) == {"flush", "mid", "rear"}
    assert names["flush"]["default"] is True
    assert all("at" not in p for p in ears["positions"])


def test_48fpd_lists_no_kit_and_opens_an_etsi_bracket_gap():
    d = device("ws-c2960s-48fpd")
    assert "kits" not in d["chassis"]
    assert "etsi-bracket" in {g["what"] for g in d["gaps"]}


def test_48fpd_unmeasurable_faces_are_empty():
    d = device("ws-c2960s-48fpd")
    for face in ("top", "bottom", "left", "right"):
        assert d["views"][face].get("empty"), face


def test_48fpd_exports_one_device_type_per_orderable_part_number():
    for tool, sub in (("netbox", "device-types/Cisco"), ("nautobot", "device-types/Cisco")):
        path = EXPORTS / tool / sub / "WS-C2960S-48FPD-L.yaml"
        assert path.exists(), f"{path}: run dcim_export.py for ws-c2960s-48fpd"
        doc = yaml.safe_load(path.read_text())
        assert doc["u_height"] == 1
        assert doc["model"] == "WS-C2960S-48FPD-L"
