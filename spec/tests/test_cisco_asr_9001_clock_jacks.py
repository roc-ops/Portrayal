"""The ASR 9001's 10MHz and 1PPS holes have their DIN 1.0/2.3 jacks in them.

Cisco ASR 9000 Series Fixed-Port Routers Hardware Installation Guide, Table 4 "Cisco ASR 9901 and Cisco ASR 9001
Router Front Panel Ports Description" gives both connectors as DIN 1.0/2.3, and Figure 13 shows the two round jacks
side by side. The registry now holds the key and a jack part, so the two holes that were drawn without one are
filled by that part under the ids they already had, instead of standing as holes with nothing in them.

These read the library's own files. They read no library/dist and render nothing.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
JACK = "common/din-1-0-2-3-jack@1"
CLOCKS = ("clk-10mhz", "clk-1pps")
# the jack's core sits 0.71 mm inside its spanner nut, in a 5.59 mm round hole
CORE_OFFSET = 0.71
HOLE = 5.59


def front():
    doc = yaml.safe_load((LIB / "devices/cisco/asr-9001/device.yaml").read_text())
    return doc["views"]["front"], doc


def test_each_clock_hole_has_a_jack_of_its_own_id():
    view, _ = front()
    placed = {p["id"]: p for p in view["components"]["placements"]}
    for cid in CLOCKS:
        assert placed[cid]["ref"] == JACK
        assert placed[cid]["group"] == "timing"


def test_each_hole_is_the_jacks_round_opening_on_the_jacks_centre():
    view, _ = front()
    placed = {p["id"]: p for p in view["components"]["placements"]}
    cutouts = {c["id"]: c for c in view["panel"]["cutouts"]}
    for cid in CLOCKS:
        assert cutouts[cid]["size"] == [HOLE, HOLE]
        assert cutouts[cid]["shape"] == "circle"
        assert [round(v, 3) for v in cutouts[cid]["at"]] == [
            round(placed[cid]["at"][0] + CORE_OFFSET, 3), round(placed[cid]["at"][1] + CORE_OFFSET, 3)]


def test_no_hole_on_the_front_is_left_with_nothing_in_it():
    view, _ = front()
    ids = {i["id"] for i in view["components"]["placements"]} | {i["id"] for i in view["components"].get("bays", [])}
    assert [c["id"] for c in view["panel"]["cutouts"] if c["id"] not in ids] == []


def test_the_gap_that_asked_for_the_part_is_closed():
    _, doc = front()
    assert "din-1-0-2-3-connector" not in {g["what"] for g in doc["gaps"]}
