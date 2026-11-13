"""The L section of the Middle Atlantic LBP-1A is drawn with raised plates; these tests hold its figures.

They read the device file only and build nothing. The kit does not check that the gauge is written alike in
every place, so these tests do it for this device.
"""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "middle-atlantic" / "lbp-1a" / "device.yaml"
DATA = yaml.safe_load(DEVICE.read_text())
GAUGE = DATA["chassis"]["thickness"]
WIDTH = DATA["chassis"]["width"]
EAR_LENGTH = 20
SIDES = ("left", "right")


def decor(view):
    return {d["id"]: d for d in DATA["views"][view]["panel"]["decor"]}


def rect(d):
    x, y = d["at"]
    w, h = d["size"]
    return (round(x, 3), round(y, 3), round(x + w, 3), round(y + h, 3))


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def area(r):
    return round((r[2] - r[0]) * (r[3] - r[1]), 3)


def notes():
    text = " ".join(v["note"] for v in DATA["provenance"].values())
    text += " " + " ".join(g["note"] for g in DATA["gaps"])
    return " ".join(text.split()).lower()


def frames(side):
    return [d for d in DATA["views"]["top"]["panel"]["decor"] if re.fullmatch(f"ear-{side}-[a-d]", d["id"])]


def test_gauge_is_the_chassis_thickness():
    assert GAUGE == 1.5


def test_web_and_leg_stand_out_by_the_gauge():
    assert decor("front")["web"].get("out") == GAUGE
    assert decor("top")["leg"].get("out") == GAUGE


def test_web_starts_one_gauge_above_and_is_one_gauge_taller():
    web = decor("front")["web"]
    height = DATA["views"]["front"]["size"]["h"]
    assert web["at"][1] == -GAUGE
    assert round(web["size"][1], 3) == round(height + GAUGE, 3)


def test_web_stops_where_each_ear_starts():
    web = decor("front")["web"]
    assert web["at"][0] == EAR_LENGTH
    assert round(web["at"][0] + web["size"][0], 3) == round(WIDTH - EAR_LENGTH, 3)


def test_other_faces_build_nothing():
    for view in ("front", "rear", "top", "bottom", "left", "right"):
        for d in DATA["views"][view]["panel"]["decor"]:
            raised = (view, d["id"]) in {("front", "web"), ("top", "leg")} or re.fullmatch(r"ear-(left|right)-[a-d]", d["id"])
            if raised:
                continue
            if d.get("vent"):
                continue
            assert "sink" not in d and "out" not in d, (view, d["id"])


def test_each_ear_is_four_raised_rects_round_its_hole():
    top = decor("top")
    for side in SIDES:
        ear = rect(top[f"ear-{side}"])
        hole = rect(top[f"ear-hole-{side}"])
        parts = frames(side)
        assert len(parts) == 4, side
        boxes = [rect(p) for p in parts]
        for p in parts:
            assert p.get("out") == GAUGE, p["id"]
            assert p["kind"] == "ear-frame", p["id"]
        assert sum(area(b) for b in boxes) == round(area(ear) - area(hole), 3), side
        for i, b in enumerate(boxes):
            assert b[0] >= ear[0] and b[1] >= ear[1] and b[2] <= ear[2] and b[3] <= ear[3], parts[i]["id"]
            assert not overlap(b, hole), parts[i]["id"]
            for c in boxes[:i]:
                assert not overlap(b, c), parts[i]["id"]


def test_ears_are_level_with_the_leg():
    leg_out = decor("top")["leg"].get("out")
    assert leg_out == GAUGE
    for side in SIDES:
        assert [p.get("out") for p in frames(side)] == [leg_out] * 4


def test_painted_ears_and_holes_stay_in_the_drawing():
    for view in ("top", "bottom"):
        d = decor(view)
        assert d["ear-left"]["at"] == [0, 4] and d["ear-left"]["size"] == [20, 8] and d["ear-left"]["rx"] == 2
        assert d["ear-right"]["at"] == [462.6, 4] and d["ear-right"]["size"] == [20, 8]
        assert d["ear-hole-left"]["at"] == [3, 6] and d["ear-hole-left"]["size"] == [10, 3]
        assert d["ear-hole-right"]["at"] == [469.6, 6] and d["ear-hole-right"]["size"] == [10, 3]
        assert d["ear-hole-left"]["vent"] == 1.5 and d["ear-hole-right"]["vent"] == 1.5


def test_slots_stay_painted_vents():
    for view in ("front", "rear", "top", "bottom"):
        slots = [d for d in DATA["views"][view]["panel"]["decor"] if d["kind"] == "tie-slot"]
        assert len(slots) == 10, view
        assert all(d["shape"] == "slot" and d.get("vent") == 1.5 and "out" not in d for d in slots), view


def test_stated_box_is_the_makers():
    chassis = DATA["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (482.6, 12.7, 12.7)


def test_notes_state_the_rule():
    text = notes()
    for phrase in (
        "the web is the face toward the front",
        "runs back from the web's top edge",
        "does not say which is which",
        "every `out` on a base plate",
        "one gauge above the top edge",
        "leave a groove",
        "frame of four raised rects",
        "neither `sink` nor `out`",
    ):
        assert phrase in text, phrase


def test_notes_state_each_limit():
    text = notes()
    for phrase in (
        "no closed end cap",
        "only if you know to look for one",
        "do not show in 3d",
        "1.5 mm larger in each direction",
        "nothing checks",
    ):
        assert phrase in text, phrase
