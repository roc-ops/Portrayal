"""The 3D body of a housing that states `chassis.section`: the section extruded along the width.

`kit/section.js` turns the end profile into indexed geometry arrays, as `kit/bevel.js`
does for a bevelled box. Every number below is recomputed here from the raw arrays and from
`portrayal.section`, the one place the compiler reads the key; the module is never asked to
check its own arithmetic.

What is held: counts and bounds, normals that point out of the solid, the material of each
facet by the way it faces, UVs that follow BoxGeometry's layout face by face, the left cap as
the mirror of the right (against the outline the compiler draws on the left face), and a
triangulation that covers the polygon exactly. Then the seam in `viewer3d.js`: a section
device takes the new branch and any other device does not, picking maps a facet to the face
it looks toward, and the camera fit is the plain box's.
"""
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest
import yaml

import warmrender
from portrayal import libwalk
from portrayal import section as sec

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
    if (c.fn === 'arrays') return {ok: S.sectionArrays(c.section, c.W, c.H, c.D)};
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


def arrays(section, w=W, h=H, d=D):
    got = run([{"fn": "arrays", "section": [list(p) for p in section], "W": w, "H": h, "D": d}])[0]
    assert "ok" in got, got
    return got["ok"]


@pytest.fixture(scope="module")
def body():
    return arrays(POLY)


# ---- recomputing, never asking the module -------------------------------------------------

def verts(a):
    p = a["positions"]
    return [tuple(p[i:i + 3]) for i in range(0, len(p), 3)]


def tris(a, group=None):
    """(vertex positions) of each triangle in `group` (a material index) or in all."""
    v, idx = verts(a), a["indices"]
    if group is None:
        rng = range(0, len(idx), 3)
    else:
        g = [g for g in a["groups"] if g["materialIndex"] == group]
        rng = range(g[0]["start"], g[0]["start"] + g[0]["count"], 3) if g else range(0)
    return [[v[idx[i + k]] for k in range(3)] for i in rng]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def tri_normal(t):
    n = cross(sub(t[1], t[0]), sub(t[2], t[0]))
    ln = math.hypot(*n)
    return tuple(c / ln for c in n), ln / 2


def to_section_frame(p, d=D, h=H):
    """A viewer-frame point as (x across the depth from the front, y down from the top)."""
    return (d / 2 - p[2], h / 2 - p[1])


def inside(pt, poly):
    """Even-odd point in polygon."""
    x, y = pt
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def solid_has(p, poly=POLY, w=W):
    return abs(p[0]) <= w / 2 and inside(to_section_frame(p), poly)


FACING = {0: (1, 0, 0), 1: (-1, 0, 0), 2: (0, 1, 0), 3: (0, -1, 0), 4: (0, 0, 1), 5: (0, 0, -1)}


def box_uv(mi, p, w=W, h=H, d=D):
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


# ---- counts and bounds --------------------------------------------------------------------

@needs_node
def test_the_fixture_makes_44_triangles_and_72_vertices(body):
    # two caps of n-2 = 10 triangles, and a rectangle (2 triangles) for each of the 12 edges
    assert len(body["indices"]) == 3 * 44
    assert len(body["positions"]) == 3 * 72
    assert len(body["normals"]) == len(body["positions"])
    assert len(body["uvs"]) == 2 * 72
    assert max(body["indices"]) == 71 and min(body["indices"]) == 0


@needs_node
def test_the_bounding_box_is_the_chassis_box(body):
    v = verts(body)
    for axis, half in enumerate((W / 2, H / 2, D / 2)):
        assert min(p[axis] for p in v) == pytest.approx(-half)
        assert max(p[axis] for p in v) == pytest.approx(half)


@needs_node
def test_the_extrusion_runs_along_the_width(body):
    # every vertex is on an end (|x| = W/2): a cap vertex, or a facet's end
    assert {round(abs(p[0]), 6) for p in verts(body)} == {W / 2}


@needs_node
def test_groups_are_contiguous_ascending_and_cover_every_index(body):
    g = body["groups"]
    assert [x["materialIndex"] for x in g] == sorted(x["materialIndex"] for x in g)
    assert [x["materialIndex"] for x in g] == [0, 1, 2, 3, 4, 5]
    pos = 0
    for x in g:
        assert x["start"] == pos and x["count"] % 3 == 0
        pos += x["count"]
    assert pos == len(body["indices"])


# ---- normals, facing, material ------------------------------------------------------------

@needs_node
def test_every_triangle_faces_out_of_the_solid_and_agrees_with_its_stored_normal(body):
    eps = 0.01
    for t in tris(body):
        n, area = tri_normal(t)
        assert area > 0
        c = tuple(sum(p[k] for p in t) / 3 for k in range(3))
        assert not solid_has(tuple(c[k] + eps * n[k] for k in range(3))), (t, n)
        assert solid_has(tuple(c[k] - eps * n[k] for k in range(3))), (t, n)
    idx, norms = body["indices"], body["normals"]
    for i in range(0, len(idx), 3):
        t = [verts(body)[idx[i + k]] for k in range(3)]
        n, _ = tri_normal(t)
        for k in range(3):
            stored = norms[3 * idx[i + k]:3 * idx[i + k] + 3]
            assert stored == pytest.approx(n, abs=1e-9)


@needs_node
def test_each_facet_takes_the_material_of_the_face_it_looks_toward(body):
    for mi in range(6):
        for t in tris(body, mi):
            n, _ = tri_normal(t)
            assert n == pytest.approx(FACING[mi], abs=1e-9), (mi, n)


@needs_node
def test_the_fixture_has_three_facets_toward_each_long_face_and_one_cap_each_end(body):
    # edges of the fixture: 3 up, 3 down, 3 toward the front, 3 toward the rear
    for mi in (2, 3, 4, 5):
        assert len(tris(body, mi)) == 6
    for mi in (0, 1):
        assert len(tris(body, mi)) == 10


@needs_node
def test_a_facet_is_a_rectangle_as_long_as_its_edge_and_as_wide_as_the_box(body):
    # the area toward each long face is the sum of (edge length) x W over the edges that look there
    want = {2: 0, 3: 0, 4: 0, 5: 0}
    for (x0, y0), (x1, y1) in zip(POLY, POLY[1:] + POLY[:1]):
        dx, dy = x1 - x0, y1 - y0
        ny, nx = -dx, dy          # outward normal (dy, -dx) = (nx, ny) in the section frame
        mi = 2 if ny < 0 else 3 if ny > 0 else (5 if nx > 0 else 4)
        want[mi] += math.hypot(dx, dy) * W
    for mi, area in want.items():
        assert sum(tri_normal(t)[1] for t in tris(body, mi)) == pytest.approx(area)


# ---- UVs ----------------------------------------------------------------------------------

@needs_node
def test_every_vertex_has_the_uv_boxgeometry_gives_that_point_on_its_face(body):
    uvs, v = body["uvs"], verts(body)
    for g in body["groups"]:
        for i in range(g["start"], g["start"] + g["count"]):
            k = body["indices"][i]
            assert uvs[2 * k:2 * k + 2] == pytest.approx(box_uv(g["materialIndex"], v[k]), abs=1e-9)


@needs_node
def test_the_uvs_are_inside_0_to_1(body):
    assert min(body["uvs"]) >= -1e-9 and max(body["uvs"]) <= 1 + 1e-9


@needs_node
def test_a_top_facet_reads_the_top_texture_along_its_length_and_depth(body):
    # the lower step of the top (x 250..281 at y = 132): u runs the whole length, v the depth
    # from the front at v = 1 - ... (the top's own layout: front at the bottom of the image)
    seen = set()
    for t in tris(body, 2):
        for p in t:
            sx, sy = to_section_frame(p)
            u, v = box_uv(2, p)
            assert v == pytest.approx(sx / D)       # the depth position across the polygon's x
            seen.add((round(sx, 6), round(sy, 6)))
    assert (250.0, 132.0) in seen and (281.0, 132.0) in seen and (14.0, 132.0) in seen


@needs_node
def test_a_front_or_rear_facet_reads_its_texture_at_its_own_height_and_length(body):
    for mi in (4, 5):
        for t in tris(body, mi):
            for p in t:
                u, v = box_uv(mi, p)
                assert 1 - v == pytest.approx((H / 2 - p[1]) / H)       # height down from the top
                assert u == pytest.approx((p[0] + W / 2) / W if mi == 4 else (W / 2 - p[0]) / W)


@needs_node
def test_the_caps_take_the_polygon_point_in_the_end_face_frame(body):
    v, uvs = verts(body), body["uvs"]
    g = {x["materialIndex"]: x for x in body["groups"]}
    # right cap: u = x / depth, v = 1 - y / height, the right face's drawing frame
    for i in range(g[0]["start"], g[0]["start"] + g[0]["count"]):
        k = body["indices"][i]
        sx, sy = to_section_frame(v[k])
        assert uvs[2 * k] == pytest.approx(sx / D) and uvs[2 * k + 1] == pytest.approx(1 - sy / H)


@needs_node
def test_the_left_cap_is_the_mirror_in_x_of_the_right_and_matches_the_left_outline(body):
    v, uvs, idx = verts(body), body["uvs"], body["indices"]
    g = {x["materialIndex"]: x for x in body["groups"]}

    def cap(mi):
        return {idx[i] for i in range(g[mi]["start"], g[mi]["start"] + g[mi]["count"])}

    right, left = cap(0), cap(1)
    assert {(round(-v[k][0], 6), round(v[k][1], 6), round(v[k][2], 6)) for k in left} == \
           {(round(v[k][0], 6), round(v[k][1], 6), round(v[k][2], 6)) for k in right}
    # the texture lands the right way round: the left face is drawn with the front at its right
    # edge, so u runs the other way, v is the same
    by_pos = {(round(v[k][1], 6), round(v[k][2], 6)): k for k in right}
    for k in left:
        r = by_pos[(round(v[k][1], 6), round(v[k][2], 6))]
        assert uvs[2 * k] == pytest.approx(1 - uvs[2 * r])
        assert uvs[2 * k + 1] == pytest.approx(uvs[2 * r + 1])
    # the compiler draws the left face as this outline in the left face's own frame
    drawn = sorted((round(x, 4), round(y, 4)) for x, y in sec.outline("left", POLY, D))
    got = sorted((round(uvs[2 * k] * D, 4), round((1 - uvs[2 * k + 1]) * H, 4)) for k in left)
    assert sorted(set(got)) == drawn
    # and the right cap is the polygon as stated
    got_r = sorted(set((round(uvs[2 * k] * D, 4), round((1 - uvs[2 * k + 1]) * H, 4)) for k in right))
    assert got_r == sorted((round(x, 4), round(y, 4)) for x, y in POLY)


# ---- the triangulation --------------------------------------------------------------------

def area(poly):
    return abs(sec.area2(poly)) / 2


def cover_count(point, flat):
    def side(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    n = 0
    for a, b, c in flat:
        s = (side(point, a, b), side(point, b, c), side(point, c, a))
        if all(x > 0 for x in s) or all(x < 0 for x in s):
            n += 1
    return n


SHAPES = {
    "the stepped fixture": POLY,
    "an L": [(0, 0), (40, 0), (40, 20), (20, 20), (20, 60), (0, 60)],
    "a staircase": [(0, 0), (60, 0), (60, 20), (40, 20), (40, 40), (20, 40), (20, 60), (0, 60)],
    "a staircase started at another vertex": [(40, 40), (20, 40), (20, 60), (0, 60), (0, 0), (60, 0), (60, 20), (40, 20)],
    "a rectangle": [(0, 0), (30, 0), (30, 50), (0, 50)],
}


@needs_node
@pytest.mark.parametrize("name", list(SHAPES))
def test_a_cap_covers_the_polygon_exactly(name):
    poly = [tuple(map(float, p)) for p in SHAPES[name]]
    w, d = 20.0, max(p[0] for p in poly)
    h = max(p[1] for p in poly)
    a = arrays(poly, w, h, d)
    for mi in (0, 1):
        flat = []
        for t in tris(a, mi):
            tri = [tuple(to_section_frame(p, d, h)) for p in t]
            flat.append(tri)
        # equal area, and a fine grid: every sample inside is in exactly one triangle, every sample outside in none
        assert sum(area(t) for t in flat) == pytest.approx(area(poly))
        xs = [i * 1.37 + 0.31 for i in range(int(d / 1.37))]
        ys = [j * 1.19 + 0.23 for j in range(int(h / 1.19))]
        for x in xs:
            for y in ys:
                assert cover_count((x, y), flat) == (1 if inside((x, y), poly) else 0), (name, x, y)
    # a cap uses only the polygon's own vertices, so it shares every edge with a facet
    assert {(round(p[1], 6), round(p[2], 6)) for t in tris(a, 0) for p in t} == \
           {(round(h / 2 - y, 6), round(d / 2 - x, 6)) for x, y in poly}


@needs_node
def test_a_polygon_wound_the_other_way_or_with_a_slanted_edge_is_refused():
    for bad in ([(0, 0), (0, 50), (30, 50), (30, 0)], [(0, 0), (30, 0), (30, 50), (5, 55)]):
        got = run([{"fn": "arrays", "section": [list(p) for p in bad], "W": 20, "H": 55, "D": 30}])[0]
        assert "error" in got, got


# ---- the seam: sectionBody ----------------------------------------------------------------

def body_of(chassis):
    return run([{"fn": "body", "chassis": chassis, "W": W, "H": H, "D": D}])[0]


@needs_node
def test_a_chassis_with_a_section_gets_the_arrays_and_one_without_gets_none():
    got = body_of({**CHASSIS})
    assert got["ok"]["arrays"]["groups"] and "refused" not in got["ok"]
    for plain in (None, {}, {"w": W, "h": H, "d": D}, {"section": []}):
        assert body_of(plain)["ok"] is None


@needs_node
@pytest.mark.parametrize("extra", [{"solid": {"polygons": []}}, {"bevel": [{"edges": ["front-left"], "size": 5}]},
                                   {"rounded": 4}, {"shell": "sheet"}, {"halves": {"hinge": "rear"}}])
def test_a_section_with_another_body_key_falls_back_with_a_reason(extra):
    got = body_of({**CHASSIS, **extra})["ok"]
    assert got["refused"] and "arrays" not in got


@needs_node
def test_a_section_that_cannot_be_built_is_refused_not_thrown():
    got = body_of({**CHASSIS, "section": [[0, 0], [10, 10], [0, 10]]})["ok"]
    assert got["refused"]


def viewer_code():
    src = (KIT / "viewer3d.js").read_text()
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?<![:'\"])//[^\n]*", "", src)


def test_the_viewer_takes_the_section_branch_before_the_bevelled_and_plain_boxes():
    code = viewer_code()
    assert re.search(r"import \{[^}]*\bsectionBody\b[^}]*\} from './section\.js'", code)
    i = code.index("sectionBody(devIndex")
    branch = code.index("} else if (secBody && secBody.arrays)")
    assert i < branch < code.index("chassis.solid) {", branch)
    assert branch < code.index("new THREE.BoxGeometry(W, H, D), mats", branch)
    # the refusal is spoken, then the old branches decide
    assert "console.warn" in code[i:branch]


def test_the_section_mesh_keeps_the_six_face_materials_in_face_of_index_order():
    code = viewer_code()
    branch = code[code.index("secBody.arrays)"):code.index("chassis.solid) {")]
    assert "new THREE.Mesh(geo, mats)" in branch or "new THREE.Mesh(geo, [...mats" in branch
    assert "FACE_OF_INDEX" not in branch      # the order is the one table, used by picking as before
    assert re.search(r"FACE_OF_INDEX = \['right', 'left', 'top', 'bottom', 'front', 'rear'\]", code)


@needs_node
def test_picking_maps_a_hit_facet_to_the_face_it_looks_toward(body):
    face_of_index = ['right', 'left', 'top', 'bottom', 'front', 'rear']
    looks = {'right': (1, 0, 0), 'left': (-1, 0, 0), 'top': (0, 1, 0), 'bottom': (0, -1, 0),
             'front': (0, 0, 1), 'rear': (0, 0, -1)}
    for g in body["groups"]:
        view = face_of_index[g["materialIndex"]]
        for t in tris({**body, "groups": [g]}, g["materialIndex"]):
            assert tri_normal(t)[0] == pytest.approx(looks[view], abs=1e-9)


def test_the_camera_fit_reads_the_bounds_and_they_are_the_boxs():
    """camera-fit takes the box's W, H, D; the body's bounds are those, so the fit is the plain box's."""
    code = viewer_code()
    assert "openOn(W, H, D)" in code
    assert "sectionBody(devIndex" not in code[code.index("openOn(W, H, D)") - 400:code.index("openOn(W, H, D)")]


@needs_node
def test_fit_for_a_section_chassis_is_the_plain_boxs(tmp_path):
    script = tmp_path / "fit.mjs"
    script.write_text("""
import {openingView} from %s;
import {sectionArrays} from %s;
const [W, H, D, section] = JSON.parse(process.argv[2]);
const a = sectionArrays(section, W, H, D);
const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
for (let i = 0; i < a.positions.length; i += 3) for (let k = 0; k < 3; k++) {
  lo[k] = Math.min(lo[k], a.positions[i + k]); hi[k] = Math.max(hi[k], a.positions[i + k]);
}
const bw = hi[0] - lo[0], bh = hi[1] - lo[1], bd = hi[2] - lo[2];
console.log(JSON.stringify({box: openingView({W, H, D, aspect: 2}), body: openingView({W: bw, H: bh, D: bd, aspect: 2})}));
""" % (json.dumps((KIT / "camera-fit.js").as_uri()), json.dumps((KIT / "section.js").as_uri())))
    p = subprocess.run(["node", str(script), json.dumps([W, H, D, [list(q) for q in POLY]])],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout)
    assert got["body"] == pytest.approx(got["box"])


# ---- a device that states no section is built as it was ------------------------------------

# a plain box, a bevelled one and a sheet body: three kinds of body the viewer already builds
AS_TODAY = ["cisco/c9300-24p", "aurcore/ais4001", "fs/cmh-6dr1u"]


@pytest.mark.heavy
def test_no_library_device_states_a_section():
    paths = libwalk.iter_devices([LIB])
    assert len(paths) > 100
    for path in paths:
        text = path.read_text()
        if "section" in text:         # only a file that says the word can state the key
            assert "section" not in (yaml.safe_load(text).get("chassis") or {}), path


@pytest.mark.heavy
@needs_node
def test_three_devices_of_other_kinds_are_built_as_they_were(tmp_path):
    """The published chassis of a plain box, a bevelled box and a sheet body: sectionBody
    answers None for each, so the viewer's chain is the one that was there. The arrays the
    bevelled one makes are the ones bevel.js makes, untouched by this change."""
    kinds = []
    for n, ref in enumerate(AS_TODAY):
        dev = LIB / "devices" / ref / "device.yaml"
        out = tmp_path / f"o{n}"
        r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB), "--out", str(out)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-600:]
        cfg = json.loads(next(out.glob("*.configs.json")).read_text())
        ch = cfg["chassis"]
        kinds.append("solid" if ch.get("solid") else "sheet" if ch.get("shell") == "sheet" else "box")
        assert body_of(ch)["ok"] is None, dev
        assert "section" not in ch
    assert kinds == ["box", "solid", "sheet"]
    # the bevelled body is bevel.js's output: the module the section code leaves alone
    src = (KIT / "viewer3d.js").read_text()
    assert "bevelledArrays(devIndex.chassis.solid.polygons, W, H, D)" in src
