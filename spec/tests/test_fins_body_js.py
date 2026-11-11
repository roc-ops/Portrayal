"""The 3D body of a housing that states `chassis.fins`: the section cut back to its core and the ribs.

`kit/section.js` turns the end profile into indexed geometry arrays. With `chassis.fins` the body
is the section with each inside field's zone cut back to its core surface, everywhere along the
length (the end margins carry no ribs), and the ribs are slabs added from the core up to their step
height, merged into the same buffer, not one mesh each. Every number below is recomputed here from
the raw arrays and from `portrayal.fins`, the one place the compiler reads the key; the module is
never asked to check its own arithmetic.

What is held: the cut-back loop and its area, the vertex and index counts of the merged buffer, each
rib's box and its height, the materials and UVs by the way each facet looks, outward normals, the
bounds of the whole body against the section's box, ribs that stand outside the box, the reach the
camera fit adds for them, what the seat does for a part that slips onto a field, and that a
chassis with no fins builds exactly as it did.
"""
import copy
import json
import math
import pathlib
import re
import shutil
import subprocess
import tempfile

import pytest
import yaml

from portrayal import fins as fins_mod

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
FIXTURES = ROOT / "spec/tests/fixtures/fins/lib/devices/fixture"
STEPPED = ROOT / "spec/tests/fixtures/section/lib/devices/fixture/stepped/device.yaml"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

CHASSIS = yaml.safe_load((FIXTURES / "finned/device.yaml").read_text())["chassis"]
OUT = yaml.safe_load((FIXTURES / "finned-outside/device.yaml").read_text())["chassis"]
W, H, D = CHASSIS["width"], CHASSIS["height"], CHASSIS["depth"]
SECTION = CHASSIS["section"]
FINS = CHASSIS["fins"]

SCRIPT = """
import * as S from %s;
const cases = JSON.parse(process.argv[2]);
const out = cases.map(c => {
  try {
    if (c.fn === 'arrays') return {ok: S.sectionArrays(c.section, c.W, c.H, c.D, c.fins)};
    if (c.fn === 'loops') return {ok: S.bodyLoops(c.section, c.fins, c.H)};
    if (c.fn === 'reach') return {ok: S.finReach(c.chassis)};
    if (c.fn === 'seat') return {ok: S.surfaceUnder(c.section, c.face, c.at, c.W, c.H, c.D, c.fins)};
    if (c.fn === 'seatPoint') return {ok: S.seatPoint(c.section, c.face, c.p, c.W, c.H, c.D, c.fins)};
    if (c.fn === 'seatFor') return {ok: S.sectionSeat(c.chassis, c.W, c.H, c.D)};
    if (c.fn === 'seatFins') return {ok: S.seatFins(c.chassis, c.W, c.H, c.D)};
    return {ok: S.sectionBody(c.chassis, c.W, c.H, c.D)};
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


def one(case):
    got = run([case])[0]
    assert "ok" in got, got
    return got["ok"]


def arrays(chassis, w=None, h=None, d=None, fins="chassis"):
    f = chassis.get("fins") if fins == "chassis" else fins
    return one({"fn": "arrays", "section": chassis["section"], "W": w or chassis["width"],
                "H": h or chassis["height"], "D": d or chassis["depth"], "fins": f})


@pytest.fixture(scope="module")
def body():
    return arrays(CHASSIS)


@pytest.fixture(scope="module")
def outside():
    return arrays(OUT)


# ---- recomputing, never asking the module -------------------------------------------------

def verts(a):
    p = a["positions"]
    return [tuple(p[i:i + 3]) for i in range(0, len(p), 3)]


def tris(a):
    v, idx = verts(a), a["indices"]
    return [[v[idx[i + k]] for k in range(3)] for i in range(0, len(idx), 3)]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def tri_normal(t):
    n = cross(sub(t[1], t[0]), sub(t[2], t[0]))
    ln = math.hypot(*n)
    return tuple(c / ln for c in n), ln / 2


def area2(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def box_uv(mi, p, w, h, d):
    """BoxGeometry's layout in three r161, written out: the face's own u and v."""
    x, y, z = p
    if mi == 0: return ((-z + d / 2) / d, 1 - (-y + h / 2) / h)
    if mi == 1: return ((z + d / 2) / d, 1 - (-y + h / 2) / h)
    if mi == 2: return ((x + w / 2) / w, 1 - (z + d / 2) / d)
    if mi == 3: return ((x + w / 2) / w, 1 - (-z + d / 2) / d)
    if mi == 4: return ((x + w / 2) / w, 1 - (-y + h / 2) / h)
    return ((-x + w / 2) / w, 1 - (-y + h / 2) / h)


def group_of(a, i):
    for g in a["groups"]:
        if g["start"] <= i < g["start"] + g["count"]:
            return g["materialIndex"]


FACING = {0: (1, 0, 0), 1: (-1, 0, 0), 2: (0, 1, 0), 3: (0, -1, 0), 4: (0, 0, 1), 5: (0, 0, -1)}


def rib_vertices(a, w):
    """The vertices of the ribs: the body's only ones are on the two end planes, x = +-w/2."""
    return [(i, p) for i, p in enumerate(verts(a)) if abs(abs(p[0]) - w / 2) > 1e-6]


def rib_groups(a, w):
    """The ribs of a buffer as `[(side, [vertex index, ...])]`, 20 vertices each. A rib's vertices
    all lie on its two ends along the length (x0 and x1), the ribs of one side do not overlap along
    the length, and the top ribs are above the middle of the box and the bottom ones below it."""
    out = []
    for side, keep in (("top", lambda y: y > 0), ("bottom", lambda y: y < 0)):
        vs = [(i, p) for i, p in rib_vertices(a, w) if keep(p[1])]
        xs = sorted({round(p[0], 6) for _i, p in vs})
        assert len(xs) % 2 == 0
        for x0, x1 in zip(xs[0::2], xs[1::2]):
            mine = [i for i, p in vs if x0 - 1e-6 <= p[0] <= x1 + 1e-6]
            assert len(mine) == 20, (side, x0, x1, len(mine))
            out.append((side, mine))
    return out


def ribs_of(a, w):
    """Each rib's (min, max) box, from its own 20 vertices (4 per face, 5 faces)."""
    vs = verts(a)
    out = []
    for _side, idx in rib_groups(a, w):
        pts = [vs[i] for i in idx]
        out.append((tuple(min(p[c] for p in pts) for c in range(3)),
                    tuple(max(p[c] for p in pts) for c in range(3))))
    return out


# ---- the cut-back body --------------------------------------------------------------------

@needs_node
def test_the_body_is_the_section_cut_back_to_each_fields_core():
    loops = one({"fn": "loops", "section": SECTION, "fins": FINS, "H": H})
    assert len(loops) == 1
    pts = [tuple(p) for p in loops[0]]
    assert area2(pts) > 0                                       # still clockwise with y down
    want = area2([tuple(p) for p in SECTION]) - 2 * (236.0 * 29.0) - 2 * (225.0 * 48.0)
    assert area2(pts) == pytest.approx(want)
    # the top of the body is at the top core, 29, and the bottom at 288 - 48 = 240
    assert min(y for _x, y in pts) == 29.0 and max(y for _x, y in pts) == 240.0
    assert len(pts) == 12                                       # the cut moves vertices, it adds none here


@needs_node
def test_a_section_with_no_fins_is_cut_back_by_nothing():
    for fins in (None, []):
        loops = one({"fn": "loops", "section": SECTION, "fins": fins, "H": H})
        assert [[list(p) for p in lp] for lp in loops] == [[list(p) for p in SECTION]]


@needs_node
def test_a_core_deeper_than_the_wall_cuts_the_flange_and_leaves_one_body():
    """Core 150 takes the whole upper casting and 18 mm of the flange across the edge's 236: what
    is left is one U-shaped body, not two."""
    fins = [{**FINS[0], "core": 150.0}]
    loops = one({"fn": "loops", "section": SECTION, "fins": fins, "H": H})
    assert len(loops) == 1
    want = area2([tuple(p) for p in SECTION]) - 2 * (236.0 * 132.0 + 236.0 * 18.0)      # area2 is twice the area
    assert area2([tuple(p) for p in loops[0]]) == pytest.approx(want)
    assert min(y for _x, y in loops[0]) == 132.0                # the flange's own ears reach up to 132


@needs_node
def test_an_outside_field_cuts_nothing():
    loops = one({"fn": "loops", "section": OUT["section"], "fins": OUT["fins"], "H": OUT["height"]})
    assert [[list(p) for p in lp] for lp in loops] == [[list(p) for p in OUT["section"]]]


# ---- the merged buffer --------------------------------------------------------------------

@needs_node
def test_the_buffer_holds_the_body_and_82_ribs_of_20_vertices(body):
    assert len(fins_mod.ribs(FINS[0])) + len(fins_mod.ribs(FINS[1])) == 82
    assert len(verts(body)) == 72 + 82 * 20 == 1712
    assert len(body["indices"]) == 132 + 82 * 5 * 6 == 2592
    assert len(body["normals"]) == len(body["positions"]) and len(body["uvs"]) == 2 * len(verts(body))


@needs_node
def test_it_is_one_buffer_with_one_group_a_material_in_ascending_order(body):
    mats = [g["materialIndex"] for g in body["groups"]]
    assert mats == sorted(set(mats))
    end = 0
    for g in body["groups"]:
        assert g["start"] == end and g["count"] % 3 == 0
        end += g["count"]
    assert end == len(body["indices"])
    assert set(mats) == {0, 1, 2, 3, 4, 5}


@needs_node
def test_the_whole_body_fills_the_chassis_box(body):
    """Cut back, the casting alone is shorter than the box; with the ribs standing to the edge
    the bounds are the section's, which are the chassis box's."""
    vs = verts(body)
    for axis, half in ((0, W / 2), (1, H / 2), (2, D / 2)):
        assert min(v[axis] for v in vs) == pytest.approx(-half)
        assert max(v[axis] for v in vs) == pytest.approx(half)


@needs_node
def test_the_casting_alone_is_cut_back_to_the_cores(body):
    """The body's own vertices lie on the end planes, x = +-W/2: their y runs from the top core
    to the bottom core."""
    cast = [p for p in verts(body) if abs(abs(p[0]) - W / 2) < 1e-6]
    assert len(cast) == 72
    assert max(p[1] for p in cast) == pytest.approx(H / 2 - 29.0)
    assert min(p[1] for p in cast) == pytest.approx(-H / 2 + 48.0)


@needs_node
def test_each_rib_is_a_slab_on_the_core_as_long_as_its_rib_and_as_wide_as_the_edge(body):
    ribs = ribs_of(body, W)
    assert len(ribs) == 82
    top = [r for r in ribs if r[1][1] > 0]
    bottom = [r for r in ribs if r[1][1] <= 0]
    assert len(top) == 41 and len(bottom) == 41
    # a rib is `rib` thick along the length; the x of rib i is span start + i * pitch, from the left end
    want = [(-W / 2 + 20.0 + 14.0 * i, -W / 2 + 27.0 + 14.0 * i) for i in range(41)]
    assert sorted((r[0][0], r[1][0]) for r in top) == pytest.approx(sorted(want))
    # across the depth it fills the edge: 14 to 250 on the top, 28 to 253 on the bottom
    for lo, hi in top:
        assert lo[2] == pytest.approx(D / 2 - 250.0) and hi[2] == pytest.approx(D / 2 - 14.0)
        assert lo[1] == pytest.approx(H / 2 - 29.0) and hi[1] == pytest.approx(H / 2)
    for lo, hi in bottom:
        assert lo[2] == pytest.approx(D / 2 - 253.0) and hi[2] == pytest.approx(D / 2 - 28.0)
        assert hi[1] == pytest.approx(-H / 2 + 48.0)
    # the bottom ribs stand at their step heights: 48 reaches the edge, 32 stops 16 short
    reach = sorted({round(hi[1] - lo[1], 6) for lo, hi in bottom})
    assert reach == [32.0, 48.0]
    assert sum(1 for lo, hi in bottom if hi[1] - lo[1] > 40.0) == 24


@needs_node
def test_a_rib_has_five_faces_and_none_against_the_core(body):
    mats_of_vertex = {}
    for t in range(0, len(body["indices"]), 3):
        for k in range(3):
            i = body["indices"][t + k]
            mats_of_vertex.setdefault(i, group_of(body, t))
    # a rib's 20 vertices, by the face each is on: the tip, both ends along the length and both
    # ends across the depth, 4 each; and none on the face against the core
    for side, idx in rib_groups(body, W):
        tip = 2 if side == "top" else 3
        assert sorted(mats_of_vertex[i] for i in idx) == sorted([0] * 4 + [1] * 4 + [tip] * 4 + [4] * 4 + [5] * 4)


@needs_node
def test_every_triangle_faces_out_of_its_solid_and_agrees_with_its_stored_normal(body):
    a = body
    for t in range(0, len(a["indices"]), 3):
        tri = [verts(a)[a["indices"][t + k]] for k in range(3)]
        n, area = tri_normal(tri)
        assert area > 1e-9
        stored = tuple(a["normals"][3 * a["indices"][t + k] + c] for k in range(1) for c in range(3))
        assert n == pytest.approx(stored, abs=1e-9)
        assert n == pytest.approx(FACING[group_of(a, t)], abs=1e-9)


@needs_node
def test_every_vertex_has_the_uv_boxgeometry_gives_that_point_on_its_face(body):
    for g in body["groups"]:
        for i in range(g["start"], g["start"] + g["count"]):
            vi = body["indices"][i]
            p = verts(body)[vi]
            want = box_uv(g["materialIndex"], p, W, H, D)
            assert (body["uvs"][2 * vi], body["uvs"][2 * vi + 1]) == pytest.approx(want, abs=1e-6)


@needs_node
def test_the_core_surface_faces_up_where_the_top_was_and_a_rib_top_is_the_tip_line(body):
    """In the top material, the casting's own facets lie at the core (115) and each rib's top at
    the edge (144): the rib tops are the highest facing-up triangles."""
    up = [t for t in tris(body) if tri_normal(t)[0][1] > 0.99]
    levels = sorted({round(t[0][1], 6) for t in up})
    # the flange's tops at 288/2 - 132 = 12, the core at 115, the rib tips at the edge, 144
    assert levels == pytest.approx([H / 2 - 132.0, H / 2 - 29.0, H / 2])


@needs_node
def test_the_vertices_a_triangulation_makes_cover_the_cut_back_cap_exactly(body):
    caps = [t for t in tris(body) if abs(t[0][0] - W / 2) < 1e-9 and abs(tri_normal(t)[0][0] - 1) < 1e-9
            and all(abs(p[0] - W / 2) < 1e-9 for p in t)]
    loops = one({"fn": "loops", "section": SECTION, "fins": FINS, "H": H})
    assert sum(tri_normal(t)[1] for t in caps) == pytest.approx(area2([tuple(p) for p in loops[0]]) / 2)


# ---- ribs outside the box -----------------------------------------------------------------

@needs_node
def test_an_outside_box_keeps_its_plain_body_and_adds_14_ribs(outside):
    assert len(verts(outside)) == 24 + 14 * 20
    ribs = ribs_of(outside, OUT["width"])
    assert len(ribs) == 14
    top = [r for r in ribs if r[0][1] >= OUT["height"] / 2 - 1e-9]
    bottom = [r for r in ribs if r[1][1] <= -OUT["height"] / 2 + 1e-9]
    assert len(top) == 7 and len(bottom) == 7
    # they stand out of the edge: root on the casting's edge, tip beyond the box
    assert sorted({round(hi[1] - lo[1], 6) for lo, hi in top}) == [12.0, 20.0]
    assert sorted({round(hi[1] - lo[1], 6) for lo, hi in bottom}) == [10.0]
    assert max(hi[1] for _lo, hi in top) == pytest.approx(OUT["height"] / 2 + 20.0)
    assert min(lo[1] for lo, _hi in bottom) == pytest.approx(-OUT["height"] / 2 - 10.0)


@needs_node
def test_the_casting_of_an_outside_box_is_the_chassis_box(outside):
    cast = [p for p in verts(outside) if abs(abs(p[0]) - OUT["width"] / 2) < 1e-6]
    assert len(cast) == 24
    assert max(p[1] for p in cast) == pytest.approx(OUT["height"] / 2)
    assert min(p[1] for p in cast) == pytest.approx(-OUT["height"] / 2)


@needs_node
def test_the_reach_of_the_ribs_beyond_the_box():
    assert one({"fn": "reach", "chassis": OUT}) == {"top": 20.0, "bottom": 10.0}
    assert one({"fn": "reach", "chassis": CHASSIS}) == {"top": 0.0, "bottom": 0.0}
    assert one({"fn": "reach", "chassis": {"w": 1, "h": 1, "d": 1}}) == {"top": 0.0, "bottom": 0.0}
    assert fins_mod.reach(OUT) == (20.0, 10.0)


# ---- the seam: sectionBody and the viewer -------------------------------------------------

@needs_node
def test_a_chassis_with_fins_gets_the_arrays_through_sectionBody():
    got = one({"fn": "body", "chassis": CHASSIS, "W": W, "H": H, "D": D})
    assert "refused" not in got and len(got["arrays"]["positions"]) // 3 == 1712


@needs_node
def test_fins_with_no_section_are_ignored_by_the_viewer():
    got = one({"fn": "body", "chassis": {"w": W, "h": H, "d": D, "fins": FINS}, "W": W, "H": H, "D": D})
    assert got is None


@needs_node
def test_fins_that_cannot_be_built_are_refused_not_thrown():
    bad = copy.deepcopy(CHASSIS)
    bad["fins"][0]["span"] = [400.0, 20.0]
    got = one({"fn": "body", "chassis": bad, "W": W, "H": H, "D": D})
    # a field that cannot be read is skipped (lint refuses it), so the casting is built without it
    assert len(got["arrays"]["positions"]) // 3 == 72 + 41 * 20


@needs_node
def test_more_than_400_ribs_is_refused():
    bad = copy.deepcopy(CHASSIS)
    for f in bad["fins"]:
        f.pop("steps", None)
        f["span"], f["rib"], f["gap"] = [0.0, 600.0], 1.0, 0.5
    got = one({"fn": "body", "chassis": bad, "W": W, "H": H, "D": D})
    assert got["refused"] and "400" in got["refused"]


# ---- no fins: built as it was -------------------------------------------------------------

STEP = yaml.safe_load(STEPPED.read_text())["chassis"]


@needs_node
def test_a_section_with_no_fins_builds_exactly_as_it_did():
    plain = one({"fn": "arrays", "section": STEP["section"], "W": STEP["width"], "H": STEP["height"],
                 "D": STEP["depth"]})
    for fins in (None, []):
        again = one({"fn": "arrays", "section": STEP["section"], "W": STEP["width"], "H": STEP["height"],
                     "D": STEP["depth"], "fins": fins})
        assert again == plain
    assert len(plain["positions"]) // 3 == 72 and len(plain["indices"]) == 132


@needs_node
def test_the_stepped_fixtures_chassis_gets_the_same_body_through_sectionBody():
    got = one({"fn": "body", "chassis": {**STEP, "w": STEP["width"]}, "W": STEP["width"],
               "H": STEP["height"], "D": STEP["depth"]})
    assert len(got["arrays"]["positions"]) // 3 == 72


# ---- the seat of a part that slips onto a field --------------------------------------------

@needs_node
def test_a_front_part_in_the_zone_is_seated_from_the_first_row_of_the_core():
    """Core 150 takes the upper casting off: at row 10 the front facet at x = 14 is cut away, and the
    seat is read at the core line (row 150), where the flange is at x = 0. Without the fins the same
    row would answer 14 mm back, from a wall that is not there."""
    fins = [{**FINS[0], "core": 150.0}]
    base = {"section": SECTION, "face": "front", "at": 10.0, "W": W, "H": H, "D": D}
    assert one({"fn": "seat", **base}) == -14.0
    assert one({"fn": "seat", **base, "fins": fins}) == 0.0
    # a row below the zone is the casting's own
    assert one({"fn": "seat", **base, "at": 200.0, "fins": fins}) == -28.0
    # the bottom zone clamps the other way: row 280 is in it, row 138 is its first
    bottom = [{**FINS[1], "core": 150.0, "steps": [{"span": [20.0, 587.0], "height": 150.0}]}]
    assert one({"fn": "seat", **{**base, "at": 280.0}, "fins": bottom}) == one(
        {"fn": "seat", **{**base, "at": 138.0}})


@needs_node
def test_a_rear_part_in_the_zone_is_clamped_the_same_way():
    fins = [{**FINS[0], "core": 150.0}]
    base = {"section": SECTION, "face": "rear", "at": 10.0, "W": W, "H": H, "D": D}
    assert one({"fn": "seat", **base, "fins": fins}) == one({"fn": "seat", **base, "at": 150.0})


@needs_node
def test_a_part_on_the_top_stands_on_the_tip_plane_and_the_others_are_unchanged():
    base = {"section": SECTION, "W": W, "H": H, "D": D}
    for face, at in (("top", 100.0), ("bottom", 100.0), ("right", 50.0), ("front", 200.0)):
        assert one({"fn": "seat", **base, "face": face, "at": at, "fins": FINS}) == \
            one({"fn": "seat", **base, "face": face, "at": at})


@needs_node
def test_the_seat_is_handed_the_polygon_as_before_and_the_fields_beside_it():
    chassis = {**CHASSIS, "w": W, "h": H, "d": D}
    assert one({"fn": "seatFor", "chassis": chassis, "W": W, "H": H, "D": D}) == SECTION
    assert one({"fn": "seatFins", "chassis": chassis, "W": W, "H": H, "D": D}) == FINS
    # a section with no fins, and a box with neither, hand over none
    stepped = {**STEP, "w": STEP["width"]}
    assert one({"fn": "seatFins", "chassis": stepped, "W": W, "H": H, "D": D}) is None
    assert one({"fn": "seatFins", "chassis": {"w": W, "h": H, "d": D}, "W": W, "H": H, "D": D}) is None
    # a section that is refused (more than 400 ribs) is seated on the flat planes, fins and all
    many = copy.deepcopy(chassis)
    for f in many["fins"]:
        f.pop("steps", None)
        f["span"], f["rib"], f["gap"] = [0.0, 600.0], 1.0, 0.5
    assert one({"fn": "seatFor", "chassis": many, "W": W, "H": H, "D": D}) is None
    assert one({"fn": "seatFins", "chassis": many, "W": W, "H": H, "D": D}) is None


# ---- the viewer ---------------------------------------------------------------------------

def viewer_code():
    import re
    src = (KIT / "viewer3d.js").read_text()
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?<![:'\"])//[^\n]*", "", src)


def test_the_viewer_fits_the_camera_to_the_ribs_that_stand_outside_the_box():
    code = viewer_code()
    assert "finReach" in code
    i = code.index("openOn(W, H + ")
    assert "finReach(devIndex.chassis)" in code[i - 400:i]
    assert "2 * Math.max(reach.top, reach.bottom)" in code[i:i + 120]
    # and the box itself is still what the opening view is first fitted to
    assert "openOn(W, H, D)" in code
    assert code.index("openOn(W, H, D)") < i


def test_ribs_outside_the_box_are_not_painted_flat_beyond_the_face():
    """A drawing that grows past its face is painted beyond it on a flat plane; the ribs are
    geometry in this body, so the viewer says so and relief leaves the plane out."""
    code = viewer_code()
    assert "noWing: ribsOutside" in code
    relief = re.sub(r"(?<![:'\"])//[^\n]*", "", (KIT / "relief.js").read_text())
    assert "if (beyond && !ctx.sheet && !ctx.noWing)" in relief


def test_the_viewer_hands_the_section_body_the_fins():
    code = viewer_code()
    assert "sectionBody(devIndex && devIndex.chassis, W, H, D)" in code
