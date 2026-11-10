"""A part on a face of a stepped housing stands on the facet under it.

`kit/section.js` answers `surfaceUnder(section, face, at, W, H, D)`: how far, in millimetres
along the face's outward normal, the section's outer surface under a part's centre row (front
and rear) or centre column (top and bottom) stands from the bounding box's face. `kit/relief.js`
`partSeats` turns the rectangles of a face's entries into one such offset per part, and
`buildFaceRelief` builds each part inside a group moved by it.

Every expected number here is found by scanning the fixture's polygon with an even-odd test
written in this file, never by asking the module. What is held: the depth under a row on the
front and the rear, the height under a column on the top and the bottom, the ends staying flat,
a part that straddles a step taking its centre's, the offsets of a part's entries agreeing, and a
device with no section being placed exactly as it was. Then the seams in the two kit files.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest
import yaml

import warmrender

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
LIB = ROOT / "library"
FIXTURE = ROOT / "spec/tests/fixtures/section/lib/devices/fixture/stepped/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

CHASSIS = yaml.safe_load(FIXTURE.read_text())["chassis"]
W, H, D = CHASSIS["width"], CHASSIS["height"], CHASSIS["depth"]
POLY = [tuple(p) for p in CHASSIS["section"]]

SCRIPT = """
import * as S from %s;
const cases = JSON.parse(process.argv[2]);
const out = cases.map(c => {
  try {
    if (c.fn === 'under') return {ok: S.surfaceUnder(c.section, c.face, c.at, c.W, c.H, c.D)};
    if (c.fn === 'point') return {ok: S.seatPoint(c.section, c.face, c.p, c.W, c.H, c.D)};
    if (c.fn === 'seat') return {ok: S.sectionSeat(c.chassis, c.W, c.H, c.D)};
    return {error: 'no such fn'};
  } catch (e) { return {error: String(e.message || e)}; }
});
console.log(JSON.stringify(out));
"""


def run(cases):
    with tempfile.TemporaryDirectory() as tmp:
        script = pathlib.Path(tmp) / "t.mjs"
        script.write_text(SCRIPT % json.dumps((KIT / "section.js").as_uri()))
        p = subprocess.run(["node", str(script), json.dumps(cases)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def under(face, at, poly=POLY):
    got = run([{"fn": "under", "section": [list(p) for p in poly], "face": face, "at": at,
                "W": W, "H": H, "D": D}])[0]
    assert "ok" in got, got
    return got["ok"]


# ---- the expected numbers, found by scanning the polygon ---------------------------------------

def inside(pt, poly=POLY):
    x, y = pt
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def scan(start, stop, probe, step=0.05):
    n = int(abs(stop - start) / step)
    sgn = 1 if stop > start else -1
    for i in range(n + 1):
        v = start + sgn * i * step
        if probe(v):
            return v
    raise AssertionError("no solid found")


def expected(face, at):
    """The outward offset of the surface found by walking in from the box's face."""
    if face == "front":
        return -scan(0, D, lambda x: inside((x, at)))
    if face == "rear":
        return scan(D, 0, lambda x: inside((x, at))) - D
    if face == "top":
        return -scan(0, H, lambda y: inside((at, y)))
    return scan(H, 0, lambda y: inside((at, y))) - H


# a row or column in each band of the fixture, away from every step
ROWS = [60.0, 143.0, 200.0]
COLS = [5.0, 100.0, 265.0, 20.0, 260.0]


@needs_node
@pytest.mark.parametrize("row", ROWS)
@pytest.mark.parametrize("face", ["front", "rear"])
def test_front_and_rear_stand_at_the_depth_of_the_outer_surface_under_the_row(face, row):
    assert under(face, row) == pytest.approx(expected(face, row), abs=0.06)


@needs_node
@pytest.mark.parametrize("col", COLS)
@pytest.mark.parametrize("face", ["top", "bottom"])
def test_top_and_bottom_stand_at_the_height_of_the_outer_surface_under_the_column(face, col):
    assert under(face, col) == pytest.approx(expected(face, col), abs=0.06)


@needs_node
def test_the_numbers_are_the_ones_the_fixture_is_drawn_with():
    # the same answers written out, so a wrong scan above cannot agree with a wrong module
    assert [under("front", r) for r in ROWS] == [-14, 0, -28]
    assert [under("rear", r) for r in ROWS] == [250 - 281, 0, 253 - 281]
    assert [under("top", c) for c in (5.0, 100.0, 265.0)] == [-132, 0, -132]
    assert [under("bottom", c) for c in (20.0, 100.0, 260.0)] == [155 - 288, 0, 155 - 288]


@needs_node
@pytest.mark.parametrize("face", ["right", "left", "comp", "nonsense"])
def test_the_end_faces_stay_flat(face):
    assert under(face, 100.0) == 0


@needs_node
def test_a_row_on_a_step_takes_the_outermost_surface_touching_it():
    assert under("front", 132.0) == 0
    assert under("rear", 132.0) == 0
    assert under("front", 155.0) == 0


@needs_node
def test_outside_the_solid_the_offset_is_zero():
    assert under("front", -5.0) == 0
    assert under("top", D + 5) == 0


@needs_node
def test_a_point_on_the_flat_plane_is_read_as_a_row_and_a_column():
    """seatPoint takes a scene point of the face plane: y is H/2 - row, z is D/2 - column."""
    pts = [
        ("front", [0, H / 2 - 200, D / 2], -28),
        ("rear", [0, H / 2 - 60, -D / 2], 250 - 281),
        ("top", [0, H / 2, D / 2 - 100], 0),
        ("top", [0, H / 2, D / 2 - 265], -132),
        ("bottom", [0, -H / 2, D / 2 - 20], 155 - 288),
        ("right", [W / 2, 0, 0], 0),
    ]
    got = run([{"fn": "point", "section": [list(p) for p in POLY], "face": f, "p": p,
                "W": W, "H": H, "D": D} for f, p, _ in pts])
    assert [g["ok"] for g in got] == [e for *_, e in pts]


# ---- a part is placed by its centre, and its entries agree --------------------------------------

PARTS = """
globalThis.location = {search: ''};
const {partSeats} = await import(%s);
const S = await import(%s);
const [rects, poly, face] = JSON.parse(process.argv[2]);
const seatAt = %s;
const seat = partSeats(rects, seatAt);
console.log(JSON.stringify(rects.map(r => seat(r))));
"""


def part_seats(rects, seat_at, poly=POLY, face="front"):
    """relief.js partSeats over `rects`, with `seat_at` (JS source of (cx, cy) => offset)."""
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "p.mjs"
        f.write_text(PARTS % (json.dumps((KIT / "relief.js").as_uri()),
                              json.dumps((KIT / "section.js").as_uri()), seat_at))
        p = subprocess.run(["node", str(f), json.dumps([rects, [list(q) for q in poly], face])],
                           capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


@needs_node
def test_a_part_that_straddles_a_step_takes_the_depth_under_its_centre_row():
    """A plug across the flange (rows 132-155): rows 100-160 centre on 130, in the upper casting,
    which stands 14 mm back; rows 110-170 centre on 140, in the flange, which reaches the plane.
    The rows between have two depths under them and the kit takes the centre's. Lint does not
    refuse it (L207 covers the end, top and bottom faces)."""
    rects = [{"owner": "up", "x": 0, "y": 100, "w": 40, "h": 60},
             {"owner": "fl", "x": 0, "y": 110, "w": 40, "h": 60}]
    assert part_seats(rects, "(cx, cy) => S.surfaceUnder(poly, face, cy, 0, 288, 281)") == [-14, 0]


@needs_node
def test_partSeats_gives_a_part_one_offset_and_a_part_with_no_owner_its_own():
    # a stand-in surface: -10 above row 135, -50 below it
    rects = [{"owner": "a", "x": 100, "y": 120, "w": 40, "h": 40},   # union 120..160, centre 140
             {"owner": "a", "x": 110, "y": 125, "w": 10, "h": 5},    # inside: the same part
             {"owner": "b", "x": 100, "y": 10, "w": 10, "h": 10},    # centre 15
             {"x": 100, "y": 200, "w": 10, "h": 10},                 # no owner, its own centre
             {"x": 100, "y": 100, "w": 10, "h": 10}]                 # no owner, its own centre 105
    assert part_seats(rects, "(x, y) => (y < 135 ? -10 : -50)") == [-50, -50, -10, -50, -10]


@needs_node
def test_no_surface_means_every_part_is_placed_where_it_was():
    rects = [{"owner": "a", "x": 1, "y": 2, "w": 3, "h": 4}, {"x": 50, "y": 50, "w": 9, "h": 9}]
    assert part_seats(rects, "null") == [0, 0]


# ---- a device that states no section is placed exactly as before --------------------------------

# a plain box, a bevelled one and a sheet body: three kinds of body the viewer already builds
AS_TODAY = ["cisco/c9300-24p", "aurcore/ais4001", "fs/cmh-6dr1u"]


@pytest.mark.heavy
@needs_node
def test_three_devices_of_other_kinds_are_placed_as_they_were(tmp_path):
    """The published chassis of a plain box, a bevelled box and a sheet body: sectionSeat answers
    null for each, so the viewer hands relief no surface, and every part on every face of every one
    is placed at offset 0 - the position it had before the offset existed."""
    cases = []
    for n, ref in enumerate(AS_TODAY):
        dev = LIB / "devices" / ref / "device.yaml"
        out = tmp_path / f"o{n}"
        r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB), "--out", str(out)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-600:]
        ch = json.loads(next(out.glob("*.configs.json")).read_text())["chassis"]
        assert "section" not in ch
        cases.append({"fn": "seat", "chassis": ch, "W": 100, "H": 100, "D": 100})
    assert [g["ok"] for g in run(cases)] == [None, None, None]
    rects = [{"owner": f"p{i}", "x": 10 * i, "y": 7 * i, "w": 20, "h": 12} for i in range(12)]
    assert part_seats(rects, "null") == [0] * 12


@needs_node
def test_a_section_chassis_gets_a_surface_and_one_without_gets_none():
    ch = {"width": W, "height": H, "depth": D, "section": [list(p) for p in POLY]}
    plain = {"width": W, "height": H, "depth": D}
    bevel = {**ch, "solid": {"polygons": []}}
    got = run([{"fn": "seat", "chassis": c, "W": W, "H": H, "D": D} for c in (ch, plain, bevel, None)])
    assert got[0]["ok"] == [list(p) for p in POLY]
    assert got[1]["ok"] is None and got[2]["ok"] is None and got[3]["ok"] is None


# ---- the seams in the kit -----------------------------------------------------------------------

def src(name):
    return (KIT / name).read_text()


def test_the_viewer_hands_relief_the_section_it_builds_the_body_from():
    code = src("viewer3d.js")
    assert "sectionSeat" in code
    assert re.search(r"buildFaceRelief\(F, \{[^}]*section: ", code, re.S)


def test_relief_builds_each_part_in_a_group_moved_by_its_seat():
    code = src("relief.js")
    assert "partSeats(" in code
    assert "seatGroup" in code
    # the seat is read from the part's centre on the flat plane, through the face's own frame
    assert "seatPoint(" in code


def test_the_tests_script_checks_nothing_new_because_section_js_is_already_in_it():
    pkg = json.loads(src("package.json"))
    assert "node --check section.js" in pkg["scripts"]["test"]
