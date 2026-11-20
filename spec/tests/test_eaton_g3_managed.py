"""The Eaton ePDU G3 managed EMAU07-10: what is true of its device file.

No build is needed: each test reads the device and its contract from the library folder.
"""
import pathlib

import yaml

LIB = pathlib.Path(__file__).resolve().parents[2] / "library"
DEVICE = yaml.safe_load((LIB / "devices/eaton/emau07-10/device.yaml").read_text())
CORD = yaml.safe_load((LIB / "components/eaton/g3-cord-l6-30p-front/v1/contract.yaml").read_text())


def _placements(view):
    return DEVICE["views"][view]["components"]["placements"]


def test_sixteen_c13_outlets_in_two_sections():
    outlets = [p for p in _placements("front") if p["ref"] == "std/c13-outlet@1"]
    assert len(outlets) == 16
    assert {p["through"] for p in outlets} == {"breaker-a", "breaker-b"}
    assert sum(1 for p in outlets if p["through"] == "breaker-a") == 8


def test_body_is_the_drawings_size():
    chassis = DEVICE["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"], chassis["ru"]) == (444.5, 87.1, 213.2, 2)


def test_every_outlet_is_named_as_printed():
    names = {rule["name"] for rule in DEVICE["interfaces"]}
    assert names == {"A{n}", "B{n}"}


def test_the_cord_part_is_the_round_gland():
    assert CORD["size"] == {"w": 27.2, "h": 39.1}
    assert CORD["attrs"]["plug"] == "nema-l6-30p"


def test_the_module_has_its_ports_and_buttons():
    ids = {p["id"] for p in _placements("front")}
    assert {"serial", "daisy-chain", "network", "usb", "reset", "display"} <= ids
    assert {"button-up", "button-down", "button-esc", "button-enter"} <= ids


def test_each_end_carries_the_four_holes_the_perspective_shows():
    for side in ("left", "right"):
        holes = [d for d in DEVICE["views"][side]["panel"]["decor"] if d["kind"] == "hole"]
        assert len(holes) == 4


def test_the_end_holes_stand_where_the_perspective_puts_them():
    """The holes sit at about 20 and 66 mm from the rear and 22 and 66.8 mm down, each about 8 by 9 mm."""
    depth = DEVICE["chassis"]["depth"]
    for side in ("left", "right"):
        holes = [d for d in DEVICE["views"][side]["panel"]["decor"] if d["kind"] == "hole"]
        cols, rows = set(), set()
        for d in holes:
            cx = d["at"][0] + d["size"][0] / 2
            cols.add(round(cx if side == "left" else depth - cx))
            rows.add(round(d["at"][1] + d["size"][1] / 2, 1))
            assert 6.0 <= d["size"][0] <= 10.0 and 7.0 <= d["size"][1] <= 11.0
        assert len(cols) == 2 and len(rows) == 2
        assert all(abs(c - t) <= 3 for c, t in zip(sorted(cols), (20, 66)))
        assert all(abs(r - t) <= 3 for r, t in zip(sorted(rows), (22.0, 66.8)))


def test_the_rear_lip_is_as_far_from_the_right_end_as_from_the_left_and_a_band_runs_along_the_top():
    """The sheet's rear lip is symmetric, 3.7 mm high, and a band 2.6 mm high runs the full width above."""
    decor = {d["id"]: d for d in DEVICE["views"]["rear"]["panel"]["decor"]}
    width = DEVICE["views"]["rear"]["size"]["w"]
    lip, band = decor["rear-lip"], decor["rear-band"]
    assert abs(lip["at"][0] - (width - lip["at"][0] - lip["size"][0])) <= 1.0
    assert abs(lip["size"][1] - 3.7) <= 0.5 and abs(lip["at"][1] + lip["size"][1] - DEVICE["views"]["rear"]["size"]["h"]) <= 0.5
    assert band["at"] == [0, 0] and abs(band["size"][0] - width) <= 0.1 and abs(band["size"][1] - 2.6) <= 0.5


def test_the_six_top_screws_are_six_millimetres_with_a_star_socket_each():
    """The plan's screws are about 6.0 mm across with a six-point star socket, as the sheet draws them."""
    top = DEVICE["views"]["top"]
    screws = [d for d in top["panel"]["decor"] if d["kind"] == "screw-head"]
    assert len(screws) == 6 and all(abs(d["size"][0] - 6.0) <= 0.4 for d in screws)
    assert len([m for m in top.get("silkscreen") or [] if m["id"].startswith("socket-")]) == 6


def test_sixteen_lamps_two_tiles_of_eight():
    lamps = [p for p in _placements("front") if p["ref"] == "common/led-dot@1"]
    assert len(lamps) == 16
