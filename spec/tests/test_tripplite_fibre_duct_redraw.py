"""The Eaton Tripp Lite series SRCABLEDUCT1UFC fibre duct, drawn from every feature the maker's spec
sheet photographs show (roc-ops/Portrayal#1094): three slots in each ear, the two rear windows where
the rear picture puts them, the block of two dark squares between them, and the pin seen through the
open end. Reads the device file and the back plate's skin, so it needs no build.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices/eaton/srcableduct1ufc/device.yaml"
BASE = LIB / "components/eaton/tripplite-duct-1ufc-base/v1"
WIDTH, HEIGHT = 494.79, 55.12


def device():
    return yaml.safe_load(DEVICE.read_text())


def rear_decor():
    return {e["id"]: e for e in device()["views"]["rear"]["panel"]["decor"]}


def left_decor():
    return {e["id"]: e for e in device()["views"]["left"]["panel"]["decor"]}


def test_each_ear_has_three_slots_on_the_rear_and_the_floor():
    slots = {i: e for i, e in rear_decor().items() if e.get("kind") == "ear-slot"}
    assert len(slots) == 6
    for left in (True, False):
        ear = sorted((e for e in slots.values() if (e["at"][0] < WIDTH / 2) == left), key=lambda e: e["at"][1])
        assert len(ear) == 3
        pitches = [round(b["at"][1] - a["at"][1], 2) for a, b in zip(ear, ear[1:])]
        assert pitches == [20.0, 20.0], "the photograph's holes are evenly spaced"
        assert abs((ear[0]["at"][1] + ear[2]["at"][1] + ear[2]["size"][1]) / 2 - HEIGHT / 2) < 0.01, "centred on the plate"
    skin = (BASE / "skins/default.svg").read_text()
    subpaths = len(re.findall(r"M\s*[0-9]", skin))
    assert subpaths == 1 + 6 + 2, "the plate outline, six ear slots and two windows are one path"


def test_the_rear_windows_stand_where_the_rear_picture_puts_them_and_are_the_passes():
    d = device()
    r = rear_decor()
    windows = [p for p in d["views"]["rear"]["passes"]]
    assert [p["id"] for p in windows] == ["rear-window-1", "rear-window-2"]
    a, b = windows
    assert a["size"] == b["size"] == [126, 22]
    # symmetric about the middle of the plate, the same margin each end
    assert abs(a["at"][0] - (WIDTH - b["at"][0] - b["size"][0])) < 0.5
    assert 78 <= a["at"][0] <= 86, "about 82 mm in from each end"
    # the outlines and the plate pieces follow the passes
    assert r["window-1-outline"]["at"][0] == a["at"][0] and r["window-2-outline"]["at"][0] == b["at"][0]
    pieces = [r[i] for i in ("back-left", "back-middle", "back-right")]
    assert round(sum(p["size"][0] for p in pieces) + 2 * 126, 2) == WIDTH, "the plate pieces and the windows tile the band"


def test_two_dark_squares_stand_between_the_windows():
    d = device()
    r = rear_decor()
    squares = sorted((e for e in r.values() if e.get("kind") == "centre-block"), key=lambda e: e["at"][0])
    assert len(squares) == 2
    a, b = d["views"]["rear"]["passes"]
    for s in squares:
        assert a["at"][0] + a["size"][0] < s["at"][0] and s["at"][0] + s["size"][0] < b["at"][0]
        assert abs(s["size"][0] - 25) < 0.5 and abs(s["size"][1] - 30) < 0.5
    assert abs((squares[0]["at"][0] + squares[1]["at"][0] + squares[1]["size"][0]) / 2 - WIDTH / 2) < 1.0, "centred on the plate"
    gap = next(g for g in d["gaps"] if g["what"] == "rear-centre-block")
    assert gap["reason"] == "needs-photo" and "drawn as marks" in gap["note"], "drawn, with what it is left open"


def test_the_pin_seen_through_the_open_end_is_a_small_disc_on_the_left_face():
    pin = left_decor()["end-pin"]
    assert pin["kind"] == "pin" and pin["size"][0] == pin["size"][1] == 2.5 and pin.get("rx") == 1.25


def test_the_notes_say_what_the_photographs_show_and_how_it_was_read():
    notes = device()["provenance"]
    assert "three" in notes["ears"]["note"].lower() and "20 mm" in notes["ears"]["note"]
    text = notes["passes"]["note"]
    assert "middle of the dark block" in text and "perspective" in text
    assert re.search(r"two dark squares", notes["rear"]["note"])
