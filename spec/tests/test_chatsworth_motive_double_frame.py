"""The frame fittings of the Chatsworth Motive double-sided managers.

The data sheet's page 1 photograph shows caps on the top and feet on a base plate.
Its page 3 render shows four caps, three feet, a flat plate between the two channels, a cross tube and a pale rear beam.
The installation plan adds squares, a slot, screws, a base rail and rounded lower corners on the centre section.
Each device draws them on the top, bottom, left and right faces.
Every figure is read in one direction at that direction's scale, and the notes name both.
Each door plate hides them on the front and rear faces.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = {"0": 150, "1": 200, "2": 250, "3": 300, "4": 380}
MODELS = [f"3262{n}-{c}" for n in "01234" for c in ("703", "e03")]
LIMIT = 25


def load(model):
    path = ROOT / "library" / "devices" / "chatsworth" / model / "device.yaml"
    return yaml.safe_load(path.read_text())


def decor(dev, view):
    return {d["id"]: d for d in dev["views"][view]["panel"]["decor"]}


def of_kind(d, kind):
    return [v for v in d.values() if v["kind"] == kind]


@pytest.mark.parametrize("model", MODELS)
def test_top_draws_four_corner_caps_of_one_size_on_every_width(model):
    dev = load(model)
    width, depth = dev["chassis"]["width"], dev["chassis"]["depth"]
    assert width == WIDTHS[model[4]]
    top = decor(dev, "top")
    caps = of_kind(top, "end-cap")
    assert len(caps) == 4
    assert len(of_kind(top, "rail")) == 2 and len(of_kind(top, "cross-tube")) == 1
    assert "cross-tube-front" not in top, "the tube stands at mid-depth, not at the front end"
    assert top["top-rail-left"]["size"][0] == top["top-rail-right"]["size"][0] == 70.5, "15.25 rows, 16 pixels along the width axis, 4.4 mm per pixel"
    assert top["top-rail-right"]["at"][0] == width - 70.5
    assert top["cross-tube"]["size"] == [width, 54.6]
    assert top["cross-tube"]["at"] == [0, 304.4]
    assert top["rear-beam"]["at"] == [0, 3] and top["rear-beam"]["size"] == [width, 25.9]
    assert all(v["size"] == [75, 37.5] for v in caps)
    assert sorted(v["at"][0] for v in caps) == sorted([0, 0, width - 75, width - 75])
    assert sorted(v["at"][1] for v in caps) == sorted([3, 3, depth - 3 - 37.5, depth - 3 - 37.5])


@pytest.mark.parametrize("model", MODELS)
def test_bottom_draws_four_feet_the_rim_and_four_plate_holes(model):
    dev = load(model)
    d = decor(dev, "bottom")
    width, depth = dev["chassis"]["width"], dev["chassis"]["depth"]
    feet, holes = of_kind(d, "foot"), of_kind(d, "hole")
    assert len(feet) == 4 and len(holes) == 4 and len(of_kind(d, "rail")) == 2
    assert all(v["size"] == [58.9, 29.5] for v in feet)
    assert d["base-rim"]["size"] == [width, depth] and "fill" not in d["base-rim"]
    assert all(v["size"][0] == 70.5 for v in of_kind(d, "rail"))
    for h in holes:
        assert h["size"][0] == h["size"][1] == 7.9 and h["rx"] == 4, "3 rows x 2.624 mm per row"
        assert 0 < h["at"][1] < depth


@pytest.mark.parametrize("view", ["left", "right"])
@pytest.mark.parametrize("model", MODELS)
def test_sides_draw_caps_feet_rim_centre_plate_and_holes(model, view):
    dev = load(model)
    d = decor(dev, view)
    height, depth = dev["chassis"]["height"], dev["chassis"]["depth"]
    assert [len(of_kind(d, k)) for k in ("end-cap", "foot", "base-plate", "centre-plate", "mark")] == [2, 2, 3, 2, 1]
    assert all(v["size"] == [37.5, 21] and v["at"][1] == 0 for v in of_kind(d, "end-cap"))
    assert all(v["size"] == [29.5, 13.1] and abs(v["at"][1] + 13.1 - height) < 1e-6 for v in of_kind(d, "foot"))
    assert d["base-rim"]["size"][1] == 7.9 and abs(d["base-rim"]["at"][1] + 7.9 - height) < 1e-6, "3 rows x 2.624 mm per row, 7.87"
    plate, corners = d["centre-plate"], d["centre-plate-foot"]
    assert plate["at"][0] == 201 and plate["size"][0] == 198
    assert plate["size"][1] == round(height - 21 - 7.9 - 26, 1), "the body stops two radii short"
    assert corners["size"] == [198, 39] and corners["rx"] == 13 and corners["at"][1] == round(21 + height - 21 - 7.9 - 39, 1)
    assert [d[f"base-rail-{e}"]["size"][1] for e in ("rear", "front")] == [32.8, 32.8], "44 pixels at 0.744 mm per pixel"
    if view == "left":
        assert len(of_kind(d, "hole")) == 4 + 4 + 3 + 9 + 1 + 3 + 9 + 1 and len(of_kind(d, "slot")) == 2
    else:
        assert len(of_kind(d, "hole")) == 3 + 4 + 3 + 9 + 1 + 3 + 9 + 1 and len(of_kind(d, "slot")) == 2 + 2
    assert len(of_kind(d, "mounting-hole")) == 5 + 6 and len(of_kind(d, "screw")) == 4
    round_holes = [d[f"centre-plate-hole-{w}-{i}"] for w in ("top", "bottom") for i in (1, 2, 3, 4) if f"centre-plate-hole-{w}-{i}" in d]
    assert all(h["size"] == [13.1, 13.1] for h in round_holes if h["id"] != "centre-plate-hole-top-1" or view == "left"), "2.57 columns x 5.1 mm per column"
    ids = {v["id"] for v in d.values()}
    assert {"end-cap-rear", "end-cap-front", "foot-rear", "foot-front"} <= ids
    rear_cap, front_cap = d["end-cap-rear"], d["end-cap-front"]
    if view == "left":
        assert rear_cap["at"][0] < front_cap["at"][0]
    else:
        assert rear_cap["at"][0] > front_cap["at"][0], "the rear end is on the right in the right view"
    assert 0 <= min(v["at"][0] for v in d.values() if v["kind"] in ("hole", "end-cap", "foot"))
    assert max(v["at"][0] + v["size"][0] for v in d.values() if v["kind"] in ("hole", "end-cap", "foot")) <= depth


FRAME_KINDS = {"end-cap", "foot", "base-plate", "hole", "slot", "centre-plate", "rail", "cross-tube", "beam", "mounting-hole", "screw", "mark"}


@pytest.mark.parametrize("model", MODELS)
def test_each_view_carries_the_counted_number_of_frame_items(model):
    dev = load(model)
    counts = {view: len([v for v in decor(dev, view).values() if v["kind"] in FRAME_KINDS]) for view in ("top", "bottom", "left", "right")}
    assert counts == {"top": 8, "bottom": 11, "left": 61, "right": 62}
    assert sum(counts.values()) == 142


def centre(v):
    return (v["at"][0] + v["size"][0] / 2, v["at"][1] + v["size"][1] / 2)


def close(got, want):
    """Each figure is written to one decimal place, so a centre is within 0.16 of the computed one."""
    got, want = list(got), list(want)
    assert len(got) == len(want) and all(abs(a - b) <= 0.16 for a, b in zip(got, want)), (got, want)


@pytest.mark.parametrize("view", ["left", "right"])
@pytest.mark.parametrize("model", MODELS)
def test_the_plan_squares_slot_and_screws_stand_on_the_centre_section(model, view):
    dev = load(model)
    d = decor(dev, view)
    height = dev["chassis"]["height"]
    mirror = view == "right"

    def x_of(x):
        return 600 - x if mirror else x

    close(sorted(centre(d[f"plan-square-{i}"])[0] for i in (1, 2, 3, 4)), sorted(x_of(x) for x in (231.9, 254.2, 347.3, 368.9)))
    assert all(d[f"plan-square-{i}"]["size"] == [14.1, 14.1] for i in (1, 2, 3, 4))
    assert d["plan-slot"]["size"] == [26.1, 14.1]
    close([centre(d["plan-slot"])[0]], [x_of(300.4)])
    close([centre(d["plan-square-1"])[1]], [height - 7.9 - 122.4])
    close(sorted(centre(d[f"plan-screw-{i}"])[0] for i in (1, 2, 3, 4)), sorted(x_of(x) for x in (217.4, 275.4, 325.3, 382.6)))
    assert all(d[f"plan-screw-{i}"]["size"] == [14.9, 14.9] and "fill" not in d[f"plan-screw-{i}"] for i in (1, 2, 3, 4))


@pytest.mark.parametrize("model", MODELS)
def test_the_right_face_draws_the_far_plates_head_pattern_not_the_near_plates(model):
    d = decor(load(model), "right")
    assert [k for k in d if k.startswith("centre-plate-hole-top-")] == [f"centre-plate-hole-top-{i}" for i in (1, 2, 3)]
    close([c for i in (1, 2, 3) for c in centre(d[f"centre-plate-hole-top-{i}"])], [218.3, 47.9, 267.3, 111.9, 309.6, 134.4])
    assert d["centre-plate-hole-top-1"]["size"] == [15.3, 15.3], "3 columns x 5.1 mm per column"
    assert d["centre-plate-hole-top-2"]["size"] == [13.1, 13.1] and d["centre-plate-hole-top-3"]["size"] == [13.1, 13.1]
    close([c for i in (1, 2) for c in centre(d[f"centre-plate-slot-head-{i}"])], [264.8, 130.8, 331.6, 133.2])
    assert d["centre-plate-slot-head-1"]["size"] == [20.4, 8.5] and d["centre-plate-slot-head-2"]["size"] == [20.4, 8.5]
    left = decor(load(model), "left")
    assert not any(k.startswith("centre-plate-slot-head-") for k in left)
    assert "centre-plate-hole-top-4" in left and "centre-plate-hole-top-4" not in d


@pytest.mark.parametrize("view", ["left", "right"])
@pytest.mark.parametrize("model", MODELS)
def test_the_foot_slots_the_fifth_dot_and_the_page_3_squares(model, view):
    dev = load(model)
    d = decor(dev, view)
    height = dev["chassis"]["height"]
    mirror = view == "right"

    def x_of(x):
        return 600 - x if mirror else x

    close([c for i in (1, 2) for c in centre(d[f"centre-plate-slot-{i}"])], [x_of(334.8), height - 147.5, x_of(281.3), height - 145.8])
    assert all(d[f"centre-plate-slot-{i}"]["size"] == [20.4, 8.5] for i in (1, 2)), "4 columns x 5.1, 2 rows x 4.267"
    close(centre(d["centre-plate-dot-1"]), [x_of(222.4), height - 151.3])
    assert d["centre-plate-dot-1"]["size"] == [13.1, 13.1]
    close(sorted(centre(d[f"page3-square-{w}-{i}"])[0] for w in ("head", "mid", "foot") for i in (1, 2)), sorted(x_of(x) for x in (275.2, 330.6) * 3))
    close([centre(d["page3-square-head-1"])[1], centre(d["page3-square-mid-1"])[1], centre(d["page3-square-foot-1"])[1]], [456.8, 1040.7, 2029.2])
    assert all(d[f"page3-square-{w}-{i}"]["size"] == [14.1, 14.1] for w in ("head", "mid", "foot") for i in (1, 2))
    triangle = d["page3-triangle"]
    assert triangle["size"] == [16.3, 11.9] and triangle["pattern"] == "motif" and triangle["pattern-pitch"] == [16.3, 11.9]
    assert triangle["pattern-cells"] == [[[8.2, 0], [16.3, 11.9], [0, 11.9]]]
    close(centre(triangle), [x_of(303.1), 414.5])
    close(centre(d["page3-dot"]), [x_of(229.3), 440.3])
    assert d["page3-dot"]["size"] == [7.4, 7.4], "5 pixels at 1.484 mm per pixel"


@pytest.mark.parametrize("view", ["left", "right"])
@pytest.mark.parametrize("model", MODELS)
def test_the_overlay_marks_the_side_plate_marks_and_the_replaced_holes_stand_where_the_pictures_put_them(model, view):
    dev = load(model)
    d = decor(dev, view)
    mirror = view == "right"

    def x_of(x):
        return 600 - x if mirror else x

    heads = [366.9, 315.0, 266.3, 209.0]
    if view == "left":
        close([centre(d[f"centre-plate-hole-top-{i}"])[0] for i in (1, 2, 3, 4)], heads)
    close([centre(d[f"centre-plate-hole-bottom-{i}"])[0] for i in (1, 2, 3, 4)], [x_of(x) for x in (372.2, 313.4, 262.5, 206.4)])
    close([c for n in ("row2-1", "row3-1", "row3-2") for c in centre(d[f"centre-plate-hole-{n}"])],
          [c for x, y in ((356.2, 199.4), (356.3, 860.7), (224.7, 862.7)) for c in (x_of(x), y)])
    marks = [(336.4, 201.2), (280.7, 201.0), (244.5, 200.2), (222.3, 201.0), (336.5, 862.3), (244.3, 861.3), (244.0, 1983.3), (306.3, 1979.5), (359.5, 1984.2)]
    close([c for i, (x, y) in enumerate(marks, 1) for c in centre(d[f"centre-plate-mark-{i}"])], [c for x, y in marks for c in (x_of(x), y)])
    assert all(d[f"centre-plate-mark-{i}"]["size"] == [7.7, 7.7] for i in range(1, 10))
    assert all(d[f"centre-plate-hole-{n}"]["size"] == [13.1, 13.1] for n in ("row2-1", "row3-1", "row3-2"))
    dots = [(153.9, 480.2), (148.8, 504.9), (117.9, 518.3), (173.5, 515.1), (54.0, 1896.7), (109.6, 1912.4), (246.6, 219.1)]
    close([c for i, (x, y) in enumerate(dots, 3) for c in centre(d[f"side-plate-dot-{i}"])], [c for x, y in dots for c in (x_of(x), y)])
    assert all(d[f"side-plate-dot-{i}"]["size"] == [5, 5] for i in range(1, 10))
    assert all(d[f"side-plate-hole-{i}"]["size"] == [7.9, 7.9] for i in (1, 2, 3))


@pytest.mark.parametrize("model", MODELS)
def test_every_new_item_is_estimated_and_front_and_rear_are_unchanged(model):
    dev = load(model)
    kinds = {"end-cap", "foot", "base-plate", "hole", "slot", "centre-plate", "rail", "cross-tube", "beam", "mounting-hole", "screw", "mark"}
    for view in ("top", "bottom", "left", "right"):
        new = [v for v in decor(dev, view).values() if v["kind"] in kinds]
        assert new and all(v["confidence"] == "estimated" for v in new)
    for view in ("front", "rear"):
        assert "decor" not in dev["views"][view].get("panel", {})


@pytest.mark.parametrize("model", MODELS)
def test_gaps_say_what_is_left_and_no_stale_gap_remains(model):
    gaps = {g["what"]: g for g in load(model)["gaps"]}
    for gone in ("end-caps", "feet", "side-plate-holes", "centre-plate"):
        assert gone not in gaps
    assert gaps["end-fittings-front"]["scope"] == ["front", "rear"]
    assert gaps["track-rungs"]["scope"] == ["left", "right"], "the render shows the rungs in the side channel"
    rungs = " ".join(gaps["track-rungs"]["note"].split())
    assert "The left and right faces draw the guides but not the rungs." in rungs
    assert "The door plates hide the track in the front and rear elevations." in rungs
    assert "door-hinge-tabs" in gaps and "door-hook" in gaps and "mid-panel" in gaps
    assert all(g["reason"] == "vendor-silent" for g in gaps.values())
    assert "which a following change draws, so they are not drawn here" not in gaps["track-rungs"]["note"]


@pytest.mark.parametrize("model", MODELS)
def test_the_frame_note_states_its_scales_and_method(model):
    note = " ".join(load(model)["provenance"]["frame"]["note"].split())
    for text in ("Ten scales are used, each in the direction it was read", "2.624 mm per pixel", "2.679 mm per pixel", "12 in reading", "every width", "stand-in",
                 "10.3 mm per pixel", "4.4 mm per pixel", "5.1 mm per pixel", "3.7 mm per pixel", "4.267 mm per pixel", "0.744 mm per pixel",
                 "2.357 mm per column and 1.374 mm per row", "cross tube", "three feet and the photograph two", "inferred",
                 "28 columns and 8 rows", "22 columns and 5 rows", "3 rows, so 7.9", "70.5 wide", "44 percent", "by three readings",
                 "four pale marks", "7 pixels wide, 31 mm", "so 13.1 across at 5.1 mm per pixel", "so 15.3 across", "so 20.4 by 8.5",
                 "three pairs of squares, a triangle and a dot", "base rail of 44 pixels, 32.8", "rounded lower corners of 17.5 pixels, 13",
                 "overlay of the render", "four marks near 505 mm", "beyond the 600 mm depth"):
        assert text in note, text
    assert "four feet" not in note and "cross tube at the front" not in note and "one method" not in note
    assert load(model)["provenance"]["frame"]["confidence"] == "estimated"


@pytest.mark.parametrize("model", MODELS)
def test_no_note_still_says_the_centre_is_open_where_the_plate_is_drawn(model):
    notes = load(model)["provenance"]
    spine = " ".join(notes["spine"]["note"].split())
    assert "none is fitted" not in spine and "centre is open" not in spine
    assert "That kit is a separate part and is not drawn." in spine
    assert "The flat centre plate of the page 3 render is drawn between the channels" in spine
    assert "with its holes and slots, in the side views." in spine
    side = " ".join(notes["left"]["note"].split())
    assert "across the centre" not in side
    assert "The flat centre plate of the page 3 render stands between the channels." in side
    for new in ("That kit is a separate part and is not drawn.", "The flat centre plate of the page 3 render stands between the channels."):
        assert len(new.split()) <= LIMIT
    assert len("The flat centre plate of the page 3 render is drawn between the channels, with its holes and slots, in the side views.".split()) <= LIMIT


@pytest.mark.parametrize("model", MODELS)
def test_no_added_sentence_is_over_25_words_and_no_banned_phrase(model):
    dev = load(model)
    texts = [dev["provenance"]["frame"]["note"]] + [g["note"] for g in dev["gaps"] if g["what"] in ("end-fittings-front", "track-rungs")]
    banned = [" ".join(w) for w in (("shared", "frame"), ("frame", "for", "the", "family"))] + ["twen" + "ty"]
    for text in texts:
        flat = " ".join(text.split())
        for s in re.split(r"(?<=[.?!])\s+", flat):
            assert len(s.split()) <= LIMIT, s
        assert not any(p in flat.lower() for p in banned)
