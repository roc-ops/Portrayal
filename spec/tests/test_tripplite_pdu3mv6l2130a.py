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


def gaps():
    """The device's gaps as the build carries them: what -> the gap."""
    source = json.loads((DIST / f"{NAME}.source.json").read_text())
    return {g["what"]: g for g in source["gaps"]}


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


def stacks(face, tol=0.06):
    """The square decor of a built face grouped by centre: a list of [centre x, centre y, widths widest first]."""
    out = []
    for _, x, y, w, h, _ in sorted(round_decor(face).values(), key=lambda s: -s[3]):
        if abs(w - h) > 0.01:
            continue
        cx, cy = x + w / 2, y + h / 2
        for s in out:
            if abs(s[0] - cx) < tol and abs(s[1] - cy) < tol:
                s[2].append(w)
                break
        else:
            out.append([cx, cy, [w]])
    return out


def count_stacks(found, want, tol=0.06):
    """How many stacks have exactly these ring widths, each within tol."""
    return sum(1 for _, _, ws in found if len(ws) == len(want) and all(abs(a - b) < tol for a, b in zip(ws, want)))


# The drawing's side view shows eight round marks inside its 42.78 deep body. Two are at the top end and six are on
# a column near the front edge. Read from the vector page: each mark is four concentric circles, 6.21, 3.38, about 3.1
# and 2.55 across. The top one has three, without the 2.55. Marks 3 and 6 carry a slot 2.55 long. The six sit 312.22 apart.
# The side view's own end lines are 572.45 points apart for 1776.44, so its scale is 3.103 per point. The front wall is the
# line at x 200.46 pt; the marks stand 3.94 mm from it (the top one 12.69 mm). A right face has x = 0 at the front. The left face
# is its mirror, 42.78 minus x.
SIDE_MARK_Y = [6.21, 13.98, 202.64, 514.86, 827.07, 1139.29, 1451.50, 1763.72]
FRONT_EDGE_MM = [12.69] + [3.94] * 7
MARK_RINGS = [[6.2, 3.4, 3.1]] + [[6.2, 3.4, 3.1, 2.55]] * 7
# The plate in the side view (x 185.08 to 198.64 pt, y 112.61 to 131.63 pt) is 42.08 by 59.02 mm. It starts 4.96 mm behind the back
# line and ends 37.12 mm in. Its screw cluster is five concentric circles, 23.55 mm from the back line and 118.10 mm from the top
# end. A cross 4.8 mm long and 1.0 mm wide sits in them.
PLATE = {"w": 42.08, "h": 59.02, "y": 88.55, "back": -4.96, "front_gap": 5.66}
PLATE_RINGS = [25.4, 17.5, 9.3, 8.75, 7.9]
PLATE_CLUSTER = (23.55, 118.10)


@pytest.mark.heavy
@pytest.mark.parametrize("face", ["right", "left"])
def test_each_side_draws_the_eight_marks_with_their_circles_and_the_plate_with_its_screw_cluster(face):
    found = stacks(face)
    flat = decor(face)
    mirror = (lambda x: x) if face == "right" else (lambda x: 42.78 - x)
    for n, (cy, edge, rings) in enumerate(zip(SIDE_MARK_Y, FRONT_EDGE_MM, MARK_RINGS), 1):
        cx = mirror(edge)
        here = [ws for sx, sy, ws in found if abs(sx - cx) < 0.06 and abs(sy - cy) < 0.06]
        assert len(here) == 1 and len(here[0]) == len(rings) and all(abs(a - b) < 0.06 for a, b in zip(here[0], rings)), (face, n, here)
    slots = sorted(round(y + h / 2, 2) for x, y, w, h in flat.values() if (round(w, 2), round(h, 2)) == (2.55, 0.9))
    assert slots == [202.64, 1139.29], "a slot on marks 3 and 6 only"
    column = sorted(cy for _, cy, ws in found if abs(ws[0] - 6.2) < 0.06 and cy > 100)
    assert len(column) == 6 and all(abs((b - a) - 312.22) < 0.1 for a, b in zip(column, column[1:])), "the column's pitch"
    cx_cluster = PLATE_CLUSTER[0] if face == "left" else 42.78 - PLATE_CLUSTER[0]
    cluster = [ws for sx, sy, ws in found if abs(sx - cx_cluster) < 0.06 and abs(sy - PLATE_CLUSTER[1]) < 0.06]
    assert len(cluster) == 1 and len(cluster[0]) == 5 and all(abs(a - b) < 0.06 for a, b in zip(cluster[0], PLATE_RINGS)), (face, cluster)
    plates = [v for v in flat.values() if abs(v[2] - PLATE["w"]) < 0.06 and abs(v[3] - PLATE["h"]) < 0.06]
    assert len(plates) == 1 and abs(plates[0][1] - PLATE["y"]) < 0.06, "one plate, level with the keyhole plate on the rear"
    x, _, w, _ = plates[0]
    if face == "left":
        assert abs(x - PLATE["back"]) < 0.06 and abs(42.78 - (x + w) - PLATE["front_gap"]) < 0.06
    else:
        assert abs(x - PLATE["front_gap"]) < 0.06 and abs(x + w - (42.78 - PLATE["back"])) < 0.06
    cross = sorted((round(w, 2), round(h, 2)) for x, y, w, h in flat.values()
                   if abs(x + w / 2 - cx_cluster) < 0.06 and abs(y + h / 2 - PLATE_CLUSTER[1]) < 0.06 and min(w, h) < 1.5)
    assert cross == [(1.0, 4.8), (4.8, 1.0)], "the cross is two bars 4.8 by 1.0"
    assert len(flat) == 1 + 31 + 2 + 1 + 5 + 2, "the body, 31 mark circles, 2 slots, the plate, 5 circles and the cross"
    marks = [(cx, cy) for cx, cy, ws in found if abs(ws[0] - 6.2) < 0.06]
    assert all(0 <= x - 3.1 and x + 3.1 <= 42.78 and 0 <= y - 3.1 and y + 3.1 <= 1776.44 for x, y in marks), "inside the body"


@pytest.mark.heavy
def test_the_front_screws_and_holes_carry_the_drawings_inner_rings_and_the_seam_lines_cross_the_face():
    found = stacks("front")
    assert count_stacks(found, [3.95, 2.82]) == 12, "the twelve small holes"
    assert count_stacks(found, [4.2]) == 4, "four 4.2 holes, each in a hexagon drawn as silkscreen"
    assert count_stacks(found, [5.5, 4.2]) == 1, "the plain hole at the foot has its ring"
    assert count_stacks(found, [5.5, 3.54]) == 6, "the six middle screws are 5.5 across with a ring"
    assert count_stacks(found, [4.8, 3.67, 2.68]) == 12, "the other twelve screws have two inner rings"
    assert count_stacks(found, [4.9, 3.81, 3.52, 2.68]) == 2, "the two plate screws"
    seams = sorted((round(y + h / 2, 1), round(w, 1)) for k, (x, y, w, h) in decor("front").items() if k.startswith("seam-line"))
    assert seams == [(1397.8, 54.9), (1410.5, 56.0), (1410.9, 54.9)], "the seam lines of the breaker end"


@pytest.mark.heavy
def test_the_rear_marks_and_holes_carry_their_rings_and_the_bracket_plates_run_to_the_right_edge():
    found = stacks("rear")
    assert count_stacks(found, [5.5, 3.53]) == 2, "the two marks"
    assert count_stacks(found, [4.5, 3.94, 3.24]) == 4 and count_stacks(found, [4.5]) == 4, "four holes with two rings, four plain"
    shapes = decor("rear")
    for n, top, tab in ((1, 280.7, 283.2), (2, 1525.4, 1527.8)):
        x, y, w, h = shapes[f"bracket-plate-{n}"]
        assert abs(x - 2.55) < 0.06 and abs(x + w - 56.0) < 0.06 and abs(y - top) < 0.06 and abs(h - 47.0) < 0.06, (n, x, y, w, h)
        tx, ty, tw, th = shapes[f"bracket-tab-{n}"]
        assert abs(tx) < 0.06 and abs(tw - 1.7) < 0.06 and abs(th - 42.2) < 0.06 and abs(ty - tab) < 0.06, (n, tx, ty, tw, th)


# The rear view's bracket holes and its two round marks, read from the vector page against the bracket plates already built.
# A hole stands 2.27 mm below its plate's top edge on the page, and the four holes stand 12.7 mm apart. The marks are measured
# from the lower plate's top edge, 576.38 pt on the page. The rear view's scale is 3.10697 mm per point, from its own end lines.
REAR_HOLE_TOPS = [282.95, 295.65, 308.35, 321.05, 1527.65, 1540.35, 1553.05, 1565.75]
REAR_MARK_TOPS = [1390.4, 1747.35]


@pytest.mark.heavy
def test_the_rear_bracket_holes_and_marks_stand_where_the_page_puts_them():
    shapes = decor("rear")
    holes = [shapes[f"bracket-hole-{n}"][1] for n in range(1, 9)]
    assert all(abs(a - b) < 0.06 for a, b in zip(holes, REAR_HOLE_TOPS)), holes
    marks = [shapes[f"rear-mark-{n}"][1] for n in (1, 2)]
    assert all(abs(a - b) < 0.06 for a, b in zip(marks, REAR_MARK_TOPS)), marks
    for n, plate in ((1, "bracket-plate-1"), (5, "bracket-plate-2")):
        top, height = shapes[plate][1], shapes[plate][3]
        inside = [shapes[f"bracket-hole-{k}"] for k in range(n, n + 4)]
        above = inside[0][1] - top
        below = top + height - (inside[-1][1] + inside[-1][3])
        assert abs(above - below) < 0.3, f"the four holes sit evenly in {plate}: {above:.2f} above, {below:.2f} below"


# The front view draws a hexagon round each of the four plain holes, 5.5 mm across its corners and 4.8 across its flats. The
# kit has no hexagon decor shape, so each is a silkscreen path with a round hole in it. The hole centres are the holes' own.
HEX_CENTRES = {13: (11.7, 1619.2), 14: (44.4, 1619.2), 15: (12.4, 1734.1), 16: (43.8, 1734.1)}


@pytest.mark.heavy
def test_each_of_the_four_plain_holes_sits_in_a_hexagon_drawn_as_a_silkscreen_path():
    svg = (DIST / f"{NAME}.front.svg").read_text()
    found = {}
    for n in HEX_CENTRES:
        m = re.search(r'<path d="([^"]+)"[^>]* fill-rule="evenodd"[^>]* transform="translate\(([-\d.]+) ([-\d.]+)\)" id="hex-ring-%d"' % n, svg)
        assert m, f"hexagon {n} is not drawn"
        found[n] = m
    for n, (cx, cy) in HEX_CENTRES.items():
        d, x, y = found[n].groups()
        assert abs(float(x) - cx) < 0.06 and abs(float(y) - cy) < 0.06, (n, x, y)
        corners = [float(v) for v in re.findall(r"[ML]\s*(-?[\d.]+)\s+-?[\d.]+", d)]
        assert max(corners) - min(corners) == pytest.approx(5.5, abs=0.06), "5.5 across the corners"
        assert d.count("a2.1") == 2, "a 4.2 round hole in the hexagon"
    holes = decor("front")
    for n, (cx, cy) in HEX_CENTRES.items():
        x, y, w, h = holes[f"hole-{n}"]
        assert abs(x + w / 2 - cx) < 0.06 and abs(y + h / 2 - cy) < 0.06, f"hole {n} is concentric with its hexagon"


@pytest.mark.heavy
def test_the_removable_brackets_are_named_17_3_mm_past_the_back():
    assert "17.3" in gaps()["side-projections"]["note"]


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
    assert len([n for n in shapes if re.fullmatch(r"bracket-hole-\d+", n)]) == 8
    assert len([n for n in shapes if re.fullmatch(r"rear-mark-\d+", n)]) == 2


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
