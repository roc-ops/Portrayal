"""The Tripp Lite series PDU3MV6L2130A, a 0U three-phase metered rack PDU.

What is true of the strip and of the three parts only it places. The 45 outlets stand in three
sections on the pitch the maker's drawing gives. Each section runs through its own two-pole
breaker. The fixed cord exports the power port its plug is. The three meter rows are one part.
Every figure is read from the build in `library/dist`, and from the export written from it.
Run `./build.sh` first.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal.artifacts import Dist

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
NAME = "pdu3mv6l2130a"
FACES = ["front", "rear", "top", "bottom", "left", "right"]
NEW_PARTS = ["eaton/tripplite-cord-l21-30p@1", "eaton/tripplite-phase-meter@1", "eaton/tripplite-breaker-20a-2p@1"]
LINES = {1: "L1-L2", 2: "L2-L3", 3: "L3-L1"}


def elements(face):
    path = DIST / f"{NAME}.{face}.elements.json"
    assert path.exists(), "run ./build.sh first: this reads library/dist"
    return json.loads(path.read_text())["elements"]


def by_id(face):
    return {e["id"]: e for e in elements(face) if "id" in e}


def outlets():
    found = by_id("front")
    return [found[f"outlet-{n}"] for n in range(1, 46)]


def decor(face):
    """The decor rectangles of a built face: id -> (x, y, w, h)."""
    svg = (DIST / f"{NAME}.{face}.svg").read_text()
    pat = r'<rect id="([^"]+)"[^>]* x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"'
    return {m[0]: tuple(float(v) for v in m[1:]) for m in re.findall(pat, svg)}


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    """The device exported from the build, as publish.sh does it, without pictures."""
    out = tmp_path_factory.mktemp("dcim")
    dx.export_device(Dist(str(DIST)), NAME, out, None)
    return out


@pytest.mark.heavy
def test_every_face_is_built_and_the_body_is_the_drawings_56_by_1776_44():
    for face in FACES:
        chassis = by_id(face)["chassis-faceplate"]["box"]
        want = {"front": (56, 1776.44), "rear": (56, 1776.44), "left": (42.78, 1776.44),
                "right": (42.78, 1776.44), "top": (56, 42.78), "bottom": (56, 42.78)}[face]
        assert (chassis["w"], chassis["h"]) == want, face
    manifest = Dist(str(DIST)).manifest(NAME)
    assert manifest["chassis"]["mount"] == "rack-side"


def round_decor(face):
    """The round decor of a built face: id -> (kind, x, y, w, h, rx)."""
    svg = (DIST / f"{NAME}.{face}.svg").read_text()
    pat = r'<rect id="([^"]+)" data-kind="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="([\d.]+)"'
    return {m[0]: (m[1], *(float(v) for v in m[2:])) for m in re.findall(pat, svg)}


# The drawing's side view shows eight round marks inside its 42.78 deep body. Two are at the top end and six are on
# a column near the front edge. Read from the vector page: the ring is 6.2 across and the inner ring 3.4. The six sit
# 312.22 apart. The side view's own end lines are 572.45 points apart for 1776.44, so its scale is 3.103 per point.
# A right face has x = 0 at the front. The left face is its mirror, 42.78 minus x.
SIDE_MARK_Y = [6.21, 13.98, 202.64, 514.86, 827.07, 1139.29, 1451.50, 1763.72]
SIDE_MARK_X = {"right": [13.46] + [4.75] * 7, "left": [29.32] + [38.03] * 7}


@pytest.mark.heavy
@pytest.mark.parametrize("face", ["right", "left"])
def test_each_side_draws_the_eight_round_marks_of_the_drawings_side_view(face):
    found = round_decor(face)
    rings = [v for n, v in found.items() if n.startswith("side-mark-") and not n.endswith("-ring")]
    inner = [v for n, v in found.items() if n.startswith("side-mark-") and n.endswith("-ring")]
    assert len(rings) == 8 and len(inner) == 8, "eight marks, each a ring and an inner ring"
    assert len(found) == 16, "nothing else is drawn on the side"
    for group in (rings, inner):
        size = 6.2 if group is rings else 3.4
        assert all(abs(w - size) < 0.05 and abs(h - size) < 0.05 and abs(rx - size / 2) < 0.05
                   for _, _, _, w, h, rx in group), "round, and as wide as the drawing's ring"
    centres = sorted((y + h / 2, x + w / 2) for _, x, y, w, h, _ in rings)
    inner_centres = sorted((y + h / 2, x + w / 2) for _, x, y, w, h, _ in inner)
    for (cy, cx), (iy, ix), want_y, want_x in zip(centres, inner_centres, SIDE_MARK_Y, SIDE_MARK_X[face]):
        assert abs(cy - want_y) < 0.1 and abs(cx - want_x) < 0.1, (face, cy, cx, want_y, want_x)
        assert abs(iy - cy) < 0.05 and abs(ix - cx) < 0.05, "the inner ring is concentric"
    assert [c[0] < 20 for c in centres] == [True] * 2 + [False] * 6, "two at the top end and six on the column"
    column = [c[0] for c in centres[2:]]
    assert len({round(c[1], 2) for c in centres[1:]}) == 1, "the column and the lower top-end mark share an x"
    assert all(abs((b - a) - 312.22) < 0.1 for a, b in zip(column, column[1:])), "the column's pitch"
    assert all(0 <= x and x + w <= 42.78 and 0 <= y and y + h <= 1776.44 for _, x, y, w, h, _ in rings), "inside the body"


@pytest.mark.heavy
@pytest.mark.parametrize("face", ["top", "bottom"])
def test_the_top_and_bottom_carry_only_the_body_as_decor(face):
    assert list(decor(face)) == ["chassis-faceplate"], face
    if face == "top":
        assert [e["class"] for e in elements(face)] == ["chassis"]


@pytest.mark.heavy
def test_45_outlets_are_36_c13_and_9_c19_in_three_sections_of_fifteen():
    rows = outlets()
    refs = [e["ref"].split(":")[0] for e in rows]
    assert refs.count("std/c13-outlet@1") == 36 and refs.count("std/c19-outlet@1") == 9
    for section in range(3):
        kinds = refs[section * 15:(section + 1) * 15]
        assert kinds == ["std/c19-outlet@1"] * 3 + ["std/c13-outlet@1"] * 12, section


@pytest.mark.heavy
def test_the_c19s_stand_at_the_drawn_pitch_and_the_c13_rows_at_theirs():
    rows = outlets()
    c19 = [e["box"]["y"] for e in rows[:3]]
    assert all(round(b - a, 1) == 34.5 for a, b in zip(c19, c19[1:])), "C19 pitch read off the drawing"
    c13 = sorted({e["box"]["y"] for e in rows[3:15]})
    assert len(c13) == 6
    assert all(round(b - a, 1) == 35.5 for a, b in zip(c13, c13[1:])), "C13 row pitch read off the drawing"
    first = [rows[i]["box"]["y"] for i in (0, 15, 30)]
    assert round(first[1] - first[0], 1) == 438.3 and round(first[2] - first[1], 1) == 529.8


@pytest.mark.heavy
def test_the_three_meter_rows_are_one_part_between_the_second_and_third_sections():
    front = by_id("front")
    meter = front["meter"]
    assert meter["ref"].split(":")[0] == "eaton/tripplite-phase-meter@1"
    rows = [e for e in elements("front") if e.get("parent") == "meter" and e["class"] == "display"]
    assert len(rows) == 3
    ys = [e["box"]["y"] for e in outlets()]
    assert ys[29] < meter["box"]["y"] < ys[30], "between the second section's last outlet and the third's first"


@pytest.mark.heavy
def test_three_breakers_stand_at_the_drawn_places():
    front = by_id("front")
    breakers = [front[f"breaker-{n}"] for n in (1, 2, 3)]
    assert {b["ref"].split(":")[0] for b in breakers} == {"eaton/tripplite-breaker-20a-2p@1"}
    ys = [b["box"]["y"] for b in breakers]
    assert [round(b - a, 1) for a, b in zip(ys, ys[1:])] == [67.8, 67.6]


@pytest.mark.heavy
def test_the_two_buttons_stand_1556_apart_on_the_rear():
    rear = by_id("rear")
    gap = rear["button-2"]["box"]["y"] - rear["button-1"]["box"]["y"]
    assert round(gap, 2) == 1556.0


@pytest.mark.heavy
def test_the_rear_draws_the_keyhole_plate_the_two_bracket_plates_and_four_seam_ticks():
    shapes = decor("rear")
    width, length = 56.0, 1776.44
    for name, (x, y, w, h) in shapes.items():
        assert 0 <= x and x + w <= width and 0 <= y and y + h <= length, f"{name} lies outside the rear face"
    button = by_id("rear")["button-1"]["box"]
    plate = shapes["keyhole-plate"]
    assert plate[1] < button["y"] + button["h"] / 2 < plate[1] + plate[3], "the keyhole plate holds the top button"
    assert not [n for n, s in shapes.items() if n.startswith("keyhole") and s[1] > 1000], "the lower button has none"
    for part in ("keyhole-slot", "keyhole-bulb"):
        x, y, w, h = shapes[part]
        assert plate[0] <= x and x + w <= plate[0] + plate[2] and plate[1] <= y and y + h <= plate[1] + plate[3], part
    assert sorted(round(shapes[n][1], 1) for n in shapes if n.startswith("seam-tick")) == [1398.5, 1398.5, 1453.4, 1453.4]
    assert len([n for n in shapes if n.startswith("bracket-plate")]) == 2
    assert len([n for n in shapes if n.startswith("bracket-hole")]) == 8
    assert len([n for n in shapes if n.startswith("rear-mark")]) == 2


@pytest.mark.heavy
def test_the_fixed_cord_stands_on_the_bottom_face_and_not_on_the_front():
    bottom = by_id("bottom")
    assert bottom["input"]["ref"].split(":")[0] == "eaton/tripplite-cord-l21-30p@1"
    assert bottom["input"]["class"] == "inlet"
    assert "input" not in by_id("front")


@pytest.mark.heavy
@pytest.mark.parametrize("ref", NEW_PARTS)
def test_each_new_part_is_in_the_built_catalogue_and_placed(ref):
    assert Dist(str(DIST)).component_by_ref(ref) is not None
    placed = {e["ref"].split(":")[0] for face in FACES for e in elements(face) if "ref" in e}
    assert ref in placed


@pytest.mark.heavy
@pytest.mark.parametrize("tree", dx.TARGETS)
def test_the_export_has_one_l21_30p_port_and_45_outlets_fed_by_it(exported, tree):
    doc = yaml.safe_load((exported / tree / "device-types" / "Eaton" / "PDU3MV6L2130A.yaml").read_text())
    assert [(p["name"], p["type"]) for p in doc["power-ports"]] == [("input", "nema-l21-30p")]
    outs = doc["power-outlets"]
    assert len(outs) == 45 and {o["power_port"] for o in outs} == {"input"}
    types = [o["type"] for o in outs]
    assert types.count("iec-60320-c13") == 36 and types.count("iec-60320-c19") == 9


@pytest.mark.heavy
@pytest.mark.parametrize("tree", dx.TARGETS)
def test_each_section_goes_through_its_own_breaker_on_its_own_pair_of_lines(exported, tree):
    doc = yaml.safe_load((exported / tree / "device-types" / "Eaton" / "PDU3MV6L2130A.yaml").read_text())
    for n, outlet in enumerate(doc["power-outlets"], 1):
        section = (n - 1) // 15 + 1
        assert outlet["name"] == f"outlet-{n}"
        assert outlet["description"] == f"Through breaker-{section}, lines {LINES[section]}", outlet["name"]
