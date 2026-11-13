"""The door of a single-sided Chatsworth Motive vertical cable manager draws what the maker's pictures show.

The data sheet's page 1 photograph shows the front door in three panels.
A plate runs down its upper part.
A white block at the plate's top carries the maker's mark.
The installation instructions (page 3) say the door has two blue latches on its back.
They draw them on the door seen from inside.
These tests cover the ten parts, 32610 to 32614, each in -703 and -E03.
The plate, the two seams and the reserved logo place are drawn on the 10 in width only (32612).
The photograph is read as showing that width.
The held pictures put the middle strip and the plate at widths that do not agree in millimetres at any listed width.
The other eight doors do not draw them and keep a gap that says so.
On the 10 in door the seams are at 0.234 and 0.729 of the width as read from the photograph.
The right seam is read, not mirrored from the left.
The plate is 109.4 wide from 65.8 and 740 high from 380.
Its edges stand about 7 mm from each seam, measured on the photograph at 2.804 mm per pixel.
The corners are rounded as each picture shows.
The white plate is rounded at the bottom and the black one at the top.
Every door has both handle tips at its edges.
The notes say the render shows one dot, at the right edge.
They say the left tip is built as the right.
The device draws the latches on its rear, left and right faces.
Both housings are at the proportion read from the installation figure, 4.7 to 1, each at its own width.
The rear housing is 17 by 80 and the side housing is 15 by 70.5.
The device keeps one gap for the hook, which no held picture shows.
Five more gaps name what each device's own frame part draws in a following change.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
HEIGHT = 2133.6
WIDTHS = {0: 150.0, 1: 200.0, 2: 250.0, 3: 300.0, 4: 380.0}
PARTS = [f"3261{w}-{c}" for w in WIDTHS for c in ("703", "e03")]
PICTURED = [p for p in PARTS if p.startswith("32612")]
OTHERS = [p for p in PARTS if p not in PICTURED]
FACE_IDS = {"seam-left", "seam-right", "door-plate", "logo-zone"}
TIP_IDS = {"latch-tip-left", "latch-tip-right"}
HOUSING_W = 17.0
HOUSING_H = 80.0
SIDE_W = 15.0
SIDE_H = 70.5
SENTENCE_LIMIT = 25
OLD_SCALE = "2.79" + "6"
FRAME_GAPS = {
    "end-caps": ["front"],
    "feet": ["front"],
    "door-hinge-tabs": ["rear"],
    "side-plate-holes": ["left", "right"],
    "track-rungs": ["rear", "left", "right"],
}


def width(part):
    return WIDTHS[int(part[4])]


def door_dir(part):
    return LIB / "components" / "chatsworth" / f"motive-{part}-door" / "v1"


def door(part):
    return yaml.safe_load((door_dir(part) / "contract.yaml").read_text())


def skin_rects(part):
    text = (door_dir(part) / "skins" / "default.svg").read_text()
    out = {}
    for m in re.finditer(r"<(rect|path) id=\"([^\"]+)\"([^>]*)>", text):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(3)))
        attrs["tag"] = m.group(1)
        out[m.group(2)] = attrs
    return out


def device(part):
    return yaml.safe_load((LIB / "devices" / "chatsworth" / part / "device.yaml").read_text())


def decor(doc, view):
    return {d["id"]: d for d in doc["views"][view]["panel"]["decor"]}


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if s]


@pytest.mark.parametrize("part", PICTURED)
def test_the_pictured_width_draws_the_seams_and_the_plate_read_from_the_photograph(part):
    rects = skin_rects(part)
    assert FACE_IDS | TIP_IDS <= set(rects)
    zone = rects["logo-zone"]
    assert zone["fill"] == "none" and "stroke" not in zone, "the maker's mark is reserved, never painted"
    el = door(part)["elements"]
    assert width(part) == 250.0
    # The seams are at 0.234 and 0.729 of the door, 20.3 and 63.3 px of 86.8. The right one is read, not mirrored.
    left = float(rects["seam-left"]["x"]) + float(rects["seam-left"]["width"]) / 2
    right = float(rects["seam-right"]["x"]) + float(rects["seam-right"]["width"]) / 2
    assert left == pytest.approx(58.5, abs=0.3)
    assert right == pytest.approx(182.3, abs=0.3)
    assert right != pytest.approx(250 - left, abs=3), "the right seam is read from the picture, not mirrored"
    # The plate is 39 px wide and 264 px high at 2.804 mm per px. It stands 2.6 and 2.5 px, about 7 mm, from the seams.
    plate_left = el["door-plate"]["at"][0]
    plate_right = plate_left + el["door-plate"]["size"][0]
    assert plate_left - left == pytest.approx(7.3, abs=0.5), "the plate stands about 7 mm from the left seam"
    assert right - plate_right == pytest.approx(7.1, abs=0.5), "the plate stands about 7 mm from the right seam"
    assert el["door-plate"]["at"] == [65.8, 380] and el["door-plate"]["size"] == [109.4, 740]
    assert el["logo-zone"]["at"] == el["door-plate"]["at"]
    assert el["logo-zone"]["size"] == [109.4, 204]
    assert zone["x"] == "65.8" and zone["y"] == "380"
    assert "1120" in rects["door-plate"]["d"], "the plate's foot is 380 + 740"


@pytest.mark.parametrize("part", PICTURED)
def test_the_plate_corners_are_rounded_as_each_picture_shows(part):
    plate = skin_rects(part)["door-plate"]
    assert plate["tag"] == "path", "the plate has rounded corners, so it is a path"
    arcs = re.findall(r"A\s*([\d.]+)\s+([\d.]+)\s+0\s+0\s+1", plate["d"])
    assert len(arcs) == 2, "two rounded corners"
    radius = 6.0 if part.endswith("e03") else 20.0
    assert all(float(a) == radius and float(b) == radius for a, b in arcs)
    first = plate["d"].split("A")[0]
    if part.endswith("e03"):
        assert first.startswith("M65.8 380"), "the white plate's top is square"
    else:
        assert not first.startswith("M65.8 380"), "the black plate's top corners are rounded"


@pytest.mark.parametrize("part", OTHERS)
def test_the_other_widths_do_not_draw_the_plate_or_the_seams(part):
    rects = skin_rects(part)
    assert not FACE_IDS & set(rects)
    assert not FACE_IDS & set(door(part)["elements"])
    gaps = {g["what"]: g for g in device(part)["gaps"]}
    assert gaps["door-plate-and-seams"]["scope"] == ["front"]
    assert gaps["door-plate-and-seams"]["reason"] == "vendor-silent"
    assert "millimetres" in gaps["door-plate-and-seams"]["note"]


@pytest.mark.parametrize("part", PICTURED)
def test_the_pictured_width_keeps_no_gap_for_the_plate(part):
    assert "door-plate-and-seams" not in {g["what"] for g in device(part)["gaps"]}


@pytest.mark.parametrize("part", PARTS)
def test_every_door_has_both_handle_tips_at_its_edges(part):
    rects = skin_rects(part)
    w = width(part)
    assert TIP_IDS <= set(rects)
    left, right = rects["latch-tip-left"], rects["latch-tip-right"]
    assert float(left["x"]) == 0 and float(left["width"]) == 2
    assert float(right["x"]) + float(right["width"]) == pytest.approx(w)
    assert left["y"] == right["y"] and left["height"] == right["height"], "the left tip is built as the right tip"


@pytest.mark.parametrize("part", PARTS)
def test_the_notes_give_the_reason_for_the_choice_in_one_short_sentence(part):
    prov = door(part)["provenance"]
    for key in ("logo-zone", "seams", "latches", "hook", "door-geometry"):
        assert key in prov
    assert prov["logo-zone"].startswith("estimated" if part in PICTURED else "not drawn")
    reason = prov["door-geometry"]
    assert "do not agree in millimetres at any listed width" in reason
    assert len(sentences(reason)) == 1 and len(reason.split()) <= SENTENCE_LIMIT
    if part in PICTURED:
        assert "drawn on this width only" in reason
    else:
        assert "not drawn on this width" in reason
    latches = " ".join(prov["latches"].split())
    assert "one dot" in latches and "right edge" in latches
    assert "left tip is built as the right tip" in latches and "no picture shows it" in latches
    assert "4.7 to 1" in latches and "stand-in" in latches
    assert "8 to 1" not in latches
    for key in ("logo-zone", "seams", "door-geometry", "latches", "hook"):
        assert all(len(s.split()) <= SENTENCE_LIMIT for s in sentences(prov[key])), prov[key]


@pytest.mark.parametrize("part", PICTURED)
def test_the_pictured_width_says_it_is_read_as_10_in(part):
    text = " ".join(door(part)["provenance"]["logo-zone"].split())
    assert "read as 10 in" in text and "inferred" in text
    assert "shows one 10 in" not in text
    assert "2.804 mm per px" in text and OLD_SCALE not in text, "one scale, derived once"
    assert "about 7 mm from each seam" in text


@pytest.mark.parametrize("part", PARTS)
def test_the_latches_are_drawn_where_the_back_of_the_door_is_seen(part):
    doc = device(part)
    rear = decor(doc, "rear")
    w = width(part)
    for side in ("left", "right"):
        housing, handle = rear[f"latch-{side}-housing"], rear[f"latch-{side}-handle"]
        assert housing["size"] == [HOUSING_W, HOUSING_H], "the housing is drawn at the figure's 4.7 to 1"
        assert housing["size"][1] / housing["size"][0] == pytest.approx(4.7, abs=0.05)
        centre = housing["at"][1] + housing["size"][1] / 2
        assert centre == pytest.approx(0.473 * HEIGHT, abs=2)
        assert handle["rx"] > 0, "a handle is a round part"
        edge = housing["at"][0] + housing["size"][0] if side == "left" else w - housing["at"][0]
        assert edge <= w / 2, "each latch sits at its own side edge"
    assert rear["latch-left-housing"]["at"][0] + rear["latch-right-housing"]["at"][0] + 17 == pytest.approx(w, abs=0.1)
    for view in ("left", "right"):
        side = decor(doc, view)
        assert {"latch-housing", "latch-handle"} <= set(side)
        size = side["latch-housing"]["size"]
        assert size == [SIDE_W, SIDE_H], "the side housing keeps the figure's 4.7 to 1 at its own width"
        assert size[1] / size[0] == pytest.approx(4.7, abs=0.05)
        assert side["latch-housing"]["at"][1] + size[1] / 2 == pytest.approx(0.473 * HEIGHT, abs=2)


@pytest.mark.parametrize("part", PARTS)
def test_the_gaps_name_the_hook_and_what_the_frame_part_draws_later(part):
    gaps = {g["what"]: g for g in device(part)["gaps"]}
    assert "door-features" not in gaps
    assert gaps["door-hook"]["scope"] == ["rear"]
    assert "no held picture shows it" in gaps["door-hook"]["note"]
    for what, scope in FRAME_GAPS.items():
        gap = gaps[what]
        note = " ".join(gap["note"].split())
        assert gap["scope"] == scope and gap["reason"] == "vendor-silent" and gap["wanted"]
        assert "each device's own frame part, which a following change draws" in note, what
        assert "shared frame" not in note and "next part for this family" not in note
        assert all(len(s.split()) <= SENTENCE_LIMIT for s in sentences(note)), note
    assert "side-plate-holes" in gaps and "track-rungs" in gaps
    assert "a plate that carries two holes" in " ".join(gaps["feet"]["note"].split())


@pytest.mark.parametrize("part", PARTS)
def test_no_note_of_the_change_carries_the_old_scale_or_the_shared_frame(part):
    texts = [(door_dir(part) / "contract.yaml").read_text(),
             (LIB / "devices" / "chatsworth" / part / "device.yaml").read_text(),
             (ROOT / "changelog.d" / "chatsworth-motive-door-features.md").read_text()]
    for text in texts:
        assert OLD_SCALE not in text and "shared frame" not in text and "twenty devices" not in text


def test_this_modules_docstring_has_no_list_and_no_long_sentence():
    doc = __doc__
    assert not re.search(r"^\s*[-*] ", doc, re.M), "no bullets: a list counts as one long sentence"
    assert not re.search(r":\s*$", doc, re.M), "no line ends in a colon"
    assert all(len(s.split()) <= SENTENCE_LIMIT for s in sentences(doc))
