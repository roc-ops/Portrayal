"""A chassis with bevelled edges (#735).

A device body was always a box. The AurCore AIS industrial switches are not:
the edges where the flat front meets the finned sides are cut back at about 45
degrees, so the flat front is narrower than the body and the front elevation
has cut corners. `chassis.bevel` names the edges; bevel.py cuts the box once
and both renderers read the result - the 2D drawing projects it, the 3D viewer
builds its mesh from the published polygons.

These pin the solid (closed, convex, the right faces), what each face drawing
shows of it, the faults L126 refuses, and the drawing render.py writes.
"""
import math
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import bevel as bv     # noqa: E402
from portrayal import lint            # noqa: E402
from portrayal import render          # noqa: E402

# The large AIS housing, with the bevels the vendor photographs suggest.
W, H, D = 83.8, 145.0, 110.0
AIS = {"width": W, "height": H, "depth": D, "bevel": [
    {"edges": ["front-left", "front-right"], "size": 11},
    {"edges": ["top-left", "top-right", "bottom-left", "bottom-right"], "size": 6}]}


def edges_of(polys):
    pts = lambda p: [tuple(round(c, 5) for c in q) for q in p["points"]]
    verts = {q for p in polys for q in pts(p)}
    edges = {frozenset((a[i], a[(i + 1) % len(a)])) for p in polys for a in [pts(p)] for i in range(len(a))}
    return verts, edges


# ---- naming -----------------------------------------------------------------

@pytest.mark.parametrize("name,want", [("front-left", "front-left"),
                                       ("left-front", "front-left"),
                                       ("top-rear", "rear-top")])
def test_an_edge_is_named_by_its_two_faces_in_either_order(name, want):
    assert bv.edge_key(name) == want


@pytest.mark.parametrize("name", ["front-rear", "left-right", "front-front", "front", "side-top"])
def test_faces_that_do_not_meet_name_no_edge(name):
    with pytest.raises(bv.BevelError):
        bv.edge_key(name)


def test_there_are_twelve_edges():
    assert len(bv.EDGES) == 12


def test_an_edge_bevelled_twice_is_refused():
    with pytest.raises(bv.BevelError, match="twice"):
        bv.parse({"bevel": [{"edges": ["front-left"], "size": 2},
                            {"edges": ["left-front"], "size": 3}]})


# ---- the solid --------------------------------------------------------------

def test_a_plain_box_is_six_quads():
    polys = bv.solid(W, H, D, {})
    assert sorted(p["face"] for p in polys) == sorted(bv.FACES)
    assert all(len(p["points"]) == 4 for p in polys)


@pytest.mark.parametrize("bevels", [
    {"front-left": 11},
    {"front-left": 11, "front-right": 11},
    bv.parse(AIS),
    {e: 5 for e in bv.EDGES},                      # every edge at once
])
def test_the_solid_is_closed(bevels):
    """V - E + F = 2: a polyhedron with no hole in it, and every edge shared."""
    polys = bv.solid(W, H, D, bevels)
    verts, edges = edges_of(polys)
    assert len(verts) - len(edges) + len(polys) == 2
    assert sum(p["face"] == "bevel" for p in polys) == len(bevels)


def test_each_polygon_winds_counter_clockwise_seen_from_outside():
    for p in bv.solid(W, H, D, bv.parse(AIS)):
        a, b, c = p["points"][:3]
        n = bv._cross(bv._sub(b, a), bv._sub(c, a))
        assert bv._dot(n, p["normal"]) > 0, p["face"]


def test_a_bevel_takes_its_size_off_each_face():
    """The front-left bevel cuts 11 off the front's width and 11 off the left's
    depth, so its cap is 11*sqrt(2) wide."""
    polys = bv.solid(W, H, D, {"front-left": 11})
    cap = next(p for p in polys if p["face"] == "bevel")
    xs = sorted({round(q[0], 6) for q in cap["points"]})
    zs = sorted({round(q[2], 6) for q in cap["points"]})
    assert xs == [-W / 2, round(-W / 2 + 11, 6)]
    assert zs == [round(D / 2 - 11, 6), D / 2]


def test_bevels_that_eat_a_face_are_refused():
    with pytest.raises(bv.BevelError, match="front"):
        bv.solid(W, H, D, {"front-left": 45, "front-right": 45})


# ---- the face drawings ------------------------------------------------------

def test_the_ais_front_has_cut_corners_and_two_strips():
    el = bv.elevation("front", W, H, D, bv.parse(AIS))
    assert len(el["outline"]) == 8                       # four corners cut
    assert {s["edge"] for s in el["strips"]} == {"front-left", "front-right"}
    xs = sorted({round(x, 6) for x, _ in el["flat"]})
    assert xs == [11.0, round(W - 11, 6)]                # the flat is 61.8 wide


def test_a_face_with_no_bevel_on_it_or_through_it_is_its_own_rectangle():
    el = bv.elevation("rear", W, H, D, {"front-left": 11, "front-right": 11})
    assert bv.is_rectangle(el["outline"], W, H)
    assert not el["strips"]


def test_the_side_drawing_puts_the_front_bevel_at_the_front_end():
    """A left side is drawn with the front at the image's right (the kit maps it
    that way), so the front-left strip is the right-most band."""
    el = bv.elevation("left", W, H, D, {"front-left": 11})
    (strip,) = el["strips"]
    assert min(x for x, _ in strip["points"]) == pytest.approx(D - 11)


def test_the_top_drawing_puts_the_front_at_the_bottom():
    el = bv.elevation("top", W, H, D, {"front-left": 11})
    cut = [p for p in el["outline"] if 0 < p[0] < W and 0 < p[1] < D]
    assert not cut
    assert (0.0, round(D - 11, 6)) in [tuple(round(c, 6) for c in p) for p in el["outline"]]


# ---- L126 -------------------------------------------------------------------

def findings(doc):
    with lint.collecting() as found:
        lint.lint_device_bevel("device.yaml", doc, [str(LIB)])
    return [m for m in found.errors + found.warnings if "[L126]" in m]


def test_L126_a_plain_box_is_not_asked_anything():
    assert not findings({"chassis": {"width": W, "height": H, "depth": D}})


def test_L126_refuses_an_edge_that_is_not_one():
    doc = {"chassis": {**AIS, "bevel": [{"edges": ["front-rear"], "size": 2}]}}
    assert findings(doc)


def test_L126_refuses_a_bevelled_face_drawn_at_another_size():
    doc = {"chassis": AIS, "views": {"front": {"size": {"w": 90, "h": 145}}}}
    assert findings(doc)


def test_L126_refuses_a_part_on_a_bevel_and_accepts_one_on_the_flat():
    def doc(at):
        return {"chassis": AIS, "views": {"front": {"panel": {"cutouts": [
            {"id": "c", "at": at, "size": {"w": 10, "h": 10}}]}}}}
    assert findings(doc([2, 50]))         # on the front-left strip
    assert not findings(doc([20, 50]))    # on the flat


# ---- the drawing ------------------------------------------------------------

FRONT_ONLY = {"width": W, "height": H, "depth": D,
              "bevel": [{"edges": ["front-left", "front-right"], "size": 11}]}


def _render(view_name="front", view=None, chassis=AIS):
    d = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
         "chassis": dict(chassis), "views": {view_name: view or {}}}
    out = render.render_view(d, view_name, view or {}, render.Library([str(LIB)]), config={})
    return out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")


def test_the_faceplate_of_a_bevelled_front_is_its_outline():
    svg = _render()
    m = re.search(r'<(?:\w+:)?(path|rect)\b[^>]*\bid="chassis-faceplate"[^>]*>', svg)
    assert m and m.group(1) == "path"
    assert 'd="M0.000,6.000' in m.group(0)


def test_the_strips_are_drawn_where_the_kit_can_find_them():
    svg = _render()
    assert 'id="chassis-bevels"' in svg
    assert svg.count("data-edge=") == 2


def test_a_face_no_bevel_touches_keeps_its_rect():
    """Bevels on the front's two edges leave the rear a plain rectangle; the AIS
    fixture would not, because its depth-wise edges cut the rear's corners too."""
    svg = _render("rear", chassis=FRONT_ONLY)
    assert re.search(r'<(?:\w+:)?rect\b[^>]*\bid="chassis-faceplate"', svg)
    assert "chassis-bevels" not in svg


def test_the_published_solid_is_what_the_drawing_projects():
    pub = bv.published(AIS)
    assert pub and len(pub["polygons"]) == len(bv.solid(W, H, D, bv.parse(AIS)))
    assert bv.published({"width": 1, "height": 1, "depth": 1}) is None


# ---- the kit's mesh ---------------------------------------------------------

NODE = r"""
import { bevelledArrays, boxUV } from '%s';
const solid = JSON.parse(process.argv[2]);
const [W, H, D] = [%s, %s, %s];
const a = bevelledArrays(solid.polygons, W, H, D);
// the area of every material group, and the UV range of the front's
const area = {};
for (const g of a.groups) {
  let s = 0;
  for (let i = g.start; i < g.start + g.count; i += 3) {
    const p = k => a.positions.slice(3 * (i + k), 3 * (i + k) + 3);
    const [p0, p1, p2] = [p(0), p(1), p(2)];
    const u = [p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]], v = [p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]];
    const c = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]];
    s += Math.hypot(...c) / 2;
  }
  area[g.materialIndex] = s;
}
const front = a.groups.find(g => g.materialIndex === 4);
const us = [];
for (let i = front.start; i < front.start + front.count; i++) us.push(a.uvs[2 * i]);
console.log(JSON.stringify({area, umin: Math.min(...us), umax: Math.max(...us),
  corner: boxUV(4, [-W / 2, H / 2, D / 2], W, H, D)}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_kit_mesh_has_the_solid_s_areas_and_box_uvs(tmp_path):
    import json
    script = tmp_path / "t.mjs"
    script.write_text(NODE % ((ROOT / "kit" / "bevel.js").as_uri(), W, H, D))
    pub = bv.published(AIS)
    out = subprocess.run(["node", str(script), json.dumps(pub)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    # the front flat is 61.8 x 145, and BoxGeometry maps x 11..72.8 to u
    assert got["area"]["4"] == pytest.approx((W - 22) * H, rel=1e-4)
    assert got["umin"] == pytest.approx(11 / W, abs=1e-4)
    assert got["umax"] == pytest.approx((W - 11) / W, abs=1e-4)
    # the top-left of the front face is u 0, v 1, as on a box
    assert got["corner"] == pytest.approx([0, 1])
    # six bevel caps, and their total is what the solid says
    caps = sum(bv._area(p["points"], p["normal"]) for p in bv.solid(W, H, D, bv.parse(AIS))
               if p["face"] == "bevel")
    assert got["area"]["6"] == pytest.approx(caps, rel=1e-4)
