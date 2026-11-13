"""The CyberPower PDU31116 monitored PDU.

The PDU31116 is a 0U strip, 1349 mm long. It has twenty NEMA 5-15R outlets in two groups of ten with a display module between them.
Its fixed cord ends in a NEMA 5-15P plug. What is true of the library once it is in:

  - It is a device of the maker, the size its data sheet gives, mounted beside a rack's upright, with six views.
  - The twenty outlets are the library's 5-15R face, numbered 1 to 20 from the cord end.
  - Inside each group the outlets keep the pitch the photograph gives.
  - The display module carries the display, the Select and Enter buttons, four lamps, the Ethernet jack, three RJ45 jacks and a USB jack.
  - Every lamp is drawn off and declares the colour it shows lit.
  - A position read off an angled photograph is declared an estimate, and a wall no document shows says so.
  - The input cord states its plug, and the DCIM file the exporter wrote carries the plug and the twenty outlets.

These read the device source and the DCIM file the exporter wrote. They render nothing.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SHA = "e8cacac23a793820280dae2b8baeae870670bf94432a9b15236059a32d438d4d"
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]


def device():
    return yaml.safe_load((LIB / "devices" / "cyberpower" / "pdu31116" / "device.yaml").read_text())


def placements(view):
    comps = (device()["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


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


def test_the_display_module_carries_the_parts_the_photograph_shows():
    refs = {i: p["ref"] for i, p in placements("front").items() if not i.startswith("outlet-")}
    assert refs["display"] == "cyberpower/pdu-lcd@1"
    assert {refs[i] for i in ("select", "enter")} == {"cyberpower/pdu-joystick@1"}
    assert refs["eth"] == "common/rj45-eth@1"
    assert {refs[i] for i in ("in-env", "out", "serial")} == {"std/rj45@2"}
    assert refs["usb"] == "common/usb-a-bezel@1"


def test_every_lamp_is_drawn_off_and_declares_the_colour_it_shows_lit():
    d = device()
    front = placements("front")
    lamps = [p for p in front.values() if p["ref"] == "common/led-dot@1"]
    assert sorted(p["id"] for p in lamps) == ["lamp-critical", "lamp-normal", "lamp-warning", "status-lamp"]
    for p in lamps:
        states = d["groups"][p["group"]]["states"]
        assert states[0] == "off"
        assert states[1]["name"] == "on" and states[1]["color"].startswith("#")
    assert not any(x.get("kind") == "lamp" for x in d["views"]["front"]["panel"]["decor"])


def test_a_position_read_off_an_angled_photograph_is_declared_an_estimate():
    d = device()
    assert d["provenance"]["method"]["confidence"] == "estimated"
    assert "NOT orthographic" in d["provenance"]["method"]["note"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert "front-angled-photograph" in gaps
    assert gaps["other-side"]["note"].startswith("built as the documented side, as no document shows this one")
    assert gaps["rear"]["scope"] == ["rear"]


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
