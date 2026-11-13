"""The shapes of the FS-PDUBK bracket that its product page's photographs show (#939).

The photographs show more than the keyholes and the square holes. Each long edge of the plate turns
back into a lip. Three gussets join the plate to the foot. Two slots run across the foot, each with a small
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
def test_the_two_lips_are_5_by_2_bars_in_the_end_views(cfg, name):
    svg = view(cfg, name)
    # the lips are on the side away from the foot: the right of the front view, the left of the rear view
    x = 30.0 if name == "front" else 0.0
    for lip, y in (("lip-top", 0.0), ("lip-bottom", 86.4)):
        m = re.search(rf'<rect id="{lip}"[^>]* x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
        assert m, f"no {lip} bar in the {cfg} {name} view"
        assert tuple(float(v) for v in m.groups()) == (x, y, 5.0, 2.0)


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
@pytest.mark.parametrize("name", ["top", "bottom"])
def test_a_lip_runs_the_whole_length_of_the_plate_in_plan(cfg, name):
    svg = view(cfg, name)
    ids = re.findall(r'<g id="lip"[^>]*transform="translate\(([\d.]+),([\d.]+)\)"', svg)
    assert len(ids) == 1, f"one lip in the {cfg} {name} view, found {ids}"
    # the lip is on the side away from the foot: the right in the top view, the left in the bottom view
    assert (float(ids[0][0]), float(ids[0][1])) == ((30.0 if name == "top" else 0.0), 0.0)
    m = re.search(r'<rect id="lip--lip"[^>]* width="([\d.]+)" height="([\d.]+)"', svg)
    assert m and (float(m.group(1)), float(m.group(2))) == (5.0, 135.0)


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
    paths = re.findall(r'<path id="foot-(?:front|rear)--gusset-\d" [^>]*d="M ([\d.]+) ([\d.]+) L ([\d.]+) ([\d.]+) V ([\d.]+) L [\d.]+ ([\d.]+) Z"', svg)
    assert len(paths) == 3, f"three gussets on the foot in the {cfg} {name} view"
    ys = sorted((float(p[1]) + float(p[5])) / 2 for p in paths)
    for a, b in zip(ys, ys[1:]):
        assert abs(b - a - PITCH) <= TOL
    assert abs(ys[1] - 88.4 / 2) <= TOL, "the middle one is at the middle of the 88.4"
    for p in paths:
        # 6.5 thick at the plate and 3.5 at the tip, 15 long: measured on the dimensioned render
        assert round(float(p[5]) - float(p[1]), 2) == 6.5
        assert round(float(p[4]) - float(p[3]), 2) == 3.5
        assert round(float(p[0]) - float(p[2]), 2) == 15.0


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
def test_three_gussets_stand_on_the_plate_at_the_foots_end(cfg):
    svg = view(cfg, "left")
    paths = re.findall(r'<path id="plate-(?:front|rear)--gusset-\d"[^>]* d="M ([\d.]+) ([\d.]+) L ([\d.]+) ([\d.]+) V ([\d.]+) L [\d.]+ ([\d.]+) Z"', svg)
    assert len(paths) == 3
    ys = sorted((float(p[1]) + float(p[5])) / 2 for p in paths)
    for a, b in zip(ys, ys[1:]):
        assert abs(b - a - PITCH) <= TOL
    for p in paths:
        # 6.5 thick at the foot's end and 3.5 at the tip, 6 along the plate: measured on the dimensioned render
        assert round(float(p[5]) - float(p[1]), 2) == 6.5
        assert round(float(p[4]) - float(p[3]), 2) == 3.5
        assert round(abs(float(p[0]) - float(p[2])), 2) == 6.0
        # the foot is at the left end in option 1 and at the right end in option 2
        assert float(p[0]) == (2.0 if cfg == "front" else 133.0)


@pytest.mark.heavy
@pytest.mark.parametrize("cfg", CONFIGS)
def test_the_far_side_of_the_plate_shows_both_lips_along_its_edges(cfg):
    svg = view(cfg, "right")
    for lip, y in (("lip-top", 0.0), ("lip-bottom", 86.4)):
        m = re.search(rf'<rect id="plate-face-(?:front|rear)--{lip}"[^>]* x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
        assert m, f"no {lip} along the edge in the {cfg} right view"
        assert tuple(float(v) for v in m.groups()) == (0.0, y, 135.0, 2.0)


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


def test_the_lip_end_tabs_are_a_named_gap_with_a_reason():
    import yaml

    path = Path(__file__).resolve().parents[2] / "library" / "devices" / "fs" / "fs-pdubk" / "device.yaml"
    gaps = {g["what"]: g for g in yaml.safe_load(path.read_text())["gaps"]}
    assert "lip-end-tabs" in gaps
    assert gaps["lip-end-tabs"]["reason"] == "needs-drawing"
    assert gaps["lip-end-tabs"]["scope"] == ["left", "right", "top", "bottom"]
    note = " ".join(gaps["lip-end-tabs"]["note"].split())
    # the measured facts at each picture's own scale, the source of the 135,
    # the probe's result and the level check's lines
    for words in (
        "3.2 to 3.5 mm",
        "2.4 to 2.7 mm",
        "flush at 135",
        "On x6 it reads 20 to 21 px at 6.04 to 6.18 px per mm",
        "On g5 it reads 21 to 22 px at 6.52 to 6.56 px per mm",
        '5.3" (135mm)',
        "The quick start guide prints no dimension",
        "all read 139",
        "working tree level 4 addressable",
        "level 4 to level 2",
        "chassis depth disagrees",
        "left.w=138, right.w=138, top.h=138, bottom.h=138, chassis.depth=135",
        "an inconsistent box must not reach solid",
        "asked for a major version beyond 1.0.0 for the depth and view change alone",
        "and no id was lost",
        "gives 140",
    ):
        assert words in note, words
    assert "the guide prints it" not in note
    assert "may read 139" in gaps["lip-end-tabs"]["wanted"]
