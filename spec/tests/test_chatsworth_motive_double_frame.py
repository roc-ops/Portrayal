"""The frame fittings of the Chatsworth Motive double-sided managers.

The data sheet's page 1 photograph shows caps on the top and feet on a base plate.
Its page 3 render shows four caps, three feet, a flat plate between the two channels, a cross tube and a pale rear beam.
The installation plan adds squares, a slot and screws on the centre section.
Each device draws them on the top, bottom, left and right faces.
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
    for h in holes:
        assert h["size"][0] == h["size"][1] == 8 and h["rx"] == 4
        assert 0 < h["at"][1] < depth


@pytest.mark.parametrize("view", ["left", "right"])
@pytest.mark.parametrize("model", MODELS)
def test_sides_draw_caps_feet_rim_centre_plate_and_holes(model, view):
    dev = load(model)
    d = decor(dev, view)
    height, depth = dev["chassis"]["height"], dev["chassis"]["depth"]
    assert [len(of_kind(d, k)) for k in ("end-cap", "foot", "base-plate", "centre-plate")] == [2, 2, 1, 1]
    assert all(v["size"] == [37.5, 21] and v["at"][1] == 0 for v in of_kind(d, "end-cap"))
    assert all(v["size"] == [29.5, 13.1] and abs(v["at"][1] + 13.1 - height) < 1e-6 for v in of_kind(d, "foot"))
    plate = d["centre-plate"]
    assert plate["at"][0] == 201 and plate["size"][0] == 198
    if view == "left":
        assert len(of_kind(d, "hole")) == 4 + 4 + 3 + 2 and len(of_kind(d, "slot")) == 2
    else:
        assert len(of_kind(d, "hole")) == 3 + 4 + 3 + 2 and len(of_kind(d, "slot")) == 2 + 2
    assert len(of_kind(d, "mounting-hole")) == 5 and len(of_kind(d, "screw")) == 4
    ids = {v["id"] for v in d.values()}
    assert {"end-cap-rear", "end-cap-front", "foot-rear", "foot-front"} <= ids
    rear_cap, front_cap = d["end-cap-rear"], d["end-cap-front"]
    if view == "left":
        assert rear_cap["at"][0] < front_cap["at"][0]
    else:
        assert rear_cap["at"][0] > front_cap["at"][0], "the rear end is on the right in the right view"
    assert 0 <= min(v["at"][0] for v in d.values() if v["kind"] in ("hole", "end-cap", "foot"))
    assert max(v["at"][0] + v["size"][0] for v in d.values() if v["kind"] in ("hole", "end-cap", "foot")) <= depth


FRAME_KINDS = {"end-cap", "foot", "base-plate", "hole", "slot", "centre-plate", "rail", "cross-tube", "beam", "mounting-hole", "screw"}


@pytest.mark.parametrize("model", MODELS)
def test_each_view_carries_the_counted_number_of_frame_items(model):
    dev = load(model)
    counts = {view: len([v for v in decor(dev, view).values() if v["kind"] in FRAME_KINDS]) for view in ("top", "bottom", "left", "right")}
    assert counts == {"top": 8, "bottom": 11, "left": 30, "right": 31}
    assert sum(counts.values()) == 80


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
    close([centre(d["plan-square-1"])[1]], [height - 8 - 122.4])
    close(sorted(centre(d[f"plan-screw-{i}"])[0] for i in (1, 2, 3, 4)), sorted(x_of(x) for x in (217.4, 275.4, 325.3, 382.6)))
    assert all(d[f"plan-screw-{i}"]["size"] == [14.9, 14.9] and "fill" not in d[f"plan-screw-{i}"] for i in (1, 2, 3, 4))


@pytest.mark.parametrize("model", MODELS)
def test_the_right_face_draws_the_far_plates_head_pattern_not_the_near_plates(model):
    d = decor(load(model), "right")
    assert [k for k in d if k.startswith("centre-plate-hole-top-")] == [f"centre-plate-hole-top-{i}" for i in (1, 2, 3)]
    close([c for i in (1, 2, 3) for c in centre(d[f"centre-plate-hole-top-{i}"])], [218.3, 47.9, 267.3, 111.9, 309.6, 134.4])
    close([c for i in (1, 2) for c in centre(d[f"centre-plate-slot-head-{i}"])], [264.8, 130.8, 331.6, 133.2])
    left = decor(load(model), "left")
    assert not any(k.startswith("centre-plate-slot-head-") for k in left)
    assert "centre-plate-hole-top-4" in left and "centre-plate-hole-top-4" not in d


@pytest.mark.parametrize("model", MODELS)
def test_every_new_item_is_estimated_and_front_and_rear_are_unchanged(model):
    dev = load(model)
    kinds = {"end-cap", "foot", "base-plate", "hole", "slot", "centre-plate", "rail", "cross-tube", "beam", "mounting-hole", "screw"}
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
    assert gaps["track-rungs"]["scope"] == ["front", "rear"]
    assert "door-hinge-tabs" in gaps and "door-hook" in gaps and "mid-panel" in gaps
    assert all(g["reason"] == "vendor-silent" for g in gaps.values())
    assert "which a following change draws, so they are not drawn here" not in gaps["track-rungs"]["note"]


@pytest.mark.parametrize("model", MODELS)
def test_the_frame_note_states_its_scales_and_method(model):
    note = " ".join(load(model)["provenance"]["frame"]["note"].split())
    for text in ("2.624 mm per pixel", "2.679 mm per pixel", "12 in reading", "every width", "stand-in", "10.3 mm per pixel", "4.4 mm per pixel", "cross tube",
                 "three feet and the photograph two", "inferred", "28 columns and 8 rows", "22 columns and 5 rows", "3.7 mm per pixel",
                 "44 percent", "0.744 mm per pixel", "four pale marks"):
        assert text in note, text
    assert "four feet" not in note and "cross tube at the front" not in note
    assert load(model)["provenance"]["frame"]["confidence"] == "estimated"


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
