"""The shapes of the FS-PDUBK bracket that its product page's photographs show (#939).

The photographs show more than the keyholes and the square holes. The far end of the plate turns back
into a lip. Three gussets join the plate to the foot. Two slots run across the foot, each with a small
tail toward the plate. The foot's free corners are rounded. The bracket is drawn 30 across the foot and
5 more for the lip, so 35 across the rack's face. Every figure is an estimate read off the photographs.
The tests state what is drawn and where, to the accuracy the reading gives. They read the BUILT drawing
(library/dist), in both mounting options.
"""
import re
from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parents[2] / "library" / "dist"
CONFIGS = ["front", "rear"]
PITCH = 31.5
TOL = 0.6


def view(cfg, name):
    return (DIST / f"fs-pdubk.{cfg}.{name}.svg").read_text()


def width(svg):
    return float(re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).group(1))


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
@pytest.mark.parametrize("name", ["front", "rear", "top", "bottom"])
def test_the_four_end_views_are_35_across_for_the_lip(cfg, name):
    assert width(view(cfg, name)) == 35.0


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
@pytest.mark.parametrize("name", ["front", "rear"])
def test_the_lip_is_a_5_mm_strip_in_the_end_views(cfg, name):
    svg = view(cfg, name)
    m = re.search(r'<rect id="lip"[^>]* x="([\d.]+)" y="0" width="([\d.]+)" height="88.4"', svg)
    assert m, f"no lip strip in the {cfg} {name} view"
    assert float(m.group(2)) == 5.0
    # the lip is on the side away from the foot: the right of the front view, the left of the rear view
    assert float(m.group(1)) == (30.0 if name == "front" else 0.0)


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
@pytest.mark.parametrize("name", ["top", "bottom"])
def test_the_lip_stands_at_the_far_end_of_the_plate_in_plan(cfg, name):
    svg = view(cfg, name)
    ids = re.findall(r'<g id="(lip-(?:front|rear))"[^>]*transform="translate\(([\d.]+),([\d.]+)\)"', svg)
    assert len(ids) == 1, f"one lip in the {cfg} {name} view, found {ids}"
    # the foot is at the top of the plan in option 1 (front) and at the bottom in option 2 (rear)
    far = 133.0 if cfg == "front" else 0.0
    assert float(ids[0][2]) == far
    # and the lip is on the side away from the foot: the right in the top view, the left in the bottom view
    assert float(ids[0][1]) == (30.0 if name == "top" else 0.0)


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
@pytest.mark.parametrize("name", ["top", "bottom"])
def test_one_gusset_is_seen_in_plan_at_the_foot(cfg, name):
    svg = view(cfg, name)
    assert len(re.findall(r'<path id="gusset-(?:front|rear)--gusset"', svg)) == 1


def centres(svg, pattern):
    out = []
    for m in re.finditer(pattern, svg):
        out.append(m)
    return out


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
def test_three_gussets_stand_on_the_foot_at_the_keyhole_pitch(cfg):
    name = "front" if cfg == "front" else "rear"
    svg = view(cfg, name)
    paths = re.findall(r'<path id="foot-(?:front|rear)--gusset-\d" [^>]*d="M ([\d.]+) ([\d.]+) L [\d.]+ [\d.]+ V [\d.]+ L [\d.]+ ([\d.]+) Z"', svg)
    assert len(paths) == 3, f"three gussets on the foot in the {cfg} {name} view"
    ys = sorted((float(a) + float(b)) / 2 for _, a, b in paths)
    for a, b in zip(ys, ys[1:]):
        assert abs(b - a - PITCH) <= TOL
    assert abs(ys[1] - 88.4 / 2) <= TOL, "the middle one is at the middle of the 88.4"


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
def test_three_gussets_stand_on_the_plate_at_the_foots_end(cfg):
    svg = view(cfg, "left")
    rects = re.findall(r'<rect id="plate-(?:front|rear)--gusset-\d"[^>]* x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    assert len(rects) == 3
    ys = sorted(float(y) + float(h) / 2 for _, y, _, h in rects)
    for a, b in zip(ys, ys[1:]):
        assert abs(b - a - PITCH) <= TOL
    # the foot is at the left end in option 1 and at the right end in option 2
    for x, _, w, _ in rects:
        if cfg == "front":
            assert float(x) < 10
        else:
            assert float(x) + float(w) > 125


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
def test_the_far_side_of_the_plate_shows_the_end_of_the_lip(cfg):
    svg = view(cfg, "right")
    m = re.search(r'<rect id="plate-face-(?:front|rear)--lip"[^>]* x="([\d.]+)" y="0" width="2" height="88.4"', svg)
    assert m
    # seen from the other side the foot swaps ends, so the lip is at the left in option 1 and the right in option 2
    assert (float(m.group(1)) < 10) == (cfg == "front")


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
def test_the_two_outer_foot_holes_are_slots_with_a_tail(cfg):
    name = "front" if cfg == "front" else "rear"
    svg = view(cfg, name)
    d = re.search(r'<path id="foot-(?:front|rear)--(?:floor|face)"[^>]* d="([^"]+)"', svg).group(1)
    subs = re.split(r"(?=M )", d)[1:]
    assert len(subs) == 5, "the sheet and four holes"
    slots = [s for s in subs[1:] if " L " in s]
    rounds = [s for s in subs[1:] if " L " not in s]
    assert len(slots) == 2 and len(rounds) == 2
    for s in slots:
        # the slot runs across the foot: it starts on a horizontal line, not a vertical one
        assert re.match(r"M [\d.]+ [\d.]+ H ", s.strip()), s
