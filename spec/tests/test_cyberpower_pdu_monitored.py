"""The CyberPower PDU31116 monitored PDU.

The PDU31116 is a 0U strip, 1349 mm long. It has twenty NEMA 5-15R outlets in two groups of ten with a display module between them.
Its fixed cord ends in a NEMA 5-15P plug. What is true of the library once it is in:

  - It is a device of the maker, the size its data sheet gives, mounted beside a rack's upright, with six views.
  - The twenty outlets are the library's 5-15R face, numbered 1 to 20 from the cord end.
  - Inside each group the outlets keep the pitch the photograph gives.
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


def test_it_is_a_zero_u_strip_of_the_maker_the_size_its_data_sheet_gives():
    d = device()
    assert (d["manufacturer"], d["model"]) == ("CyberPower", "PDU31116")
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == (48, 1349, 56)
    assert c["mount"] == "rack-side"
    assert d["datasheet"]["sha256"] == SHA


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
    assert module["at"] == [2.4, 364.0]
    assert module["size"] == [43.2, 131.0]
    assert 3.0 < module["size"][1] / module["size"][0] < 3.1, "page 2 reads 988 by 326.5 px: 3.03 to 1"
    top, bottom = module["at"][1], module["at"][1] + module["size"][1]
    ys = [placements("front")[i]["at"][1] for i in ("select", "enter", "display", "eth", "in-env", "out", "serial", "usb")]
    assert all(top < y < bottom for y in ys), "every part of the module sits inside it"
    assert decor("front")["module-slot"]["size"] == [25.4, 1.7]


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
        "rear", "mounting-brackets", "ends", "other-side", "vent-slits", "front-width", "outlet-size", "port-labels",
        "display-and-marks", "lamp-meanings", "numbering-direction", "manual",
    ])
    assert gaps["other-side"]["note"].startswith("built as the documented side, as no document shows this one")
    assert gaps["rear"]["scope"] == ["rear"]
    assert "56.6" in gaps["front-width"]["note"], "the gap states the width page 2 reads against the sheet's 48"


def test_the_cord_leaves_the_cord_end_at_the_measured_offset():
    cord = placements("bottom")["input"]
    assert cord["ref"] == "cyberpower/pdu-cord-5-15p@1"
    assert cord["at"] == [15.1, 20.0], "centre 23.1 across: 0.9 mm above the middle of the 48 mm end, read on page 1"


def test_the_vents_are_slits_three_millimetres_apart_and_the_far_end_carries_its_dot():
    for view, dot_x in (("left", 36.5), ("right", 17.9)):
        fields = decor(view)
        for n in (1, 2):
            vent = fields[f"vent-{n}"]
            assert vent["pattern"] == "motif"
            assert vent["pattern-pitch"] == [14.0, 3.0]
            assert vent["pattern-cells"] == [[[3.5, 0.8], [10.5, 0.8], [10.5, 2.2], [3.5, 2.2]]]
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
