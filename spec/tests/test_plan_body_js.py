"""The closed 3D body of a housing that states `chassis.plan-outline`: the section cut band by band.

`kit/section.js` `sectionArrays(section, W, H, D, fins, clip, plan)` builds the body from what the
plan leaves of it (`kit/plan.js`, the x-sweep, written once more in JavaScript; `kit/plan-body.js`
turns the pieces into welded faces). Every number below is recomputed here, from first principles
(is this point in the solid?) and from `portrayal.plan`'s pieces, never by asking the module to check
its own arithmetic.

What is held: counts and bounds (the body's box is the chassis box), every normal pointing out of
the solid, the material of each triangle by the way it faces and where its wall comes from (a section
wall keeps its face's slot, a plan wall is slot 7, an end cap is slot 0 or 1), the UVs (a plan wall's
is the special case, never read from `boxUV`), a mesh that is watertight (every edge shared by exactly
two triangles, once in each direction) with and without ribs, the volume equal to the sum of
(piece area x row height) from `plan.py`'s pieces, a section wall that wins within 0.5 mm of a plan
edge and a plan wall that stands when the edge is 0.7 mm in, a ledge in a wall where a band edge is not
a section row, and the 400-rib cap counted before the plan clips the ribs. Then the seams in
`viewer3d.js`: the new slot, picking and level of detail, the camera fit, and a housing without the
key built exactly as it was.
"""
import hashlib
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

import pytest
import yaml

import warmrender
from portrayal import libwalk
from portrayal import plan as P

from test_plan_body_cases import ASYMMETRIC, three_band
from test_section_body_js import box_uv, cross, sub, tri_normal, tris, verts, viewer_code

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
LIB = ROOT / "library"
FIXTURES = ROOT / "spec/tests/fixtures"
RENDER = ROOT / "spec/tools/portrayal/render.py"
AS_TODAY = FIXTURES / "plan_outline/as-today.json"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

SCRIPT = """
import * as S from %s;
const reqs = JSON.parse(process.argv[2]);
console.log(JSON.stringify(reqs.map(r => {
  try {
    if (r.fn === 'face') return {ok: S.planWallFace(r.n)};
    if (r.fn === 'color') return {ok: S.planWallColor(r.svg)};
    if (r.fn === 'halves') return {ok: S.sectionHalves(r.chassis, r.W, r.H, r.D)};
    if (r.fn === 'body') return {ok: S.sectionBody(r.chassis, r.W, r.H, r.D)};
    return {ok: S.sectionArrays(r.section, r.W, r.H, r.D, r.fins, undefined, r.plan)};
  } catch (e) { return {error: String(e.message || e)}; }
})));
"""

PLAN_WALL = 7
SEAM = 6

# the three-band box and the asymmetric one, each with ribs on both long edges
THREE = three_band()
THREE_FINS = [
    {"on": "top", "span": [40, 560], "core": 29, "rib": 7, "gap": 7},
    {"on": "bottom", "span": [40, 560], "core": 48, "rib": 7, "gap": 7,
     "steps": [{"span": [40, 190], "height": 48}, {"span": [190, 420], "height": 32}, {"span": [420, 560], "height": 48}]},
]
ASYM_FINS = [
    {"on": "top", "span": [10, 70], "core": 6, "rib": 3, "gap": 3},
    {"on": "bottom", "span": [20, 50], "core": 10, "rib": 2, "gap": 2},
]


def run(reqs):
    with tempfile.TemporaryDirectory() as tmp:
        script = pathlib.Path(tmp) / "t.mjs"
        script.write_text(SCRIPT % json.dumps((KIT / "section.js").as_uri()))
        p = subprocess.run(["node", str(script), json.dumps(reqs)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:]
    return json.loads(p.stdout)


def arrays_of(box, fins=None, expect_error=False):
    got = run([{"section": box["section"], "W": box["width"], "H": box["height"], "D": box["depth"],
                "fins": fins, "plan": box["plan-outline"]}])[0]
    if expect_error:
        assert "error" in got, "expected the build to be refused"
        return got["error"]
    assert "ok" in got, got
    return got["ok"]


_cache = {}


def built(name):
    if name not in _cache:
        box, fins = {"three": (THREE, None), "three-ribs": (THREE, THREE_FINS), "asym": (ASYMMETRIC, None),
                     "asym-ribs": (ASYMMETRIC, ASYM_FINS)}[name]
        _cache[name] = (box, fins, arrays_of(box, fins))
    return _cache[name]


NAMES = ["three", "three-ribs", "asym", "asym-ribs"]


# ---- first principles: is a point in the solid? --------------------------------------------

def even_odd(pt, poly):
    x, y = pt
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def ribs_of(box, fins):
    """[(x0, x1, on, tip, root)] as fins.py reads the fields, the section's edge extent beside them."""
    out = []
    H = box["height"]
    for f in fins or []:
        a, b = f["span"]
        n = int(math.floor((b - a + f["gap"] + 0.01) / (f["rib"] + f["gap"])))
        for i in range(n):
            x0 = a + i * (f["rib"] + f["gap"])
            x1 = x0 + f["rib"]
            height = f["core"]
            for st in f.get("steps", []):
                if st["span"][0] <= (x0 + x1) / 2 < st["span"][1]:
                    height = st["height"]
            top = f["on"] == "top"
            root = f["core"] if top else H - f["core"]
            out.append((x0, x1, f["on"], root - height if top else root + height, root))
    return out


def edge_extent(box, on):
    y = 0 if on == "top" else box["height"]
    pts = [tuple(p) for p in box["section"]]
    runs = [(min(a[0], b[0]), max(a[0], b[0])) for a, b in zip(pts, pts[1:] + pts[:1])
            if a[1] == b[1] == y and a[0] != b[0]]
    assert len(runs) == 1
    return runs[0]


def band_at(box, h):
    bands = box["plan-outline"]
    if h < bands[0]["heights"][0]:
        return bands[0]
    for b in bands:
        if b["heights"][0] <= h < b["heights"][1]:
            return b
    return bands[-1]


def solid_has(box, fins, p):
    """A viewer-frame point in the solid the plan and the ribs make, from the definitions alone."""
    W, H, D = box["width"], box["height"], box["depth"]
    x, y, z = p[0] + W / 2, p[2] + D / 2, None
    h = H / 2 - p[1]
    sx = D - y
    if not (-1e-9 <= x <= W + 1e-9):
        return False
    b = band_at(box, h)
    if not even_odd((x, y), [tuple(q) for q in b["points"]]):
        return False
    section = [tuple(q) for q in box["section"]]
    cut = False
    for f in fins or []:
        if f["on"] == "top" and 0 <= h < f["core"] or f["on"] == "bottom" and H - f["core"] <= h <= H:
            e0, e1 = edge_extent(box, f["on"])
            if e0 < sx < e1:
                cut = True
    if even_odd((sx, h), section) and not cut:
        return True
    for x0, x1, on, tip, root in ribs_of(box, fins):
        e0, e1 = edge_extent(box, on)
        if x0 < x < x1 and e0 < sx < e1 and min(tip, root) <= h < max(tip, root):
            return True
    return False


# ---- recomputing, never asking the module -------------------------------------------------

def edges(a):
    v, idx = verts(a), a["indices"]
    out = Counter()
    for i in range(0, len(idx), 3):
        k = [tuple(round(c, 5) for c in v[idx[i + j]]) for j in range(3)]
        for j in range(3):
            out[(k[j], k[(j + 1) % 3])] += 1
    return out


def volume(a):
    v, idx = verts(a), a["indices"]
    s = 0.0
    for i in range(0, len(idx), 3):
        p0, p1, p2 = v[idx[i]], v[idx[i + 1]], v[idx[i + 2]]
        c = cross(p1, p2)
        s += p0[0] * c[0] + p0[1] * c[1] + p0[2] * c[2]
    return s / 6.0


def expected_volume(box, fins):
    """Sum of (piece area x row height) from plan.py's pieces, less the cut-back casting, plus the
    ribs each clipped by its own band."""
    plan = P.Plan({k: box[k] for k in ("width", "height", "depth", "section", "plan-outline")})
    W, H, D = box["width"], box["height"], box["depth"]
    total = sum(sum(P.area(p) for p in s["pieces"]) * (s["heights"][1] - s["heights"][0]) for s in plan.solid)
    for f in fins or []:
        e0, e1 = edge_extent(box, f["on"])
        c0, c1 = (0.0, float(f["core"])) if f["on"] == "top" else (H - f["core"], float(H))
        rect = [(0.0, D - e1), (float(W), D - e1), (float(W), D - e0), (0.0, D - e0)]
        for s in plan.solid:
            o = min(s["heights"][1], c1) - max(s["heights"][0], c0)
            if o > 1e-9:
                polys = [P.polygon(p) for p in s["pieces"]]
                total -= o * sum(P.area(p) for p in P.sweep([polys, [rect]]))
    for x0, x1, on, tip, root in ribs_of(box, fins):
        e0, e1 = edge_extent(box, on)
        rect = [(x0, D - e1), (x1, D - e1), (x1, D - e0), (x0, D - e0)]
        lo, hi = min(tip, root), max(tip, root)
        for i, b in enumerate(plan.bands):
            b0 = -1e9 if i == 0 else b["heights"][0]
            b1 = 1e9 if i == len(plan.bands) - 1 else b["heights"][1]
            o = min(hi, b1) - max(lo, b0)
            if o > 1e-9:
                total += o * sum(P.area(p) for p in P.sweep([[b["points"]], [rect]]))
    return total


def rows_plan(box):
    return P.rows([tuple(p) for p in box["section"]], box["depth"])


# ---- counts and bounds --------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("name", NAMES)
def test_the_bounding_box_is_the_chassis_box_ribs_inside_it(name):
    box, fins, a = built(name)
    v = verts(a)
    for axis, half in enumerate((box["width"] / 2, box["height"] / 2, box["depth"] / 2)):
        assert min(p[axis] for p in v) == pytest.approx(-half, abs=1e-6)
        assert max(p[axis] for p in v) == pytest.approx(half, abs=1e-6)


@needs_node
@pytest.mark.parametrize("name", NAMES)
def test_arrays_are_well_formed_groups_ascend_and_cover_every_index(name):
    box, fins, a = built(name)
    n = len(a["positions"]) // 3
    assert len(a["normals"]) == len(a["positions"]) and len(a["uvs"]) == 2 * n
    assert len(a["indices"]) % 3 == 0 and min(a["indices"]) >= 0 and max(a["indices"]) < n
    mats = [g["materialIndex"] for g in a["groups"]]
    assert mats == sorted(mats) and len(set(mats)) == len(mats)
    assert set(mats) <= {0, 1, 2, 3, 4, 5, PLAN_WALL}
    assert PLAN_WALL in mats and SEAM not in mats          # a plan wall exists; the closed body has no cut face
    pos = 0
    for g in a["groups"]:
        assert g["start"] == pos and g["count"] % 3 == 0 and g["count"] > 0
        pos += g["count"]
    assert pos == len(a["indices"])
    for t in tris(a):
        assert tri_normal(t)[1] > 1e-9, "a degenerate triangle"


@needs_node
def test_a_box_that_is_not_cut_has_the_ribs_beyond_the_plain_boxs_triangle_count():
    plain = built("three")[2]
    ribbed = built("three-ribs")[2]
    assert len(ribbed["indices"]) > len(plain["indices"])


# ---- facing -------------------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("name", NAMES)
def test_every_triangle_faces_out_of_the_solid_and_agrees_with_its_stored_normal(name):
    box, fins, a = built(name)
    eps = 0.01
    idx, norms, v = a["indices"], a["normals"], verts(a)
    for i in range(0, len(idx), 3):
        t = [v[idx[i + k]] for k in range(3)]
        n, area = tri_normal(t)
        c = tuple(sum(p[k] for p in t) / 3 for k in range(3))
        assert not solid_has(box, fins, tuple(c[k] + eps * n[k] for k in range(3))), (t, n)
        assert solid_has(box, fins, tuple(c[k] - eps * n[k] for k in range(3))), (t, n)
        for k in range(3):
            assert norms[3 * idx[i + k]:3 * idx[i + k] + 3] == pytest.approx(n, abs=1e-6)


# ---- the material of each triangle, by its facing and where it comes from -----------------

FACING = {0: (1, 0, 0), 1: (-1, 0, 0), 2: (0, 1, 0), 3: (0, -1, 0), 4: (0, 0, 1), 5: (0, 0, -1)}


def section_lines(box, h):
    """The plan-frame y of the section's front and rear walls at height h: (front, rear)."""
    for y0, y1, iv in rows_plan(box):
        if y0 <= h < y1:
            return [hi for lo, hi in iv], [lo for lo, hi in iv]
    return [], []


@needs_node
@pytest.mark.parametrize("name", ["three", "asym"])
def test_each_triangle_takes_the_material_of_its_facing_and_origin(name):
    box, fins, a = built(name)
    W, H, D = box["width"], box["height"], box["depth"]
    seen = Counter()
    for g in a["groups"]:
        mi = g["materialIndex"]
        for t in tris({**a, "groups": [g]}, mi):
            n, _ = tri_normal(t)
            c = tuple(sum(p[k] for p in t) / 3 for k in range(3))
            seen[mi] += 1
            if mi in (2, 3):
                assert n == pytest.approx(FACING[mi], abs=1e-9)
            elif mi in (0, 1):                       # an end cap: on the end, the end face's texture
                assert n == pytest.approx(FACING[mi], abs=1e-9)
                assert all(abs(abs(p[0]) - W / 2) < 1e-6 for p in t)
            elif mi in (4, 5):                       # a section wall: on the section's own front or rear
                assert n == pytest.approx(FACING[mi], abs=1e-9)
                h = H / 2 - c[1]
                front, rear = section_lines(box, h)
                assert any(abs((c[2] + D / 2) - y) < 1e-6 for y in (front if mi == 4 else rear)), (mi, c)
            else:                                    # a plan wall: horizontal normal, not a section wall or a cap
                assert mi == PLAN_WALL and abs(n[1]) < 1e-6      # (a welded wall is upright to a millionth)
                h = H / 2 - c[1]
                if abs(n[0]) < 1e-6:                 # across the width: not on a section line
                    front, rear = section_lines(box, h)
                    assert all(abs((c[2] + D / 2) - y) > 0.01 for y in (front if n[2] > 0 else rear)), c
                elif abs(n[2]) < 1e-6:               # an end wall of a casting: not on an end of the box
                    assert abs(abs(c[0]) - W / 2) > 1e-6, c
    assert all(seen[m] for m in (0, 1, 2, 3, 4, 5, PLAN_WALL)), seen


@needs_node
def test_the_three_band_box_has_slanted_plan_walls_at_its_rounded_corners():
    box, fins, a = built("three")
    slanted = [t for t in tris(a, PLAN_WALL) if abs(tri_normal(t)[0][0]) > 1e-3 and abs(tri_normal(t)[0][2]) > 1e-3]
    assert len(slanted) >= 4 * 3 * 2          # the corners of three bands, two triangles a wall
    flat = [t for t in tris(a, PLAN_WALL) if abs(tri_normal(t)[0][1]) < 1e-6]
    assert len(flat) == len(tris(a, PLAN_WALL))


# ---- UVs ----------------------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("name", NAMES)
def test_uvs_follow_boxuv_except_on_a_plan_wall_whose_uv_is_the_special_case(name):
    box, fins, a = built(name)
    W, H, D = box["width"], box["height"], box["depth"]
    v, uvs = verts(a), a["uvs"]
    for g in a["groups"]:
        for i in range(g["start"], g["start"] + g["count"]):
            k = a["indices"][i]
            if g["materialIndex"] == PLAN_WALL:
                assert uvs[2 * k:2 * k + 2] == [0, 0]
            else:
                assert uvs[2 * k:2 * k + 2] == pytest.approx(box_uv(g["materialIndex"], v[k], W, H, D), abs=1e-9)
    assert all(math.isfinite(u) for u in uvs)
    assert min(uvs) >= -1e-9 and max(uvs) <= 1 + 1e-9


# ---- watertight, volume -------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("name", NAMES)
def test_the_mesh_is_watertight_every_edge_shared_by_two_triangles_once_each_way(name):
    box, fins, a = built(name)
    e = edges(a)
    bad = [(k, n) for k, n in e.items() if n != 1 or e.get((k[1], k[0])) != 1]
    assert not bad, f"{len(bad)} edges are not shared by exactly two triangles; first {bad[:3]}"


@needs_node
@pytest.mark.parametrize("name", NAMES)
def test_the_volume_is_the_pieces_area_times_the_row_height(name):
    box, fins, a = built(name)
    assert volume(a) == pytest.approx(expected_volume(box, fins), rel=1e-6)


def tip_vertices(a, box):
    """(plan x, plan y) of the corners of the top-facing triangles on the top edge's tip line."""
    H, W, D = box["height"], box["width"], box["depth"]
    out = []
    for t in tris(a, 2):
        if all(abs(p[1] - H / 2) < 1e-6 for p in t):
            out += [(p[0] + W / 2, p[2] + D / 2) for p in t]
    return out


@needs_node
def test_a_rib_the_plan_cuts_partly_is_cut_to_the_plan_s_edge():
    """The asymmetric box's upper casting has a slanted rear edge from (6, 14) to (30, 12): the rib at
    x 10 to 13 is cut by it and the rib at x 64 to 67 stands whole against the band's straight edge."""
    box, fins, a = built("asym-ribs")
    tips = tip_vertices(a, box)
    first = [y for x, y in tips if 10 - 1e-6 <= x <= 13 + 1e-6]
    last = [y for x, y in tips if 64 - 1e-6 <= x <= 67 + 1e-6]
    assert min(first) == pytest.approx(14 + (12 - 14) * (13 - 6) / 24)             # on the slanted edge, at its far end
    assert max(first) == pytest.approx(60)
    assert min(last) == pytest.approx(12)
    assert not [1 for x, y in tips if x < 10 - 1e-6 or x > 67 + 1e-6]              # no rib outside the field


@needs_node
def test_a_rib_the_plan_removes_entirely_is_dropped():
    box = ribbed(299.75, 290.0)              # 400 ribs; the plan keeps the ones past x = 290
    a = arrays_of(box, box["_fins"])
    tips = [t for t in tris(a, 2) if all(abs(p[1] - 15) < 1e-6 for p in t)]       # H/2 = 15, the tip line
    assert sum(tri_normal(t)[1] for t in tips) == pytest.approx(13 * 0.5 * 100)   # ribs 387 to 399: 13 of the 400


# ---- a section wall wins within 0.5 mm, a plan wall does not -------------------------------

def rect_box(front_y, bands=None):
    return {"width": 40.0, "height": 20.0, "depth": 30.0, "section": [[0, 0], [30, 0], [30, 20], [0, 20]],
            "plan-outline": bands or [{"heights": [0, 20], "points": [[0, 0], [40, 0], [40, front_y], [0, front_y]]}]}


def count(a, mi):
    return len(tris(a, mi)) if any(g["materialIndex"] == mi for g in a["groups"]) else 0


@needs_node
def test_a_plan_edge_0_3_mm_inside_the_front_is_the_section_wall_and_draws_no_plan_wall_there():
    a = arrays_of(rect_box(29.7))
    front = tris(a, 4)
    assert front and sum(tri_normal(t)[1] for t in front) == pytest.approx(40 * 20)
    assert all(abs(p[2] - 15) < 1e-6 for t in front for p in t)          # on the section's front, not 0.3 in
    # the body is the whole box: no plan wall faces the front
    assert not [t for t in tris(a, PLAN_WALL) if tri_normal(t)[0][2] > 0.5]
    assert volume(a) == pytest.approx(40 * 30 * 20)


@needs_node
def test_a_plan_edge_0_7_mm_inside_the_front_is_a_plain_wall_and_the_section_wall_is_gone():
    a = arrays_of(rect_box(29.3))
    assert count(a, 4) == 0
    walls = [t for t in tris(a, PLAN_WALL) if tri_normal(t)[0][2] > 0.5]
    assert sum(tri_normal(t)[1] for t in walls) == pytest.approx(40 * 20)
    assert all(abs(p[2] - (29.3 - 15)) < 1e-6 for t in walls for p in t)
    assert volume(a) == pytest.approx(40 * 29.3 * 20)


# ---- a band edge that is not a section row ------------------------------------------------

@needs_node
def test_a_band_edge_that_is_not_a_section_row_makes_a_ledge_in_the_wall():
    inner = [[5, 5], [35, 5], [35, 25], [5, 25]]
    outer = [[0, 0], [40, 0], [40, 30], [0, 30]]
    box = rect_box(0, [{"heights": [0, 10], "points": outer}, {"heights": [10, 20], "points": inner}])
    a = arrays_of(box)
    # the section's front wall (slot 4) stands only where the outer band is: half its height
    assert sum(tri_normal(t)[1] for t in tris(a, 4)) == pytest.approx(40 * 10)
    assert sum(tri_normal(t)[1] for t in tris(a, 5)) == pytest.approx(40 * 10)
    # the ledge faces down, the ring of the outer band the inner one leaves, at the band edge
    down = tris(a, 3)
    ring = [t for t in down if abs(t[0][1]) < 1e-6]                     # y = 0: the band edge, 10 mm down
    assert sum(tri_normal(t)[1] for t in ring) == pytest.approx(40 * 30 - 30 * 20)
    assert sum(tri_normal(t)[1] for t in down) == pytest.approx(40 * 30 - 30 * 20 + 30 * 20)   # and the bottom
    # the inner band's walls are plain, 10 mm tall, all round
    assert sum(tri_normal(t)[1] for t in tris(a, PLAN_WALL)) == pytest.approx(2 * (30 + 20) * 10)
    assert volume(a) == pytest.approx(40 * 30 * 10 + 30 * 20 * 10)
    e = edges(a)
    assert all(n == 1 and e.get((k[1], k[0])) == 1 for k, n in e.items())


# ---- the 400-rib cap counts ribs before the plan clips them --------------------------------

def ribbed(span_to, plan_x):
    return {"width": 300.0, "height": 30.0, "depth": 100.0, "section": [[0, 0], [100, 0], [100, 30], [0, 30]],
            "plan-outline": [{"heights": [0, 30], "points": [[plan_x, 0], [300, 0], [300, 100], [plan_x, 100]]}],
            "_fins": [{"on": "top", "span": [0, span_to], "core": 5, "rib": 0.5, "gap": 0.25}]}


@needs_node
def test_the_rib_cap_counts_before_the_clip_so_401_ribs_the_plan_mostly_removes_are_refused():
    box = ribbed(300.5, 290.0)             # 401 ribs; the plan keeps only the last few
    err = arrays_of(box, box["_fins"], expect_error=True)
    assert "401" in err and "400" in err


@needs_node
def test_400_ribs_the_plan_mostly_removes_build_and_the_removed_ones_are_dropped():
    box = ribbed(299.75, 290.0)            # exactly 400
    whole =arrays_of({**box, "plan-outline": [{"heights": [0, 30], "points": [[0, 0], [300, 0], [300, 100], [0, 100]]}]},
                      box["_fins"])
    cut = arrays_of(box, box["_fins"])
    assert len(cut["indices"]) < len(whole["indices"]) / 4
    assert volume(cut) == pytest.approx(expected_volume(box, box["_fins"]), rel=1e-6)


# ---- refused, not thrown, by sectionBody ---------------------------------------------------

@needs_node
def test_a_plan_that_is_not_clockwise_is_refused_by_sectionBody_not_thrown():
    ch = {**THREE, "plan-outline": [{"heights": [0, 288], "points": list(reversed(THREE["plan-outline"][1]["points"]))}]}
    got = run([{"fn": "body", "chassis": ch, "W": ch["width"], "H": ch["height"], "D": ch["depth"]}])[0]["ok"]
    assert got["refused"] and "arrays" not in got


@needs_node
def test_sectionBody_hands_the_plan_to_the_arrays_and_without_it_builds_the_extrusion():
    ch = {**THREE}
    got = run([{"fn": "body", "chassis": ch, "W": 600, "H": 288, "D": 281}])[0]["ok"]
    assert PLAN_WALL in [g["materialIndex"] for g in got["arrays"]["groups"]]
    plain = {k: v for k, v in ch.items() if k != "plan-outline"}
    got = run([{"fn": "body", "chassis": plain, "W": 600, "H": 288, "D": 281}])[0]["ok"]
    assert [g["materialIndex"] for g in got["arrays"]["groups"]] == [0, 1, 2, 3, 4, 5]


# ---- the open state of such a housing builds, drawn as the extrusion until the next order ---

@needs_node
def test_the_open_state_of_a_section_plan_housing_builds_without_throwing_as_the_unclipped_extrusion():
    halves = {"base": {"outer": "top", "stands": 144.0}, "lid": {"hinge": "rear", "stands": 144.0}}
    ch = {**THREE, "halves": halves}
    got = run([{"fn": "halves", "chassis": ch, "W": 600, "H": 288, "D": 281}])[0]["ok"]
    assert "split" in got and "refused" not in got
    for part in ("base", "lid"):
        mats = {g["materialIndex"] for g in got["split"][part]["arrays"]["groups"]}
        assert PLAN_WALL not in mats and SEAM in mats          # the halves do not follow the plan yet
    closed = run([{"fn": "body", "chassis": ch, "W": 600, "H": 288, "D": 281}])[0]["ok"]
    assert PLAN_WALL in {g["materialIndex"] for g in closed["arrays"]["groups"]}


# ---- picking, level of detail, the colour --------------------------------------------------

@needs_node
def test_a_plan_wall_picks_as_the_face_it_faces():
    got = run([{"fn": "face", "n": n} for n in
               ([0, 0, 1], [0, 0, -1], [1, 0, 0], [-1, 0, 0], [0.6, 0, 0.8], [0.8, 0, -0.6], [-0.6, 0, -0.8],
                [-0.8, 0, 0.6])])
    # the larger horizontal component decides; a slanted wall at exactly 45 degrees picks the front or rear
    assert [g["ok"] for g in got] == ["front", "rear", "right", "left", "front", "right", "rear", "left"]


@needs_node
def test_a_plan_wall_picks_from_a_vector_normal_as_it_does_from_an_array():
    # the viewer hands over three's face normal, a vector with x, y and z fields (this page does not load
    # three, so a plain object with those fields stands for it); an array answers the same
    normals = [(0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0.6, 0, 0.8), (0.8, 0, -0.6),
               (0.7071, 0, 0.7071), (-0.7071, 0, -0.7071), (-0.2, 0, -0.98), (0.3, 0.1, 0.95)]
    want = ["front", "rear", "right", "left", "front", "right", "front", "rear", "rear", "front"]
    as_vector = run([{"fn": "face", "n": {"x": x, "y": y, "z": z}} for x, y, z in normals])
    as_array = run([{"fn": "face", "n": [x, y, z]} for x, y, z in normals])
    assert [g["ok"] for g in as_vector] == want
    assert [g["ok"] for g in as_array] == want


@needs_node
def test_the_wall_colour_is_the_faceplate_fill_of_the_first_face_that_states_one():
    svg = {"front": '<svg><path id="chassis-faceplate" d="M0,0 L1,1" fill="#8a9299"/></svg>',
           "rear": '<svg><rect fill="#111111" id="chassis-faceplate"/></svg>'}
    other = {"rear": '<svg><rect fill="#111111" id="chassis-faceplate"/></svg>', "top": "<svg/>"}
    got = run([{"fn": "color", "svg": svg}, {"fn": "color", "svg": other}, {"fn": "color", "svg": {}}])
    assert [g["ok"] for g in got] == ["#8a9299", "#111111", None]


def test_the_viewer_gives_the_body_a_seventh_material_and_picks_a_plan_wall_by_its_normal():
    code = viewer_code()
    assert re.search(r"import \{[^}]*\bPLAN_WALL_INDEX\b[^}]*\bplanWallFace\b[^}]*\} from './section\.js'", code) or \
        re.search(r"import \{[^}]*\bplanWallFace\b[^}]*\bPLAN_WALL_INDEX\b[^}]*\} from './section\.js'", code)
    branch = code[code.index("secBody.arrays)"):code.index("chassis.solid) {")]
    assert "PLAN_WALL_INDEX" in branch and "planWallColor" in branch
    pick = code[code.index("function pick(ev)"):code.index("let hovered = null")]
    assert "PLAN_WALL_INDEX" in pick and "planWallFace" in pick
    # a plan wall is no texture: its hit says the face and no part (its UV is not the face's drawing)
    assert re.search(r"PLAN_WALL_INDEX\)\s*return \{view[^}]*path: null", pick)


def test_level_of_detail_never_reads_the_new_slot():
    code = viewer_code()
    lod = code[code.index("const lodFaces"):code.index("reliefGroup = new THREE.Group()")]
    assert "PLAN_WALL_INDEX" not in lod
    assert [int(m) for m in re.findall(r"\['(?:right|left|top|bottom|front|rear)',\s*(\d),", lod)] == [0, 1, 2, 3, 4, 5]


@needs_node
@pytest.mark.parametrize("name", ["three", "asym"])
def test_the_camera_fit_of_the_plan_body_is_the_plain_boxs(name, tmp_path):
    box, fins, a = built(name)
    script = tmp_path / "fit.mjs"
    script.write_text("""
import {openingView} from %s;
const [W, H, D, positions] = JSON.parse(process.argv[2]);
const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
for (let i = 0; i < positions.length; i += 3) for (let k = 0; k < 3; k++) {
  lo[k] = Math.min(lo[k], positions[i + k]); hi[k] = Math.max(hi[k], positions[i + k]);
}
console.log(JSON.stringify({box: openingView({W, H, D, aspect: 2}),
  body: openingView({W: hi[0] - lo[0], H: hi[1] - lo[1], D: hi[2] - lo[2], aspect: 2})}));
""" % json.dumps((KIT / "camera-fit.js").as_uri()))
    p = subprocess.run(["node", str(script), json.dumps([box["width"], box["height"], box["depth"], a["positions"]])],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout)
    assert got["body"] == pytest.approx(got["box"], rel=1e-9)


# ---- a housing without the key is built as it was ------------------------------------------

def digest(a):
    keys = [k for k in ("positions", "normals", "uvs", "indices", "groups") if k in a]
    blob = json.dumps({k: a[k] for k in keys}, sort_keys=True)
    return {"sha256": hashlib.sha256(blob.encode()).hexdigest(),
            "triangles": len(a["indices"]) // 3 if "indices" in a else len(a["positions"]) // 9,
            "materials": [g["materialIndex"] for g in a["groups"]]}


def as_today_inputs():
    """The published chassis of a device with a section, one with fins, one with fins outside the box:
    the fixtures the earlier orders built."""
    out = {}
    for label, path in (("a stepped housing (section)", "section/lib/devices/fixture/stepped"),
                        ("a finned housing (fins)", "fins/lib/devices/fixture/finned"),
                        ("a finned housing, ribs outside (fins)", "fins/lib/devices/fixture/finned-outside")):
        ch = yaml.safe_load((FIXTURES / path / "device.yaml").read_text())["chassis"]
        out[label] = (ch["section"], ch["width"], ch["height"], ch["depth"], ch.get("fins"))
    return out


def as_today_digests():
    reqs, labels = [], []
    for label, (section, w, h, d, fins) in as_today_inputs().items():
        reqs.append({"section": section, "W": w, "H": h, "D": d, "fins": fins, "plan": None})
        labels.append(label)
    return {label: digest(r["ok"]) for label, r in zip(labels, run(reqs))}


@needs_node
def test_housings_without_the_key_build_the_arrays_and_materials_they_did_before():
    """Golden digests of the arrays `sectionArrays` made on `origin/main` before the plan outline,
    for a stepped housing and two finned ones; the call is the one the viewer makes, with no plan."""
    want = json.loads(AS_TODAY.read_text())
    got = as_today_digests()
    for label in as_today_inputs():
        assert got[label] == want[label], label


@needs_node
def test_a_null_or_empty_plan_is_no_plan():
    section, w, h, d, fins = as_today_inputs()["a finned housing (fins)"]
    base = run([{"section": section, "W": w, "H": h, "D": d, "fins": fins}])[0]["ok"]
    for plan in (None, []):
        again = run([{"section": section, "W": w, "H": h, "D": d, "fins": fins, "plan": plan}])[0]["ok"]
        assert again == base


def published_chassis(ref, tmp):
    dev = LIB / "devices" / ref / "device.yaml"
    out = tmp / ref.replace("/", "-")
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    return json.loads(next(out.glob("*.configs.json")).read_text())["chassis"]


def bevel_digest(ch, tmp):
    script = tmp / "bevel.mjs"
    script.write_text("""
import {bevelledArrays} from %s;
const [polys, W, H, D] = JSON.parse(process.argv[2]);
console.log(JSON.stringify(bevelledArrays(polys, W, H, D)));
""" % json.dumps((KIT / "bevel.js").as_uri()))
    p = subprocess.run(["node", str(script), json.dumps([ch["solid"]["polygons"], ch["w"], ch["h"], ch["d"]])],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-600:]
    return digest(json.loads(p.stdout))


LIBRARY_KINDS = (("a plain box", "cisco/c9300-24p"), ("a bevelled box", "aurcore/ais4001"))


@pytest.mark.heavy
@needs_node
def test_a_plain_box_and_a_bevelled_box_still_take_the_branches_they_took(tmp_path):
    """The published chassis of a plain box and a bevelled one: `sectionBody` says null for each, so
    the viewer's chain is the one that was there, and the bevelled arrays are bevel.js's, unchanged
    (the golden digest was taken before this order)."""
    want = json.loads(AS_TODAY.read_text())
    for label, ref in LIBRARY_KINDS:
        ch = published_chassis(ref, tmp_path)
        assert "plan-outline" not in ch and "section" not in ch
        assert run([{"fn": "body", "chassis": ch, "W": ch["w"], "H": ch["h"], "D": ch["d"]}])[0]["ok"] is None
        if ch.get("solid"):
            assert bevel_digest(ch, tmp_path) == want[label], label
        else:
            assert want[label] == {"box": "sectionBody is null"}
    src = (KIT / "viewer3d.js").read_text()
    assert "bevelledArrays(devIndex.chassis.solid.polygons, W, H, D)" in src
    assert "new THREE.Mesh(new THREE.BoxGeometry(W, H, D), mats)" in src or \
        "new THREE.Mesh(geo, mats)" in src


def write_as_today():
    """Regenerate fixtures/plan_outline/as-today.json from the code as it stands. Only for a change
    that is meant to alter what a housing without a plan outline builds, which this order is not:
        PYTHONPATH=spec/tools:spec/tests python3 spec/tests/test_plan_body_js.py --write-today
    """
    out = dict(as_today_digests())
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for label, ref in LIBRARY_KINDS:
            ch = published_chassis(ref, tmp)
            out[label] = bevel_digest(ch, tmp) if ch.get("solid") else {"box": "sectionBody is null"}
    AS_TODAY.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print("wrote", AS_TODAY)


@pytest.mark.heavy
def test_no_library_device_states_a_plan_outline():
    """(the guard of the earlier order stays; this one only says why this order may not add one: the
    site's copy of the kit has no plan body yet)"""
    for path in libwalk.iter_devices([LIB]):
        text = path.read_text()
        if "plan-outline" in text:
            assert "plan-outline" not in (yaml.safe_load(text).get("chassis") or {}), path


if __name__ == "__main__":
    if "--write-today" in sys.argv:
        write_as_today()
    else:
        print(write_as_today.__doc__)
