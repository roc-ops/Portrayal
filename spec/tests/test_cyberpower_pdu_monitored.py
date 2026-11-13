"""The CyberPower PDU31116 monitored PDU.

The PDU31116 is a 0U strip, 1349 mm long. It has twenty NEMA 5-15R outlets in two groups of ten with a display module between them.
Its fixed cord ends in a NEMA 5-15P plug. What is true of the library once it is in:

  - It is a device of the maker, the sizes its data sheet gives, mounted beside a rack's upright, with six views.
  - The pictures decide which sheet figure is the front: it is 56 mm wide and 48 mm deep.
  - The twenty outlets are the library's 5-15R face, numbered 1 to 20 from the cord end.
  - Inside each group the outlets keep the pitch the photograph gives.
  - What the second picture shows across the face is placed from it: the holes, outlet 11, the numerals, the screws and the tab.
  - The display module is refitted from the data sheet's second picture, an orthographic view: about 3.03 long to 1 across.
  - It carries the display, two ring buttons, four lamps, the Ethernet jack, three RJ45 jacks and a USB jack.
  - Every lamp is drawn off and declares the colour the second picture shows it lit, the two Ethernet lamps included.
  - The three RJ45 jacks are drawn black and the Ethernet jack sits on a grey plate, as the picture shows them.
  - The vents are slits, and the far end carries the small dot the photograph shows.
  - A position read off an angled photograph is declared an estimate, and a wall no document shows says so.
  - The input cord states its plug, and the DCIM file the exporter wrote carries the plug and the twenty outlets.

These read the device source, the new button part and the DCIM file the exporter wrote. They render nothing.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SHA = "e8cacac23a793820280dae2b8baeae870670bf94432a9b15236059a32d438d4d"
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
DEVICE = LIB / "devices" / "cyberpower" / "pdu31116" / "device.yaml"
RING = LIB / "components" / "cyberpower" / "pdu-ring-button" / "v1"


def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(view):
    comps = (device()["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


def decor(view):
    return {d["id"]: d for d in device()["views"][view]["panel"]["decor"] if "id" in d}


def test_it_is_a_zero_u_strip_of_the_maker_the_sizes_its_data_sheet_gives():
    d = device()
    assert (d["manufacturer"], d["model"]) == ("CyberPower", "PDU31116")
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == (56, 1349, 48)
    assert c["mount"] == "rack-side"
    assert d["datasheet"]["sha256"] == SHA


def test_the_front_is_56_wide_and_48_deep_because_both_pictures_read_the_front_as_56():
    views = device()["views"]
    assert views["front"]["size"] == {"w": 56.0, "h": 1349.0}
    assert views["rear"]["size"] == {"w": 56.0, "h": 1349.0}
    assert views["top"]["size"] == {"w": 56.0, "h": 48.0}
    assert views["bottom"]["size"] == {"w": 56.0, "h": 48.0}
    assert views["left"]["size"] == {"w": 48.0, "h": 1349.0}
    assert views["right"]["size"] == {"w": 48.0, "h": 1349.0}
    gaps = {g["what"]: g for g in device()["gaps"]}
    gap = gaps["dimension-labels"]
    assert gap["reason"] == "sources-disagree"
    for reading in ("48 x 1349 x 56 mm", "56.6", "56.0", "56.7", "55.0"):
        assert reading in gap["note"], reading
    assert "front-width" not in gaps


def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched():
    views = device()["views"]
    assert sorted(views) == sorted(VIEWS)
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name}: neither drawn nor an `empty:` sentence"
        if not drawn:
            assert "Searched" in v["empty"], f"{name}: an empty face names what was searched"
            assert "two pictures" in v["empty"], f"{name}: the bare rear names both held pictures"


def test_the_twenty_outlets_are_the_library_5_15r_numbered_from_the_cord_end_at_the_photographed_pitch():
    front = placements("front")
    outlets = {i: p for i, p in front.items() if i.startswith("outlet-")}
    assert sorted(outlets, key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(1, 21)]
    assert {p["ref"] for p in outlets.values()} == {"std/nema-5-15r@1"}
    ys = [outlets[f"outlet-{n}"]["at"][1] for n in range(1, 21)]
    assert ys == sorted(ys, reverse=True), "outlet 1 is at the cord end, which is the bottom of the standing strip"
    for lo, hi in ((1, 10), (11, 20)):
        steps = [ys[n - 1] - ys[n] for n in range(lo, hi)]
        assert all(30.0 < s < 36.5 for s in steps), steps
        assert max(steps) - min(steps) < 1.0, "the pitch is one number inside a group"
    assert ys[9] - ys[10] > 300, "the display module sits between the two groups"


def test_the_display_module_is_refitted_from_the_orthographic_picture_at_about_3_to_1():
    module = decor("front")["display-module"]
    assert module["at"] == [6.4, 364.0]
    assert module["size"] == [43.2, 131.0]
    assert 3.0 < module["size"][1] / module["size"][0] < 3.1, "page 2 reads 988 by 326.5 px: 3.03 to 1"
    margin_far = 56.0 - (module["at"][0] + module["size"][0])
    assert abs(module["at"][0] - margin_far) < 0.01, "the module is centred across the 56 mm front"
    top, bottom = module["at"][1], module["at"][1] + module["size"][1]
    ys = [placements("front")[i]["at"][1] for i in ("select", "enter", "display", "eth", "in-env", "out", "serial", "usb")]
    assert all(top < y < bottom for y in ys), "every part of the module sits inside it"
    assert decor("front")["module-slot"]["size"] == [25.4, 1.7]


def test_what_the_second_picture_shows_across_the_face_is_placed_from_it():
    """Page 2 is orthographic: 7.55 px per mm, the band's centre at 28 mm across."""
    front = placements("front")
    for n in range(1, 21):
        assert front[f"outlet-{n}"]["at"][0] == 5.3, "outlet 11's block reads 5.1 to 32.5 across: centred on 18.8"
    holes = [d for i, d in decor("front").items() if i.startswith("hole-")]
    assert len(holes) == 8
    for hole in holes:
        assert hole["size"] == [2.6, 2.6], "page 2 reads each hole 20 px across"
        assert hole["at"][0] in (18.9, 34.1), "the two holes are 115 px, 15.2 mm, apart and centred on the band"
    assert sorted({h["at"][0] for h in holes}) == [18.9, 34.1]
    numerals = [s for s in device()["views"]["front"]["silkscreen"] if s.get("for", "").startswith("outlet-")]
    assert len(numerals) == 20
    for numeral in numerals:
        assert numeral["at"][0] == 41.8, "the numeral's baseline is 913.5 px on page 2"
        assert numeral["font-size"] == 5.6, "its figures stand 31 px, 4.1 mm"


def test_the_module_screws_are_dark_discs_with_a_cross_slot_the_library_part_cannot_draw():
    """common/screw-head@1 is 3.6 mm and silver and takes no size; page 2 shows 5.6 mm dark heads."""
    screw_part = yaml.safe_load((LIB / "components" / "common" / "screw-head" / "v1" / "contract.yaml").read_text())
    assert screw_part["size"]["w"] == 3.6
    assert "common/screw-head@1" not in {p["ref"] for p in placements("front").values()}
    fields = decor("front")
    for n, across in ((1, 11.85), (2, 38.5)):
        disc = fields[f"module-screw-{n}"]
        assert disc["size"] == [5.6, 5.6] and disc["rx"] == 2.8
        assert disc["at"] == [across, 366.7]
        horizontal, vertical = fields[f"module-screw-{n}-slot-h"], fields[f"module-screw-{n}-slot-v"]
        assert horizontal["size"] == [3.4, 0.7] and vertical["size"] == [0.7, 3.4]
        centre = (across + 2.8, 366.7 + 2.8)
        assert horizontal["at"] == [round(centre[0] - 1.7, 2), round(centre[1] - 0.35, 2)]
        assert vertical["at"] == [round(centre[0] - 0.35, 2), round(centre[1] - 1.7, 2)]


def test_the_small_tab_on_the_far_end_edge_of_the_module_is_drawn():
    tab = decor("front")["module-tab"]
    assert tab["size"] == [5.8, 1.8], "page 2 reads it 44 px across the face and 13.5 px along, 5.8 by 1.8 mm"
    assert tab["at"] == [25.0, 364.7]
    module = decor("front")["display-module"]
    assert module["at"][1] < tab["at"][1] < module["at"][1] + 2.0, "it sits on the far-end edge of the module"


def test_the_module_carries_the_parts_the_pictures_show_and_the_two_buttons_are_the_new_ring():
    refs = {i: p["ref"] for i, p in placements("front").items() if not i.startswith("outlet-")}
    assert refs["display"] == "cyberpower/pdu-lcd@1"
    assert {refs[i] for i in ("select", "enter")} == {"cyberpower/pdu-ring-button@1"}
    assert refs["eth"] == "common/rj45-eth@1"
    assert {refs[i] for i in ("in-env", "out", "serial")} == {"std/rj45@2"}
    assert refs["usb"] == "common/usb-a-bezel@1"
    contract = yaml.safe_load((RING / "contract.yaml").read_text())
    assert (contract["name"], contract["version"], contract["class"]) == ("pdu-ring-button", "1.0.0", "button")
    assert contract["size"] == {"w": 11.0, "h": 11.0}
    assert (RING / "skins" / "default.svg").is_file()


def test_every_lamp_is_drawn_off_and_declares_the_colour_the_second_picture_shows_it_lit():
    d = device()
    front = placements("front")
    lamps = [p for p in front.values() if p["ref"] == "common/led-dot@1"]
    assert sorted(p["id"] for p in lamps) == ["lamp-critical", "lamp-normal", "lamp-warning", "status-lamp"]
    lit = {"status": "#9de916", "lamp-normal": "#fbfb04", "lamp-warning": "#faba04", "lamp-critical": "#f90304"}
    for p in lamps:
        states = d["groups"][p["group"]]["states"]
        assert states[0] == "off"
        assert states[1]["name"] == "on" and states[1]["color"] == lit[p["group"]]
    assert not any(x.get("kind") == "lamp" for x in d["views"]["front"]["panel"]["decor"])


def test_the_two_ethernet_jack_lamps_declare_the_colours_the_picture_shows():
    eth = placements("front")["eth"]
    link, tx_rx = eth["states"]["led-a"], eth["states"]["led-b"]
    assert link == ["off", {"name": "link", "color": "#e7e31c"}]
    assert tx_rx == ["off", {"name": "tx-rx", "color": "#bfe387"}]


def test_the_lamp_legends_are_written_as_printed_with_their_dash():
    texts = {s["text"] for s in device()["views"]["front"]["silkscreen"]}
    assert {"- Normal", "- Warning", "- Critical", "Tx/Rx", "Link", "In / ENV", "Out", "Serial", "USB"} <= texts
    assert not {"Select", "Enter"} & texts, "the two button names are printed marks and are not drawn"


def test_the_three_rj45_jacks_are_black_and_the_ethernet_jack_sits_on_a_grey_plate():
    front = placements("front")
    for jack in ("in-env", "out", "serial"):
        assert front[jack]["attrs"]["finish"] == "#2b2f33", jack
    assert "finish" not in front["eth"].get("attrs", {})
    plate = decor("front")["eth-plate"]
    assert plate["fill"] == "#b6b5bb"
    assert plate["size"] == [16.5, 17.0]


def test_a_position_read_off_an_angled_photograph_is_declared_an_estimate():
    d = device()
    note = d["provenance"]["method"]["note"]
    assert d["provenance"]["method"]["confidence"] == "estimated"
    assert "NOT orthographic" in note
    assert "two pictures" in note
    gaps = {g["what"]: g for g in d["gaps"]}
    assert sorted(gaps) == sorted([
        "rear", "mounting-brackets", "ends", "other-side", "vent-slits", "dimension-labels", "outlet-size", "port-labels",
        "display-and-marks", "lamp-meanings", "numbering-direction", "manual",
    ])
    assert gaps["other-side"]["note"].startswith("built as the documented side, as no document shows this one")
    assert gaps["rear"]["scope"] == ["rear"]
    assert "56.6" in gaps["dimension-labels"]["note"], "the gap states the width page 2 reads against the sheet's order"


def test_the_cord_leaves_the_cord_end_at_the_measured_offset():
    cord = placements("bottom")["input"]
    assert cord["ref"] == "cyberpower/pdu-cord-5-15p@1"
    assert cord["at"] == [19.1, 16.0], "centre 27.1 across: 0.9 mm above the middle of the 56 mm end, mid-depth of 48 mm"


def test_the_vents_are_slits_three_millimetres_apart_and_the_far_end_carries_its_dot():
    for view, field_x, dot_x in (("left", 32.6, 31.2), ("right", 3.4, 15.2)):
        fields = decor(view)
        for n in (1, 2):
            vent = fields[f"vent-{n}"]
            assert vent["pattern"] == "motif"
            assert vent["pattern-pitch"] == [12.0, 3.0]
            assert vent["pattern-cells"] == [[[3.0, 0.8], [9.0, 0.8], [9.0, 2.2], [3.0, 2.2]]]
            assert vent["at"][0] == field_x and vent["size"][0] == 12.0
        assert fields["end-dot"]["at"] == [dot_x, 1.2]
        assert fields["end-dot"]["size"] == [1.6, 1.6]


def test_the_device_says_the_data_sheet_holds_two_pictures_and_where_each_is():
    text = DEVICE.read_text()
    assert "two pictures" in text
    assert "page 1" in text and "page 2" in text
    assert "no document states a colour" not in text.lower()


def test_the_input_cord_states_its_plug_and_the_strip_is_monitored_and_not_switched():
    d = device()
    assert placements("bottom")["input"]["ref"] == "cyberpower/pdu-cord-5-15p@1"
    assert d["attrs"]["power"]["input-plug"] == "nema-5-15p"
    m = d["attrs"]["management"]
    assert (m["metering-scope"], m["outlet-switching"]) == ("input", False)
    rules = {r["physical"]: r for r in d["interfaces"]}
    assert rules["outlet-{n}"]["range"] == "1-20"


def test_the_exporter_writes_the_input_plug_and_every_outlet_the_drawing_places():
    """The DCIM file the exporter wrote from the built library, not the source, carries the cord's plug and the outlets."""
    exported = yaml.safe_load((LIB / "exports" / "netbox" / "device-types" / "CyberPower" / "PDU31116.yaml").read_text())
    assert [p["type"] for p in exported["power-ports"]] == ["nema-5-15p"]
    assert len(exported["power-outlets"]) == 20
    assert {o["power_port"] for o in exported["power-outlets"]} == {"input"}
