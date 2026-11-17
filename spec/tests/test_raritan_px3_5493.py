"""The Raritan PX3-5493, a 0U rack PDU with 20 IEC C13 and 4 IEC C19 outlets in two circuits of 12.

What is true of the library once the device is in it.
The device exists under its maker and its outline is the printed unit size.
Its 24 outlets stand in four groups of six with a C19 first in each.
Each circuit's 12 outlets run through one of the two breakers.
The controller carries the jacks and buttons the specification's panel drawing shows.
The rear carries two mounting buttons 1244.0 apart, and every side is drawn or says why not.
Every estimate or borrowed shape is declared in the device's provenance or its gaps.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "raritan" / "px3-5493" / "device.yaml"
LENGTH = 1539.0
C13_H = 22.0
C19_H = 27.7
PITCH = 33.4
# First outlet of each group of six, measured from the cord end of the strip (mm), per the mechanical drawing.
GROUP_STARTS = {"A": 306.2, "B": 515.1, "C": 1096.8, "D": 1305.1}
GROUP_OUTLETS = {"A": range(24, 18, -1), "B": range(18, 12, -1), "C": range(12, 6, -1), "D": range(6, 0, -1)}
REUSED = {
    "std/c13-outlet@1", "std/c19-outlet@1", "raritan/px3-breaker@1", "raritan/px3-cord-60309@1",
    "raritan/px3-mounting-button@1", "raritan/pxo-lcd@1", "raritan/pxo-button@1", "raritan/pxo-usb-b@1",
    "std/rj45@2", "common/rj45-eth@1", "std/usb-a@1", "common/led-dot@1", "common/reset-button@1",
}


def _device():
    return yaml.safe_load(DEVICE.read_text(encoding="utf-8"))


def _placements(dev, view=None):
    out = []
    for name, v in dev.get("views", {}).items():
        if view and name != view:
            continue
        out.extend((v.get("components") or {}).get("placements") or [])
    return out


def _by_id(dev, view):
    return {p["id"]: p for p in _placements(dev, view)}


def _outlet_centre(p):
    height = C13_H if p["ref"].startswith("std/c13") else C19_H
    return p["at"][1] + height / 2


def _outlets(dev):
    return {int(p["id"].rsplit("-", 1)[1]): p for p in _placements(dev, "front") if p["id"].startswith("outlet-")}


def test_the_device_exists_under_its_maker_and_is_modelled():
    dev = _device()
    assert dev["manufacturer"] == "Raritan"
    assert dev["model"] == "PX3-5493"
    assert dev["maturity"] == "modelled"
    assert dev["version"] == "0.1.0"


def test_the_outline_is_the_printed_unit_size():
    chassis = _device()["chassis"]
    assert (chassis["width"], chassis["depth"], chassis["height"]) == (52, 65, 1539)
    assert chassis["mount"] == "rack-side"


def test_every_side_is_drawn_or_says_why_it_is_not():
    views = _device()["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    assert views["left"]["size"] == {"w": 65, "h": 1539}
    assert views["top"]["size"] == {"w": 52, "h": 65}
    for name in ("top", "bottom", "left", "right"):
        view = views[name]
        assert view.get("panel") or view.get("components") or view.get("empty"), name


def test_twenty_c13_and_four_c19_outlets_numbered_one_to_twenty_four():
    outlets = _outlets(_device())
    assert sorted(outlets) == list(range(1, 25))
    c19 = sorted(n for n, p in outlets.items() if p["ref"] == "std/c19-outlet@1")
    assert c19 == [6, 12, 18, 24]
    assert sum(1 for p in outlets.values() if p["ref"] == "std/c13-outlet@1") == 20


def test_the_outlets_stand_in_four_groups_of_six_at_the_drawings_pitch():
    outlets = _outlets(_device())
    for key, numbers in GROUP_OUTLETS.items():
        centres = [LENGTH - _outlet_centre(outlets[n]) for n in numbers]
        for k, c in enumerate(centres):
            assert abs(c - (GROUP_STARTS[key] + PITCH * k)) < 0.06, (key, k, c)
        first = outlets[list(numbers)[0]]
        assert first["ref"] == "std/c19-outlet@1", key


def test_the_gap_between_groups_is_eight_mm_wider_than_the_pitch():
    outlets = _outlets(_device())
    ordered = [LENGTH - _outlet_centre(outlets[n]) for n in range(24, 0, -1)]
    steps = [round(b - a, 1) for a, b in zip(ordered, ordered[1:])]
    assert steps.count(PITCH) == 20, steps
    wide = [s for s in steps if s != PITCH]
    assert len(wide) == 3, wide
    assert [round(s) for s in wide] == [42, 415, 41], wide


def test_each_circuit_of_twelve_outlets_runs_through_its_own_breaker():
    dev = _device()
    placements = _placements(dev, "front")
    breakers = [p["id"] for p in placements if p["ref"] == "raritan/px3-breaker@1"]
    assert sorted(breakers) == ["breaker-1", "breaker-2"]
    for n, p in _outlets(dev).items():
        assert p["through"] == ("breaker-1" if n <= 12 else "breaker-2"), n


def test_the_controller_carries_the_jacks_the_panel_drawing_shows():
    placed = _by_id(_device(), "front")
    jacks = {
        "eth-1": "common/rj45-eth@1", "eth-2": "common/rj45-eth@1", "feature": "std/rj45@2",
        "console": "std/rj45@2", "expansion": "std/rj45@2", "sensor": "std/rj45@2",
        "usb-a-1": "std/usb-a@1", "usb-a-2": "std/usb-a@1", "usb-b": "raritan/pxo-usb-b@1",
    }
    for pid, ref in jacks.items():
        assert placed[pid]["ref"] == ref, pid
    assert placed["display"]["ref"] == "raritan/pxo-lcd@1"
    assert placed["reset"]["ref"] == "common/reset-button@1"
    buttons = [p for p in placed.values() if p["ref"] == "raritan/pxo-button@1"]
    assert len(buttons) == 4


def _turn(p):
    return p.get("rotate", 0) % 360


def test_the_lower_row_of_rj45_jacks_is_the_upper_row_turned_a_half_turn():
    """The drawing's panel (pages 4 and 6, view C) draws the lower RJ45 row as a 180 degree mirror of the upper row.

    The upper row has its latch tab at the top and the lower row at the bottom.
    The strip stands with the drawing turned a quarter turn, so the upper row's latch faces the left.
    A quarter turn of 90 gives that, and the lower row needs the other quarter turn, 270.
    """
    placed = _by_id(_device(), "front")
    for upper, lower in (("eth-1", "eth-2"), ("feature", "console"), ("expansion", "sensor")):
        assert _turn(placed[upper]) == 90, upper
        assert _turn(placed[lower]) == 270, lower
        assert (_turn(placed[lower]) - _turn(placed[upper])) % 360 == 180, (upper, lower)


def test_the_two_ethernet_jacks_are_the_interfaces():
    dev = _device()
    physical = [i["physical"] for i in dev["interfaces"]]
    assert "eth-1" in physical and "eth-2" in physical
    assert any(i["physical"] == "outlet-{n}" and i["range"] == "1-24" for i in dev["interfaces"])
    speeds = {p["id"]: (p.get("attrs") or {}).get("speed") for p in _placements(dev, "front") if p["id"].startswith("eth-")}
    assert speeds == {"eth-1": "1g", "eth-2": "1g"}


def test_the_input_is_the_fixed_iec_60309_cord_at_the_cord_end():
    dev = _device()
    cord = _by_id(dev, "front")["input"]
    assert cord["ref"] == "raritan/px3-cord-60309@1"
    assert cord["at"][1] > 1480
    assert dev["attrs"]["power"]["input-cord"] == "fixed"
    assert dev["attrs"]["power"]["input-current-a"] == 32


def test_the_rear_carries_two_buttons_1244_apart_147_5_from_each_end():
    rear = _by_id(_device(), "rear")
    buttons = [p for p in rear.values() if p["ref"] == "raritan/px3-mounting-button@1"]
    assert len(buttons) == 2
    centres = sorted(p["at"][1] + 7.35 for p in buttons)
    assert round(centres[1] - centres[0], 2) == 1244.0
    assert round(centres[0], 2) == 147.5
    assert round(LENGTH - centres[1], 2) == 147.5


def test_every_outlet_has_a_lamp_drawn_off_with_its_states():
    dev = _device()
    lamps = [p for p in _placements(dev, "front") if p["id"].startswith("led-")]
    assert len(lamps) == 24
    group = dev["groups"]["outlet-leds"]
    states = group["states"]
    assert states[0] == "off"
    colours = {s["color"] for s in states[1:] if isinstance(s, dict)}
    assert len(colours) >= 2
    assert {p["for"] for p in lamps} == {f"outlet-{n}" for n in range(1, 25)}


def test_only_parts_already_in_the_library_are_used():
    refs = {p["ref"] for p in _placements(_device())}
    assert refs <= REUSED, refs - REUSED


def test_estimates_and_gaps_are_declared():
    dev = _device()
    assert dev["provenance"]["colours"]["confidence"] == "estimated"
    gaps = {g["what"] for g in dev.get("gaps", [])}
    assert {"eth2-speed", "mounting-button-size", "side-profile", "rack-kit", "jack-media"} <= gaps, gaps
    text = yaml.safe_dump(dev["provenance"]).lower()
    assert "no vendor stencil" in text and "no photograph" in text


def test_the_references_name_the_specification_and_its_drawing():
    dev = _device()
    assert "rev 2025-06-25" in dev["datasheet"]["title"]
    titles = " ".join(r["title"] for r in dev["references"])
    assert "MPX3-5493" in titles and "Mounting Brackets" in titles
