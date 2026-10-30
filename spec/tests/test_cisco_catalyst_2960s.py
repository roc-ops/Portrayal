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
    assert b["flexstack-slot"]["accepts"] == [BLANK, "cisco/c2960s-stack@1"]
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
    assert {dc[f"poe-tag-{n}"]["fill"] for n in range(1, 25)} == {"#ffff99"}


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
    # the port numerals above the jacks stand on yellow tags and stay dark; the SFP+ numbers stand on white tabs
    assert silk["silk-49"]["fill"] == "#595959" and silk["silk-50"]["fill"] == "#595959"


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


# --- the second look: plates, bar, silver, MODE button, marks, labels, fan, bay and the module -----------
#
# Every figure below is read from a held source at a stated scale: the NetBox 48FPD-L front stencil at
# 11.345 px per mm (5475 px over 482.6 mm, the chassis starting 216 px in) and the NetBox rear photograph
# of the WS-C2960S-48LPD-L at 3.41 px per mm. The three stencils agree on every value used here.

STENCIL_PLATE_X = [22.65, 112.03, 201.41, 290.79]
STENCIL_OUTLINE_X = [20.66, 110.06, 199.46, 288.86]


def order(d, view):
    return [x["id"] for x in d["views"][view]["panel"].get("decor") or [] if x.get("id")]


def silk_ids(d, view):
    return {s["id"]: s for s in d["views"][view].get("silkscreen") or [] if s.get("id")}


def test_48fpd_jack_plates_are_the_stencils_silver_inside_a_white_ring_and_a_dark_channel():
    """Plate #efefef (23316 px), bar #dcdcdc (31850 px), ring #ffffff (1800 px) on the 48FPD-L stencil."""
    dc = decor(device("ws-c2960s-48fpd"), "front")
    for n in range(1, 5):
        ring, chan, plate, bar = (dc[f"jack-{k}-{n}"] for k in ("ring", "channel", "plate", "bar"))
        assert ring["at"] == [STENCIL_OUTLINE_X[n - 1], 10.9] and ring["size"] == [89.2, 27.6]
        assert ring["fill"] == "#ffffff" and ring["kind"] == "jack-plate"
        assert chan["fill"] == "#404040"
        assert plate["kind"] == "jack-plate" and plate["fill"] == "#efefef"
        assert plate["at"] == [STENCIL_PLATE_X[n - 1], 12.87] and plate["size"] == [85.5, 23.89]
        assert bar["fill"] == "#dcdcdc" and bar["at"] == [STENCIL_PLATE_X[n - 1], 22.92] and bar["size"] == [85.5, 3.7]


def test_48fpd_plates_are_painted_above_the_charcoal_and_under_the_outlines_and_the_jacks():
    d = device("ws-c2960s-48fpd")
    o = order(d, "front")
    for n in range(1, 5):
        seq = [o.index(f"jack-{k}-{n}") for k in ("ring", "channel", "plate", "bar")]
        assert seq == sorted(seq) and seq[-1] < o.index(f"jack-block-outline-{n}")
    # the decor layer is painted before the cutouts and the placed jacks, which the renderer keeps in that order
    assert o.index("lamp-block") < o.index("jack-ring-1")


def test_48fpd_mode_button_is_the_stencils_teal_rounded_button_with_its_black_rim():
    """Interior #255e6d (1375 px, box 330,435,385,460), rim #020404 (90 px, box 315,430,318,460); 85 x 62 px."""
    dc = decor(device("ws-c2960s-48fpd"), "front")
    rim, b = dc["mode-button-rim"], dc["mode-button"]
    assert rim["at"] == [8.73, 36.32] and rim["size"] == [7.5, 5.46] and rim["rx"] == 1.8 and rim["fill"] == "#020404"
    assert b["at"] == [8.99, 36.58] and b["size"] == [6.88, 4.76] and b["fill"] == "#255e6d"
    assert list(dc).index("mode-button-rim") < list(dc).index("mode-button"), "the rim is under the teal"


def test_48fpd_usb_a_and_sfp_cages_are_drawn_silver_as_surrounds_the_parts_leave_visible():
    """USB-A shell #7b7b7b (7675 px), cage frames #cfcfcf (1423 px each); the parts' own skins are not edited."""
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "front")
    assert dc["usb-shell"]["fill"] == "#7b7b7b" and dc["usb-shell"]["at"] == [380.96, 6.52]
    assert dc["sfp-frame-1"]["fill"] == "#cfcfcf" and dc["sfp-frame-2"]["fill"] == "#cfcfcf"
    assert dc["sfp-frame-1"]["at"] == [379.9, 27.3] and dc["sfp-frame-2"]["at"] == [409.87, 27.3]
    o = order(d, "front")
    assert o.index("usb-shell") > o.index("usb-surround") and o.index("sfp-frame-1") < o.index("sfp-outline-1")
    p = by_id(d, "front")
    assert p["port-49"]["ref"] == "std/sfp@1" and p["usb-a"]["ref"] == "std/usb-a@1"
    assert "sfp-collar-silver" in gaps(d)


def test_48fpd_ticks_are_a_yellow_band_with_a_motif_of_gaps_at_the_stencils_pitch():
    """47 ticks a block, 5 px (0.44 mm) wide on a 20.41 px (1.799 mm) pitch, from 481 px, 444 to 471 px tall."""
    dc = decor(device("ws-c2960s-48fpd"), "front")
    for n in range(1, 5):
        band, gap = dc[f"tick-band-{n}"], dc[f"tick-gaps-{n}"]
        assert band["fill"] == "#ffff99" and band["size"] == [83.2, 2.37]
        assert gap["pattern"] == "motif" and gap["pattern-pitch"] == [1.8, 2.37] and gap["size"] == band["size"]
        assert gap["at"] == band["at"]
    assert dc["tick-band-1"]["at"] == [23.36, 39.13]


def test_48fpd_corner_marks_are_left_and_the_gap_says_why():
    """The jack part paints the corner shoulders the marks sit on, and silkscreen lies under the parts."""
    d = device("ws-c2960s-48fpd")
    assert not [k for k in silk_ids(d, "front") if k.startswith("mark-")]
    g = gaps(d)["front-text-and-corner-marks"]["wanted"]
    assert "corner marks 1X to 48X" in g and "under the parts" in g


def test_48fpd_poe_strip_text_is_drawn_and_740_w_is_left_because_it_is_unreadable_on_the_ticks():
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "front")
    assert dc["poe-label-box"]["fill"] == "#ffffff" and dc["poe-label-box"]["at"] == [26.97, 38.17]
    s = silk_ids(d, "front")
    assert [s[i]["text"] for i in ("silk-poe-power", "silk-poe-over", "silk-poe-ethernet")] == ["POWER", "OVER", "ETHERNET"]
    assert not any("740" in str(v.get("text", "")) for v in s.values())
    g = gaps(d)["front-text-and-corner-marks"]["wanted"]
    assert "740 W" in g and "USB symbol" in g


def test_48fpd_rear_warning_label_is_the_photographs_three_lines_and_triangle():
    d = device("ws-c2960s-48fpd")
    s = silk_ids(d, "rear")
    lines = [s[f"silk-warning-{i}"] for i in (1, 2, 3)]
    assert [x["text"] for x in lines] == ["DC INPUTS FOR REMOTE", "POWER SUPPLY", "SPECIFIED IN MANUAL"]
    assert [x["at"] for x in lines] == [[322.2, 8.42], [322.2, 11.76], [322.2, 14.93]]
    assert {x["fill"] for x in lines} == {"#cfd3d1"} and {x["anchor"] for x in lines} == {"middle"}
    tri = s["warning-triangle"]
    assert tri["at"] == [298.15, 7.6] and tri["fill"] == "#dce0e0" and tri["filled"] is False and tri["path"].startswith("M")


def test_48fpd_rear_ratings_strip_and_rating_plate_carry_the_photographs_text_as_stand_ins():
    d = device("ws-c2960s-48fpd")
    s = silk_ids(d, "rear")
    strip = [s[i]["text"] for i in ("silk-rps-12v", "silk-rps-48v", "silk-rps-78a")]
    assert strip == ["+12V", "@11.25A, -48V", "@7.8A"]
    assert "dc-symbol-1" in s and "dc-symbol-2" in s
    assert {s[i]["fill"] for i in ("silk-rps-12v", "silk-rps-48v", "silk-rps-78a")} == {"#626661"}
    plate = [s[i] for i in ("silk-rating-1", "silk-rating-2", "silk-rating-3")]
    assert [x["text"] for x in plate] == ["RATING", "100-240V~", "8-4A, 50-60Hz"]
    assert {x["fill"] for x in plate} == {"#414445"} and {x["at"][0] for x in plate} == {368.0}
    for x in list(s.values()):
        if x.get("text"):
            assert x["font-size"] >= 1.5


def test_48fpd_rear_label_gap_quotes_the_photograph_and_each_models_own_row():
    g = gaps(device("ws-c2960s-48fpd"))["rear-label-text"]["wanted"]
    for needle in ("NetBox photograph", "another model", "8-4A", "+12V", "11.25A", "7.8A", "9 to 4 A",
                   "5 to 2 A", "1 to 0.5 A", "+12 V @ 3 A", "15 A", "12-6A", "estimated", "Table 1-2", "Table 1-3"):
        assert needle in g, needle


def test_48fpd_rear_label_provenance_marks_every_figure_estimated_with_file_box_count_and_median():
    n = device("ws-c2960s-48fpd")["provenance"]["rear-labels"]
    assert n["confidence"] == "estimated"
    for needle in ("cisco-ws-c2960s-48lpd-l.rear.png", "(1043,20,1160,55)", "948", "#cfd3d1", "#626661", "#414445",
                   "median", "stand-in"):
        assert needle in n["note"], needle


def test_48fpd_fan_exhaust_is_a_web_plate_under_the_vent_field_with_the_photographs_light_edges():
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "rear")
    plate = dc["fan-exhaust-plate"]
    assert plate["kind"] == "fan-exhaust-plate" and plate["at"] == [158.1, 13.2] and plate["size"] == [52.5, 27.3]
    assert plate["fill"] == "#404345"
    assert order(d, "rear").index("fan-exhaust-plate") < order(d, "rear").index("fan-exhaust")
    fan = dc["fan-exhaust"]
    assert fan["pattern"] == "vent" and fan["pattern-pitch"] == [17.72, 10.22] and fan["size"] == [52.5, 27.3]
    assert dc["fan-edge-top"]["fill"] == "#b9bcba" and dc["fan-edge-top"]["at"] == [158.1, 12.0]
    assert dc["fan-edge-bottom"]["fill"] == "#b9bcba" and dc["fan-edge-bottom"]["at"][1] == 40.5
    note = d["provenance"]["rear"]["note"]
    assert "crisp" in note and "cairosvg" in note and "#404345" in note and "#040507" in note


def test_48fpd_flexstack_bay_corners_overpaint_the_seam_so_no_rectangle_shows():
    """The corner fills reach 0.4 mm past the box so the bay's dark opening cannot show as a hairline."""
    import re
    skin = (COMPONENTS / "c2960s-flexstack-blank/v1/skins/default.svg").read_text()
    fill = re.search(r'<g id="rear-plate-fill"[^>]*>(.*?)</g>', skin, re.S).group(1)
    corners = [[float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", d)] for d in re.findall(r' d="([^"]+)"', fill)]
    assert len(corners) == 2
    upper_right, lower_left = corners
    assert max(upper_right[0::2]) >= 103.7 and min(upper_right[1::2]) <= -0.4
    assert min(lower_left[0::2]) <= -0.4 and max(lower_left[1::2]) >= 39.4
    assert path_points(skin, "plate") == BLANK_OUTLINE, "the outline is the owner's answer A and does not change"
    bay = bays(device("ws-c2960s-48fpd"))["flexstack-slot"]
    assert bay["at"] == [2.6, 1.8] and bay["size"] == {"w": 103.3, "h": 39.0}


# --- the C2960S-STACK FlexStack module, its own part -----------------------------------------------------

STACK = "cisco/c2960s-stack@1"


def test_flexstack_module_is_one_new_component_with_the_printed_part_number():
    c = component("c2960s-stack")
    assert c["version"] == "1.0.0" and c["kind"] == "module"
    assert c["part-numbers"] == {"C2960S-STACK": {"part": "C2960S-STACK"}}
    assert "model" not in c["attrs"], "a part with part-numbers carries its name there (lint L1)"
    assert "PDF p29" in c["provenance"]["part-number"] and "1-5" in c["provenance"]["part-number"]


def test_flexstack_module_has_the_covers_outline_and_size_so_it_fits_the_bay():
    skin = (COMPONENTS / "c2960s-stack/v1/skins/default.svg").read_text()
    assert path_points(skin, "plate") == BLANK_OUTLINE
    c = component("c2960s-stack")
    assert c["size"] == {"w": 103.3, "h": 39.0, "d": 3.0}
    assert c["relief"]["features"][0]["node"] == "plate" and c["relief"]["features"][0]["shape"] is True
    b = bays(device("ws-c2960s-48fpd"))["flexstack-slot"]
    assert (c["size"]["w"], c["size"]["h"]) == (b["size"]["w"], b["size"]["h"])


def test_flexstack_module_has_two_stack_ports_declared_as_port_elements():
    c = component("c2960s-stack")
    ports_ = {k: v for k, v in c["elements"].items() if v["class"] == "port"}
    assert set(ports_) == {"stack-1", "stack-2"}
    skin = (COMPONENTS / "c2960s-stack/v1/skins/default.svg").read_text()
    assert ">STACK 1<" in skin and ">STACK 2<" in skin and ">C2960S-STACK<" in skin
    assert 'id="stack-1"' in skin and 'id="stack-2"' in skin


def test_flexstack_module_logo_is_a_reserved_region_and_not_drawn():
    c = component("c2960s-stack")
    assert "logo-zone" in c["provenance"]["logo"] and "not drawn" in c["provenance"]["logo"].lower()
    assert c["elements"]["logo-zone"]["class"] == "logo-zone"
    skin = (COMPONENTS / "c2960s-stack/v1/skins/default.svg").read_text()
    assert "cisco" not in skin.lower().replace("c2960s-stack", "")


def test_flexstack_module_colours_equal_their_photograph_samples():
    c = component("c2960s-stack")
    skin = (COMPONENTS / "c2960s-stack/v1/skins/default.svg").read_text()
    for colour in ("#393e41", "#3f565d", "#171615", "#aea699", "#2b3f45", "#b3b8bb", "#a1a5a8"):
        assert colour in skin, colour
    note = c["provenance"]["colour"]
    for needle in ("(80,60,140,120)", "3600", "#393e41", "2483", "#171615", "447", "#aea699", "606", "#2b3f45",
                   "(230,137,330,142)", "500 px", "#3f565d", "median", "estimated"):
        assert needle in note, needle


@pytest.mark.parametrize("name", ["ws-c2960s-48fpd"])
def test_every_stacking_models_bay_accepts_the_blank_and_the_module_and_defaults_to_the_blank(name):
    """Table 1-1 (PDF p3, printed 1-1) marks the model with footnote 1, 'Support Cisco FlexStack technology'."""
    b = bays(device(name))["flexstack-slot"]
    assert b["accepts"] == [BLANK, STACK] and b["default"] == BLANK


def test_48fpd_has_a_configuration_that_seats_the_module_and_the_default_still_seats_the_blank():
    cfg = device("ws-c2960s-48fpd")["configurations"]
    assert cfg["with-flexstack-module"]["kind"] == "example"
    assert cfg["with-flexstack-module"]["bays"] == {"flexstack-slot": STACK}
    assert cfg["ws-c2960s-48fpd-l"]["bays"] == {"flexstack-slot": BLANK}


def test_48fpd_exports_one_device_type_per_orderable_part_number():
    for tool, sub in (("netbox", "device-types/Cisco"), ("nautobot", "device-types/Cisco")):
        path = EXPORTS / tool / sub / "WS-C2960S-48FPD-L.yaml"
        assert path.exists(), f"{path}: run dcim_export.py for ws-c2960s-48fpd"
        doc = yaml.safe_load(path.read_text())
        assert doc["u_height"] == 1
        assert doc["model"] == "WS-C2960S-48FPD-L"


# --- the third look: the owner's fourteen notes on the preview ---------------------------------------------
#
# Front figures are read from the NetBox 48FPD-L stencil at 11.345 px per mm (the chassis 216 px in), rear
# figures from the NetBox 48LPD-L rear photograph at 3.41 px per mm. Each colour below is the median of the
# pixels of the box its provenance names.

LAMP = "common/led-arrow-sm@1"


def lamps(d):
    return [p for p in placements(d, "front") if p.get("ref") == LAMP]


def subpaths(path):
    return path.count("M ")


def centre(p):
    return (p["at"][0] + 1.125, p["at"][1] + 1.0)


def test_48fpd_port_arrows_are_up_for_odd_ports_and_down_for_even_with_no_dark_disc_left():
    """Stencil arrows: light grey #808080 (120 px, box 520,96,535,104), no circle, 2.38 x 2.12 mm."""
    d = device("ws-c2960s-48fpd")
    p = by_id(d, "front")
    for n in range(1, 49):
        assert p[f"led-port-{n}"]["ref"] == LAMP
        assert p[f"led-port-{n}"]["skin"] == ("up" if n % 2 else "down"), n
    assert p["led-port-49"]["skin"] == "down" and p["led-port-50"]["skin"] == "down"
    s = silk_ids(d, "front")
    ups = [x for x in lamps(d) if x["skin"] == "up" and not x.get("rotate")]
    downs = [x for x in lamps(d) if x["skin"] == "down"]
    assert (len(ups), len(downs)) == (25, 27)
    assert s["lamp-arrows-up"]["fill"] == s["lamp-arrows-down"]["fill"] == s["lamp-arrows-right"]["fill"] == "#808080"
    assert subpaths(s["lamp-arrows-up"]["path"]) == len(ups)
    assert subpaths(s["lamp-arrows-down"]["path"]) == len(downs)
    assert subpaths(s["lamp-arrows-right"]["path"]) == 1
    # the disc each punched lamp opening draws is covered in the panel colour, one cover for each opening
    cuts = [c for c in d["views"]["front"]["panel"]["cutouts"] if c["id"].startswith(("led-port-", "led-console-", "led-mgmt"))]
    assert len(cuts) == len(lamps(d)) == 53
    assert s["lamp-hole-cover"]["fill"] == d["chassis"]["color"] == "#404040"
    assert subpaths(s["lamp-hole-cover"]["path"]) == len(cuts)
    order = [x["id"] for x in d["views"]["front"]["silkscreen"] if x.get("id")]
    assert order.index("lamp-hole-cover") < order.index("lamp-arrows-up")


def test_48fpd_port_arrow_fill_gap_says_the_lamp_part_keeps_its_dark_fill():
    g = gaps(device("ws-c2960s-48fpd"))["port-arrow-fill"]["wanted"]
    for needle in ("#808080", "led-arrow-sm", "2.38 x 2.12", "not edited", "Figure 1-9", "PDF p18", "printed 1-16"):
        assert needle in g, needle


def test_48fpd_console_and_management_lamps_are_arrows_where_the_stencil_has_them():
    """Stencil arrow centres (392.38, 11.15), (397.09, 11.15) and (428.16, 24.11) mm; Figure 1-9 calls two of them LEDs."""
    d = device("ws-c2960s-48fpd")
    p = by_id(d, "front")
    want = {"led-console-usb": ((392.38, 11.15), "down", None), "led-console-rj45": ((397.09, 11.15), "up", 90),
            "led-mgmt": ((428.16, 24.11), "up", None)}
    for i, ((x, y), skin, rot) in want.items():
        assert p[i]["ref"] == LAMP and p[i]["skin"] == skin and p[i].get("rotate") == rot, i
        cx, cy = centre(p[i])
        assert abs(cx - x) < 0.05 and abs(cy - y) < 0.05, i
        assert p[i]["group"] == "leds"
    assert p["led-console-usb"]["for"] == "console-usb" and p["led-console-rj45"]["for"] == "console"
    assert "Figure 1-9" in d["provenance"]["controls-and-lamps"]["note"]


def test_48fpd_console_label_stands_inside_the_surround_and_clears_the_arrow_row():
    """Stencil label #bbd5d8 (578 px, box 4648,85,4746,101), cap height 1.23 mm, baseline 8.81 mm, centre 395.02 mm."""
    d = device("ws-c2960s-48fpd")
    lab = silk_ids(d, "front")["silk-console"]
    assert lab["text"] == "CONSOLE" and lab["fill"] == "#bbd5d8" and lab["at"] == [395.02, 8.81]
    assert lab["font-size"] >= 1.5
    panel = decor(d, "front")["console-panel"]
    top = lab["at"][1] - 0.716 * lab["font-size"]
    assert top >= panel["at"][1] and lab["at"][1] < p_arrow_top(d), "the label sits under the panel's top edge, above the arrows"
    half = 4.9 * lab["font-size"] / 2
    assert lab["at"][0] - half > panel["at"][0] and lab["at"][0] + half < panel["at"][0] + panel["size"][0]


def p_arrow_top(d):
    p = by_id(d, "front")
    return min(p[i]["at"][1] for i in ("led-console-usb", "led-console-rj45"))


def test_48fpd_console_and_management_jacks_stand_on_the_stencils_white_plates():
    """Plate #efefef (10086 px each, boxes 4782,86,4959,226 and 4998,86,5175,226), 15.6 x 12.34 mm."""
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "front")
    for i, x in (("console-jack-plate", 402.47), ("mgmt-jack-plate", 421.51)):
        assert dc[i]["at"] == [x, 7.58] and dc[i]["size"] == [15.6, 12.34] and dc[i]["fill"] == "#efefef"
    o = order(d, "front")
    assert o.index("console-panel") < o.index("console-jack-plate") < o.index("mgmt-outline")
    out = dc["mgmt-outline"]
    assert out["at"][0] + 0.5 < dc["mgmt-jack-plate"]["at"][0]
    assert dc["mgmt-jack-plate"]["at"][0] + 15.6 < out["at"][0] + out["size"][0] - 0.5
    p = by_id(d, "front")
    assert p["console"]["rotate"] == 180 and p["mgmt"]["rotate"] == 180 and p["console"]["ref"] == "std/rj45-ganged@2"
    g = gaps(d)["rj45-white-body-skin"]["wanted"]
    assert "std/rj45-ganged@2" in g and "left: the part's skin" in g and "latch stays up" in g


def test_48fpd_usb_a_keeps_its_part_its_skin_and_its_rotation_and_declares_the_interior():
    d = device("ws-c2960s-48fpd")
    u = by_id(d, "front")["usb-a"]
    assert u["ref"] == "std/usb-a@1" and u["skin"] == "usb2" and u["rotate"] == 90
    g = gaps(d)["usb-a-interior"]["wanted"]
    for needle in ("silver interior", "tongue at the left", "270 degree", "owner", "Figure 1-1", "#7b7b7b"):
        assert needle in g, needle


def test_48fpd_mini_b_connector_is_the_placed_part_unturned_and_the_contact_side_is_declared():
    d = device("ws-c2960s-48fpd")
    m = by_id(d, "front")["console-usb"]
    assert m["ref"] == "std/mini-usb@1" and "rotate" not in m and m["at"] == [390.65, 17.0]
    cut = [c for c in d["views"]["front"]["panel"]["cutouts"] if c["id"] == "console-usb"][0]
    assert cut["size"] == [7.7, 3.9]
    g = gaps(d)["mini-usb-contact-side"]["wanted"]
    for needle in ("lower half", "only source", "Figure 1-5", "PDF p9", "printed 1-7", "not turned"):
        assert needle in g, needle


def test_48fpd_sfp_cages_have_the_stencils_numeral_tabs_pull_tabs_and_dark_numerals_on_them():
    """Tab #f2f2f2 (2112 px), numeral #595959 (70 px), pull tab #c1c5cb (240 px), projection #000000 (861 px)."""
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "front")
    s = silk_ids(d, "front")
    for n, (tx, nx) in ((1, (383.61, 387.40)), (2, (413.75, 417.50))):
        tab = dc[f"sfp-number-tab-{n}"]
        assert tab["at"] == [tx, 39.49] and tab["size"] == [7.49, 2.73] and tab["fill"] == "#f2f2f2"
        num = s[f"silk-{48 + n}"]
        assert num["text"] == str(n) and num["fill"] == "#595959" and num["at"] == [nx, 41.52]
        assert tab["at"][0] < num["at"][0] < tab["at"][0] + tab["size"][0]
        assert tab["at"][1] < num["at"][1] - 0.716 * num["font-size"] and num["at"][1] < tab["at"][1] + tab["size"][1]
        assert dc[f"sfp-pull-tab-{n}"]["fill"] == "#c1c5cb" and dc[f"sfp-pull-tab-shadow-{n}"]["fill"] == "#000000"
    assert s["silk-sfp"]["text"] == "SFP+" and s["silk-sfp"]["at"] == [402.5, 41.1]
    o = order(d, "front")
    assert o.index("sfp-frame-1") < o.index("sfp-pull-tab-shadow-1") < o.index("sfp-pull-tab-1") < o.index("sfp-outline-1")
    g = gaps(d)["sfp-collar-silver"]["wanted"]
    for needle in ("clips", "gold contacts", "Not drawn", "std/sfp", "#c1c5cb", "#f2f2f2", "#595959"):
        assert needle in g, needle


def test_48fpd_mgmt_base_t_legend_is_declared_because_it_is_under_the_legend_size():
    d = device("ws-c2960s-48fpd")
    assert not [x for x in silk_ids(d, "front").values() if "MGMT" in str(x.get("text", ""))]
    g = gaps(d)["mgmt-base-t-legend"]["wanted"]
    for needle in ("BASET", "0.78 mm", "1.5 mm", "#ffff99", "not drawn"):
        assert needle in g, needle


def test_48fpd_poe_tags_are_one_yellow_tag_for_each_pair_under_the_numerals():
    """24 tags, #ffff99 (240 px, box 490,32,530,38), 13.18 x 3.44 mm at y 2.64, at the runs measured on the stencil."""
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "front")
    xs = [23.89, 37.81, 51.74, 65.76, 79.68, 93.61, 113.27, 127.19, 141.12, 155.13, 169.06, 182.99,
          202.64, 216.57, 230.5, 244.51, 258.44, 272.37, 292.02, 305.95, 319.88, 333.89, 347.82, 361.75]
    tags = [dc[f"poe-tag-{n}"] for n in range(1, 25)]
    assert [t["at"] for t in tags] == [[x, 2.64] for x in xs]
    assert {tuple(t["size"]) for t in tags} == {(13.18, 3.44)} and {t["fill"] for t in tags} == {"#ffff99"}
    assert not [k for k in dc if k.startswith("poe-strip")]
    for a, b in zip(tags, tags[1:]):  # the tags do not touch
        assert a["at"][0] + a["size"][0] < b["at"][0]
    o = order(d, "front")
    assert o.index("poe-tag-24") < o.index("jack-block-outline-1"), "the tags are decor, under the numerals' silkscreen"
    assert "wrong" in d["provenance"]["front-marks"]["note"] and "Figure 1-1" in d["provenance"]["front-marks"]["note"]


def test_48fpd_usb_symbol_is_drawn_white_and_the_logo_stays_a_region():
    d = device("ws-c2960s-48fpd")
    s = silk_ids(d, "front")
    assert s["usb-symbol-lines"]["fill"] == s["usb-symbol-heads"]["fill"] == "#ffffff"
    assert subpaths(s["usb-symbol-heads"]["path"]) == 4  # the arrowhead and the three discs
    assert s["usb-symbol-lines"]["at"][0] + 1.5 < decor(d, "front")["usb-surround"]["at"][0]
    assert [r["id"] for r in d["views"]["front"]["regions"] if r["id"] == "logo-zone"] == ["logo-zone"]
    assert not [x for x in s.values() if "cisco" in str(x.get("text", "")).lower()]
    g = gaps(d)["front-text-and-corner-marks"]["wanted"]
    assert "740 W" in g and "PDF p62" in g and "never drawn" in g and "16 of them" in g


def test_48fpd_rear_label_gap_opens_with_the_stand_in_line_and_asks_the_owner_to_choose():
    d = device("ws-c2960s-48fpd")
    g = gaps(d)["rear-label-text"]["wanted"]
    assert g.startswith("Label figures are another model's, kept as stand-ins.")
    for needle in ("9 to 4 A", "+12 V @ 4 A, -52 V @ 15 A", "5 to 2 A", "1 to 0.5 A", "PDF p62, printed 1-2",
                   "PDF p64, printed 1-4", "Figure 1-10", "12-6A", "owner's decision"):
        assert needle in g, needle
    assert d["provenance"]["rear-labels"]["confidence"] == "estimated"


def test_48fpd_rear_screws_have_the_cross_the_modules_screws_use_at_the_measured_places():
    """Heads #bdc8c5 (360 px, box 926,88,946,109; the median of three), slot ink #667572 (85 px, box 1478,88,1496,106)."""
    d = device("ws-c2960s-48fpd")
    dc, s = decor(d, "rear"), silk_ids(d, "rear")
    for n, x in ((1, 108.0), (2, 270.8), (3, 433.0)):
        scr = dc[f"rear-screw-{n}"]
        assert scr["at"] == [x, 25.3] and scr["size"] == [6.8, 6.8] and scr["fill"] == "#bdc8c5"
        cross = s[f"rear-screw-cross-{n}"]
        assert cross["fill"] == "#667572" and cross["filled"] is False
        assert cross["at"] == [round(x + 3.4, 2), 28.7]
        assert cross["path"] == "M -2.15 0 H 2.15 M 0 -2.15 V 2.15"
    module = (COMPONENTS / "c2960s-stack/v1/skins/default.svg").read_text()
    assert module.count('stroke-width="0.35" fill="none"/></g>') >= 3, "the module's own screws are crossed"


def test_48fpd_rear_undrawn_details_gap_lists_what_the_photograph_shows_and_the_render_does_not():
    d = device("ws-c2960s-48fpd")
    g = gaps(d)["rear-undrawn-details"]
    assert g["scope"] == ["rear"]
    for needle in ("diagonal edge", "two small oval tabs", "#323637", "#373b3e", "rectangular outline marks",
                   "round hole", "notch", "three pins", "dimensioned view"):
        assert needle in g["wanted"], needle
    assert not [k for k in decor(d, "rear") if "tab" in k], "the tabs are too faint to place and are not drawn"


def test_48fpd_rps_connector_fills_equal_their_photograph_samples_and_the_counts_are_unchanged():
    """Housing #f4f5ee (905 px), cells #7d7464 (594 px), contacts #887555 (198 px), top edge #0e1010 (420 px)."""
    d = device("ws-c2960s-48fpd")
    dc = decor(d, "rear")
    assert dc["rps-housing"]["fill"] == "#f4f5ee" and dc["rps-housing"]["at"] == [299.1, 25.1]
    cells = [v for k, v in dc.items() if k.startswith("rps-pin-")]
    contacts = [v for k, v in dc.items() if k.startswith("rps-contact-")]
    assert len(cells) == 22 and {c["fill"] for c in cells} == {"#7d7464"}
    assert len(contacts) == 22 and {c["fill"] for c in contacts} == {"#887555"}
    for c in cells:  # a contact sits in the middle of its cell
        mid = [v for v in contacts if abs(v["at"][0] - (c["at"][0] + 1.15)) < 0.01 and abs(v["at"][1] - (c["at"][1] + 1.25)) < 0.01]
        assert len(mid) == 1
    assert dc["rps-shroud"]["fill"] == "#656c66" and dc["rps-housing-top-edge"]["fill"] == "#0e1010"
    assert dc["rps-housing-top-edge"]["at"][1] == dc["rps-shroud"]["at"][1]
    o = order(d, "rear")
    assert o.index("rps-shroud") < o.index("rps-housing") < o.index("rps-pin-1-1") < o.index("rps-contact-1-1")
    assert o.index("rps-shroud") < o.index("rps-housing-top-edge")
    top = dc["rps-housing-top-edge"]
    assert top["at"][1] + top["size"][1] <= dc["rps-housing"]["at"][1] + 0.001, "the edge lies above the housing"
    assert "rps-connector-part" in gaps(d)


def test_48fpd_rear_colour_gap_adds_the_second_photograph_and_the_guides_three_faces():
    g = gaps(device("ws-c2960s-48fpd"))["faceplate-colour"]["wanted"]
    for needle in ("#3f4447", "2000 px", "#404145", "1120 px", "#44464a", "1800 px", "#d4d6d8", "3500 px", "#bebdbb",
                   "15000 px", "#8f908f", "1250 px", "Figure 1-10", "PDF p19", "printed 1-17", "#404040"):
        assert needle in g, needle
    assert device("ws-c2960s-48fpd")["chassis"]["color"] == "#404040"


# --- the FlexStack module's frame band and its two silver cages -------------------------------------------


def inset(points, t):
    n = len(points)
    lines = []
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = (dx * dx + dy * dy) ** 0.5
        lines.append(((a[0] - dy / ln * t, a[1] + dx / ln * t), (dx, dy)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        k = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * k, p1[1] + d1[1] * k))
    return out


def test_flexstack_module_frame_is_a_band_of_the_measured_thickness_inside_the_unchanged_outline():
    """Band 9 px (8 top, 10 bottom) at 3.41 px per mm = 2.64 mm; frame #3f565d (500 px, box 230,137,330,142)."""
    skin = (COMPONENTS / "c2960s-stack/v1/skins/default.svg").read_text()
    assert path_points(skin, "plate") == BLANK_OUTLINE
    face = path_points(skin, "face")
    want = inset(BLANK_OUTLINE, 2.64)
    assert len(face) == 8
    assert all(abs(a[0] - b[0]) < 0.02 and abs(a[1] - b[1]) < 0.02 for a, b in zip(face, want))
    import re
    assert re.search(r'<path id="plate"[^>]*fill="#3f565d"', skin) and re.search(r'<path id="face"[^>]*fill="#393e41"', skin)
    assert skin.index('id="plate"') < skin.index('id="face"') < skin.index('id="pocket"')
    c = component("c2960s-stack")
    assert c["size"] == {"w": 103.3, "h": 39.0, "d": 3.0} and c["relief"]["wall"] == "#3f565d"
    assert "2.64 mm" in c["provenance"]["colour"] and "gaps" not in c
    rel = c["provenance"]["relief"]
    assert "one slab" in rel and "not stepped in 3D" in rel and "Wanted:" in rel and c["relief"]["features"][0]["color"] == "#393e41"
    blank = (COMPONENTS / "c2960s-flexstack-blank/v1/skins/default.svg").read_text()
    assert path_points(blank, "plate") == path_points(skin, "plate"), "the cover's outline is the owner's answer A"


def test_flexstack_module_ports_are_two_silver_cages_with_dark_openings_in_a_blue_recess_and_no_olive_outline():
    """Cage #aea699 (447 px, box 152,58,208,124), opening #171615 (2483 px), recess border #2b3f45 (606 px)."""
    import re
    skin = (COMPONENTS / "c2960s-stack/v1/skins/default.svg").read_text()
    assert "#a29886" not in skin
    c = component("c2960s-stack")
    for i, y in (("stack-1", 15.2), ("stack-2", 25.0)):
        g = re.search(r'<g id="%s">(.*?)</g>' % i, skin, re.S).group(1)
        rects = re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"[^>]*fill="(#[0-9a-f]+)"', g)
        (sx, sy, sw, sh, sf), (ox, oy, ow, oh, of) = rects
        assert (float(sx), float(sy), float(sw), float(sh), sf) == (41.9, y, 16.5, 9.0, "#aea699")
        assert of == "#171615" and float(ox) > float(sx) and float(oy) > float(sy)
        assert float(ox) + float(ow) < float(sx) + float(sw) and float(oy) + float(oh) < float(sy) + float(sh)
        assert c["elements"][i]["at"] == [41.9, y] and c["elements"][i]["size"] == [16.5, 9.0]
    assert re.search(r'<rect id="pocket"[^>]*fill="#2b3f45"', skin)
    assert set(k for k, v in c["elements"].items() if v["class"] == "port") == {"stack-1", "stack-2"}
    assert ">STACK 1<" in skin and ">STACK 2<" in skin and ">C2960S-STACK<" in skin
    assert "rotate" not in skin and c["elements"]["logo-zone"]["class"] == "logo-zone"
