"""The open state and the seating of a housing that states `chassis.plan-outline`.

A housing that states `section`, `halves` and `plan-outline` opens as two halves, and each half is the
body the plan leaves of it (`kit/plan-body.js`, `kit/section.js` `splitSection`) on its side of the seam.
Every number below is recomputed here, from the polygons of the fixture and from the definitions
(shoelace areas, the divergence theorem, a hand-turned lid), never by asking the module to check its own
arithmetic.

What is held: each half watertight with and without ribs, for a seam inside a band and one exactly on a
band edge; the two halves' volumes adding up to the closed body's; each half's bounds the bounds of its
clipped positions; each half's rim cap the polygon of the band on its own side of the seam, in the plain
slot and facing the other half, the rib's cut face in the invisible slot; the closed body's arrays as the
earlier order built them; the lid turning about the section's hinge line with its lobes; a part seated on
the surface the plan leaves under it; and a housing without the key opening and seating as it did.
"""
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest
import yaml

from test_plan_body_js import THREE, THREE_FINS, edges, volume
from test_section_body_js import tris, verts
from test_section_split_js import hand_corners, rot_x, with_seam

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
FIXTURES = ROOT / "spec/tests/fixtures"
TODAY = FIXTURES / "plan_outline/open-as-today.json"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

W, H, D = THREE["width"], THREE["height"], THREE["depth"]
SEAM, PLAN_WALL = 6, 7

SCRIPT = """
import * as S from %s;
import * as Hs from %s;
const reqs = JSON.parse(process.argv[2]);
console.log(JSON.stringify(reqs.map(r => {
  try {
    const c = r.chassis;
    if (r.fn === 'split') return {ok: S.splitSection(r.section, r.W, r.H, r.D, r.fins, r.halves, r.plan)};
    if (r.fn === 'closed') return {ok: S.sectionArrays(r.section, r.W, r.H, r.D, r.fins, undefined, r.plan)};
    if (r.fn === 'open') {
      const cut = S.sectionHalves(c, r.W, r.H, r.D);
      const plan = Hs.housingPlan(c.halves, {w: r.W, h: r.H, d: r.D}, cut && cut.split);
      return {ok: {cut, plan, bounds: plan ? Hs.openBounds(plan) : null,
                   lid: plan && r.corners ? r.corners.map(p => Hs.lidPoint(plan, p)) : null}};
    }
    if (r.fn === 'seats') {
      const poly = S.sectionSeat(c, r.W, r.H, r.D);
      if (!poly) return {ok: null};
      const fins = S.seatFins(c, r.W, r.H, r.D);
      const plan = S.seatPlan ? S.seatPlan(c, r.W, r.H, r.D) : null;
      return {ok: r.points.map(([face, p]) => S.seatPoint(poly, face, p, r.W, r.H, r.D, fins, plan))};
    }
    return {error: 'unknown fn'};
  } catch (e) { return {error: String(e.message || e)}; }
})));
"""


def run(reqs):
    with tempfile.TemporaryDirectory() as tmp:
        script = pathlib.Path(tmp) / "t.mjs"
        script.write_text(SCRIPT % (json.dumps((KIT / "section.js").as_uri()), json.dumps((KIT / "housing.js").as_uri())))
        p = subprocess.run(["node", str(script), json.dumps(reqs)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:]
    return json.loads(p.stdout)


def one(req):
    got = run([req])[0]
    assert "ok" in got, got
    return got["ok"]


def split(box, stands, fins=None, outer="top", hinge="rear", plan=True):
    return one({"fn": "split", "section": box["section"], "W": box["width"], "H": box["height"], "D": box["depth"],
                "fins": fins, "halves": with_seam(stands, outer, hinge),
                "plan": box["plan-outline"] if plan else None})


def closed(box, fins=None):
    return one({"fn": "closed", "section": box["section"], "W": box["width"], "H": box["height"],
                "D": box["depth"], "fins": fins, "plan": box["plan-outline"]})


# ---- the boxes ---------------------------------------------------------------------------------------------

def band_split(heights_at=143.0):
    """The three-band box with its flange band cut in two at a height that is no row of the section: the
    upper piece keeps the flange's lobes, the lower has none (the two points of each lobe left out), so the
    two bands have different polygons and a seam there has two different rims."""
    bands = json.loads(json.dumps(THREE["plan-outline"]))
    flange = bands[1]
    plain = [p for p in flange["points"] if p not in ([204.0, 0.0], [276.0, 0.0], [600.0, 112.0], [600.0, 168.0])]
    assert len(plain) == len(flange["points"]) - 4
    upper = {"heights": [132.0, heights_at], "points": flange["points"]}
    lower = {"heights": [heights_at, 155.0], "points": plain}
    return {**THREE, "plan-outline": [bands[0], upper, lower, bands[2]]}


SPLIT = band_split()
# a seam inside the flange band, and one exactly on a band's edge that the section has no row at
CASES = {
    "inside a band": (THREE, 144.0),
    "on a band edge": (SPLIT, 143.0),
}
RIBS = {"no ribs": None, "ribs": THREE_FINS}


def shoelace(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def cap_triangles(a, group, y):
    """The triangles of `group` lying flat at height y."""
    return [t for t in tris(a, group) if all(abs(p[1] - y) < 1e-6 for p in t)]


def area(t):
    u = [t[1][i] - t[0][i] for i in range(3)]
    v = [t[2][i] - t[0][i] for i in range(3)]
    c = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return math.sqrt(sum(x * x for x in c)) / 2


def bounds(a):
    pos = a["positions"]
    return [min(pos[i::3]) for i in range(3)], [max(pos[i::3]) for i in range(3)]


# ---- 1. the halves cut by the plan ------------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("ribs", list(RIBS))
@pytest.mark.parametrize("case", list(CASES))
def test_each_half_is_watertight_every_edge_shared_by_two_triangles_once_each_way(case, ribs):
    box, stands = CASES[case]
    s = split(box, stands, RIBS[ribs])
    for name in ("base", "lid"):
        e = edges(s[name]["arrays"])
        bad = [(k, n) for k, n in e.items() if n != 1 or e.get((k[1], k[0])) != 1]
        assert not bad, f"{name}: {len(bad)} edges are not shared by exactly two triangles; first {bad[:3]}"


@needs_node
@pytest.mark.parametrize("ribs", list(RIBS))
@pytest.mark.parametrize("case", list(CASES))
def test_the_two_halves_add_up_to_the_closed_body(case, ribs):
    box, stands = CASES[case]
    s = split(box, stands, RIBS[ribs])
    both = volume(s["base"]["arrays"]) + volume(s["lid"]["arrays"])
    assert both == pytest.approx(volume(closed(box, RIBS[ribs])), rel=1e-6)


@needs_node
def test_the_halves_follow_the_plan_not_the_extrusion():
    """Seam 100 mm down is inside the upper casting, whose plan polygon runs from x = 20 to 580 while the
    extruded section runs the whole 600: the base is narrower than the extrusion would make it."""
    s = split(THREE, 100.0)
    lo, hi = bounds(s["base"]["arrays"])
    assert (lo[0], hi[0]) == pytest.approx((-280.0, 280.0))
    assert PLAN_WALL in {g["materialIndex"] for g in s["base"]["arrays"]["groups"]}
    extruded = split(THREE, 100.0, plan=False)
    assert bounds(extruded["base"]["arrays"])[0][0] == pytest.approx(-300.0)


@needs_node
@pytest.mark.parametrize("stands", [100.0, 144.0, 200.0])
def test_each_halfs_bounds_are_the_bounds_of_its_clipped_positions(stands):
    s = split(THREE, stands, THREE_FINS)
    for name in ("base", "lid"):
        lo, hi = bounds(s[name]["arrays"])
        assert s[name]["min"] == pytest.approx(lo) and s[name]["max"] == pytest.approx(hi)
        assert s[name]["size"] == pytest.approx([b - a for a, b in zip(lo, hi)])
        assert s[name]["center"] == pytest.approx([(a + b) / 2 for a, b in zip(lo, hi)])
    # the seam is the half's own face: the base ends at it from above, the lid from below
    assert bounds(s["base"]["arrays"])[0][1] == pytest.approx(H / 2 - stands)
    assert bounds(s["lid"]["arrays"])[1][1] == pytest.approx(H / 2 - stands)


@needs_node
def test_the_pivot_is_still_the_hinge_faces_line_of_the_section_at_the_seam_row():
    for stands, z in ((144.0, D / 2 - 281.0), (100.0, D / 2 - 250.0)):
        s = split(THREE, stands)
        assert s["pivot"] == pytest.approx([0.0, 0.0 + (144.0 - stands), z])


# ---- 2. the visible rim caps, open state only ---------------------------------------------------------------

@needs_node
def test_each_half_has_its_cap_in_the_plain_slot_flat_at_the_seam_and_facing_the_other_half():
    s = split(THREE, 144.0)
    for name, normal in (("base", -1.0), ("lid", 1.0)):
        a = s[name]["arrays"]
        mats = [g["materialIndex"] for g in a["groups"]]
        assert SEAM not in mats, "no rib crosses this seam: nothing is left for the invisible slot"
        caps = cap_triangles(a, PLAN_WALL, 0.0)
        assert caps, name
        for t in caps:                                    # wound to agree with the way it faces
            u = [t[1][i] - t[0][i] for i in range(3)]
            v = [t[2][i] - t[0][i] for i in range(3)]
            ny = u[2] * v[0] - u[0] * v[2]
            assert ny * normal > 0, (name, t)


@needs_node
def test_the_cap_is_the_polygon_of_the_band_on_the_halfs_own_side():
    """Seam 144 is inside the flange band, whose polygon covers the section's whole depth at its rows: both
    caps are that polygon (shoelace, by hand from the fixture), lobes included."""
    flange = shoelace([tuple(p) for p in THREE["plan-outline"][1]["points"]])
    s = split(THREE, 144.0)
    for name in ("base", "lid"):
        got = sum(area(t) for t in cap_triangles(s[name]["arrays"], PLAN_WALL, 0.0))
        assert got == pytest.approx(flange, rel=1e-9), name


@needs_node
def test_a_seam_on_a_band_edge_gives_each_half_the_polygon_of_the_band_on_its_side():
    """The flange band is cut at 143 into an upper band with its two lobes and a lower one without. Each lobe
    is a trapezoid: the rear one is (72 + 88) / 2 x 8 = 640 and the end one (56 + 72) / 2 x 10 = 640. The
    base is the upper band, the lid the lower, and their caps differ by exactly the lobes."""
    s = split(SPLIT, 143.0)
    upper = shoelace([tuple(p) for p in SPLIT["plan-outline"][1]["points"]])
    lower = shoelace([tuple(p) for p in SPLIT["plan-outline"][2]["points"]])
    assert upper - lower == pytest.approx(1280.0)
    y = H / 2 - 143.0
    assert sum(area(t) for t in cap_triangles(s["base"]["arrays"], PLAN_WALL, y)) == pytest.approx(upper, rel=1e-9)
    assert sum(area(t) for t in cap_triangles(s["lid"]["arrays"], PLAN_WALL, y)) == pytest.approx(lower, rel=1e-9)


RIBBED = {
    "width": 60.0, "height": 40.0, "depth": 50.0,
    "section": [[10, 0], [40, 0], [40, 5], [50, 5], [50, 40], [0, 40], [0, 5], [10, 5]],
    "plan-outline": [{"heights": [0.0, 40.0], "points": [[0, 0], [60, 0], [60, 50], [0, 50]]}],
}
RIBBED_FINS = [{"on": "top", "span": [5.0, 55.0], "core": 15.0, "rib": 4.0, "gap": 4.0}]


@needs_node
def test_a_rib_the_seam_crosses_is_capped_in_the_invisible_slot_and_the_casting_in_the_plain_one():
    """The top field cuts the casting back 15 mm over x 10 to 40 and the wings either side stay; six ribs of
    4 mm stand on the cut surface and a seam 8 down runs through the wings and every rib. The wings' cap,
    two of 10 x 60, is visible (slot 7); the six rib sections, 4 x 30 each, are slot 6, which is not drawn."""
    s = split(RIBBED, 8.0, RIBBED_FINS)
    a = s["base"]["arrays"]
    y = 40.0 / 2 - 8.0
    assert sum(area(t) for t in cap_triangles(a, PLAN_WALL, y)) == pytest.approx(60.0 * 20.0, rel=1e-9)
    assert sum(area(t) for t in cap_triangles(a, SEAM, y)) == pytest.approx(6 * 4.0 * 30.0, rel=1e-9)
    e = edges(a)
    assert not [k for k, n in e.items() if n != 1 or e.get((k[1], k[0])) != 1]


@needs_node
def test_a_cap_is_never_coincident_with_a_face_of_the_closed_body():
    """The closed body is one mesh with no face at the seam where the seam is inside a band; the caps are the
    halves' own, and the halves are only built for the open state."""
    c = closed(THREE)
    assert not [t for g in range(8) for t in cap_triangles(c, g, 0.0)]
    c = closed(THREE, THREE_FINS)
    assert not [t for g in range(8) for t in cap_triangles(c, g, 0.0)]
    assert SEAM not in {g["materialIndex"] for g in c["groups"]}


def digest(a):
    blob = json.dumps({k: a[k] for k in ("positions", "normals", "uvs", "indices", "groups")}, sort_keys=True)
    return {"sha256": hashlib.sha256(blob.encode()).hexdigest(), "triangles": len(a["indices"]) // 3,
            "materials": [g["materialIndex"] for g in a["groups"]]}


# ---- a housing without the key opens and seats as it did -----------------------------------------------------

def chassis_of(path):
    return yaml.safe_load((FIXTURES / path / "device.yaml").read_text())["chassis"]


def no_fins(ch):
    return {k: v for k, v in ch.items() if k != "fins"}


def devices():
    stepped = chassis_of("opening-section/lib/devices/fixture/stepped-open")
    outside = chassis_of("fins/lib/devices/fixture/finned-outside")
    outside = {**outside, "halves": {"base": {"outer": "top", "stands": 20.0},
                                     "lid": {"hinge": "rear", "angle": 110.0, "stands": 20.0}}}
    clam = chassis_of("halves/lib/devices/fixture/clam")
    return {"section and halves": no_fins(stepped), "section, halves and fins": stepped,
            "fins, ribs outside the box, halves": outside, "neither (a plain box that opens)": clam}


def seat_points(ch):
    w, h, d = ch["width"], ch["height"], ch["depth"]
    out = []
    for i in range(11):
        f = i / 10
        out += [["top", [-w / 2 + f * w, h / 2, d / 2 - f * d]], ["bottom", [-w / 2 + f * w, -h / 2, d / 2 - f * d]],
                ["front", [0.0, h / 2 - f * h, d / 2]], ["rear", [0.0, h / 2 - f * h, -d / 2]]]
    return out


def open_state(ch):
    """What the viewer asks of a chassis that opens, and where it seats parts: numbers only."""
    w, h, d = ch["width"], ch["height"], ch["depth"]
    got = one({"fn": "open", "chassis": ch, "W": w, "H": h, "D": d,
               "corners": [[x * 10, y * 10, z * 10] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]})
    cut = got["cut"]
    parts = None
    if cut and cut.get("split"):
        sp = cut["split"]
        parts = {n: {"arrays": digest(sp[n]["arrays"]), "min": sp[n]["min"], "max": sp[n]["max"],
                     "center": sp[n]["center"], "body": sp[n]["body"]} for n in ("base", "lid")}
        parts.update(seam=sp["seam"], pivot=sp["pivot"])
    plan = json.loads(json.dumps(got["plan"]))
    if plan and plan.get("split"):
        plan["split"] = "(the parts above)"
    seats = one({"fn": "seats", "chassis": ch, "W": w, "H": h, "D": d, "points": seat_points(ch)})
    return {"parts": parts, "plan": plan, "bounds": got["bounds"], "lid": got["lid"], "seats": seats}


def closed_plan_digests():
    return {"the three-band box": digest(closed(THREE)), "the three-band box with ribs": digest(closed(THREE, THREE_FINS))}


@needs_node
@pytest.mark.parametrize("label", list(devices()))
def test_a_housing_without_the_key_opens_and_seats_as_it_did(label):
    """Golden numbers taken from `origin/main` before this order: the halves' arrays (sha256), bounds, pivot,
    the open state's plan and camera box, the lid's corners and the seat of a part at eleven places on
    each of the four faces. A section with halves, one with fins too, a finned one with its ribs outside
    the box, and a plain box that opens."""
    want = json.loads(TODAY.read_text())["devices"][label]
    assert json.loads(json.dumps(open_state(devices()[label]))) == want


@needs_node
def test_the_closed_plan_body_is_the_arrays_the_earlier_order_built():
    want = json.loads(TODAY.read_text())["closed"]
    assert closed_plan_digests() == want


# ---- 3. bounds, pivot and the lid ----------------------------------------------------------------------------

def opened(angle, stands=144.0):
    ch = {**THREE, "halves": {"base": {"outer": "top", "stands": stands},
                              "lid": {"hinge": "rear", "angle": angle, "stands": H - stands}}}
    return one({"fn": "open", "chassis": ch, "W": W, "H": H, "D": D,
                "corners": [[x * 10, y * 10, z * 10] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]}), ch


@needs_node
@pytest.mark.parametrize("angle", [90.0, 110.0, 180.0])
@pytest.mark.parametrize("stands", [100.0, 144.0])
def test_the_open_bounds_hold_the_clipped_base_and_the_turned_lid(angle, stands):
    got, ch = opened(angle, stands)
    sp = got["cut"]["split"]
    corners = []
    blo, bhi = sp["base"]["min"], sp["base"]["max"]
    corners += [(x, y, z) for x in (blo[0], bhi[0]) for y in (blo[1], bhi[1]) for z in (blo[2], bhi[2])]
    corners += hand_corners(sp, angle)
    lo, hi = got["bounds"]["min"], got["bounds"]["max"]
    for i in range(3):
        assert lo[i] == pytest.approx(min(c[i] for c in corners), abs=1e-6)
        assert hi[i] == pytest.approx(max(c[i] for c in corners), abs=1e-6)
    # with the seam in the upper casting the base is the plan's 560 wide and the lid, flange and lobes, 600
    if stands == 100.0:
        assert sp["base"]["size"][0] == pytest.approx(560.0) and sp["lid"]["size"][0] == pytest.approx(600.0)
    assert got["plan"]["lid"]["pivot"] == pytest.approx(sp["pivot"])


@needs_node
@pytest.mark.parametrize("angle", [90.0, 110.0, 180.0])
def test_a_lobe_and_a_rounded_corner_of_the_lid_swing_with_it(angle):
    """lidPoint turns a point of the lid about the pivot line by the angle: the tip of the end lobe (plan
    600, 112) and a vertex of the flange's rounded corner (plan 24, 8) of the lid half go where a hand
    turn about the hinge line puts them."""
    got, ch = opened(angle)
    sp = got["cut"]["split"]
    lid = sp["lid"]["arrays"]
    pos = lid["positions"]
    def vertex(px, py):
        for i in range(0, len(pos), 3):
            if abs(pos[i] - (px - W / 2)) < 1e-4 and abs(pos[i + 2] - (py - D / 2)) < 1e-4:
                return (pos[i], pos[i + 1], pos[i + 2])
        raise AssertionError(f"no lid vertex at plan {px}, {py}")
    cc = sp["lid"]["center"]
    for px, py in ((600.0, 112.0), (24.0, 8.0)):
        v = vertex(px, py)
        local = [v[k] - cc[k] for k in range(3)]
        got_pt = one({"fn": "open", "chassis": ch, "W": W, "H": H, "D": D, "corners": [local]})["lid"][0]
        assert got_pt == pytest.approx(rot_x(v, sp["pivot"], angle), abs=1e-5)


# ---- 4. seating on the plan -----------------------------------------------------------------------------------

def seat(face, px, py, row=None, chassis=None):
    """The seat of a part at plan (px, py) on a face: the viewer's frame is x - 300 across and z = py - 140.5."""
    ch = chassis or THREE
    p = [px - W / 2, (H / 2 - row) if row is not None else (H / 2 if face == "top" else -H / 2), py - D / 2]
    return one({"fn": "seats", "chassis": ch, "W": W, "H": H, "D": D, "points": [[face, p]]})[0]


@needs_node
def test_a_part_over_the_flange_band_stands_on_the_flange():
    # plan (300, 15) is 15 from the rear, 266 from the front: only the flange (rows 132 to 155) is there
    assert seat("top", 300.0, 15.0) == pytest.approx(-132.0)
    assert seat("bottom", 300.0, 15.0) == pytest.approx(155.0 - H)


@needs_node
def test_a_part_over_the_upper_castings_top_stands_on_the_plane():
    assert seat("top", 300.0, 150.0) == pytest.approx(0.0)
    assert seat("bottom", 300.0, 140.0) == pytest.approx(0.0)


@needs_node
def test_a_part_over_a_rounded_corner_stands_on_the_surface_that_exists_there():
    """Plan (22, 33) is in the flange's corner but outside the upper casting's smaller one (its arc passes
    through (21.61, 37) and (26, 32.61)): the extrusion would put the casting's top under it, the plan
    leaves the flange's, 132 down."""
    assert seat("top", 22.0, 33.0) == pytest.approx(-132.0)
    # a part on the rear wall of the upper casting 100 down, at x = 24: the arc's chord, y = 34.61
    assert seat("rear", 24.0, 0.0, row=100.0) == pytest.approx(-34.61, abs=1e-3)
    assert seat("front", 24.0, 0.0, row=100.0) == pytest.approx(263.39 - D, abs=1e-3)
    # and mid-length it is the straight wall, the section's own
    assert seat("rear", 300.0, 0.0, row=100.0) == pytest.approx(-31.0)
    assert seat("front", 300.0, 0.0, row=100.0) == pytest.approx(-14.0)


@needs_node
def test_a_part_over_a_lobe_stands_on_the_lobe():
    """The end lobe reaches x = 600 between y 112 and 168 at the flange rows only: over it the top is the
    flange's, not the casting's the extrusion would put under a column at that depth. A part on the front
    of the lobe at row 140 is on its flank, the chord from (600, 168) to (590, 176): at x = 597 it is at
    y = 170.4, 110.6 behind the front plane."""
    assert seat("top", 597.0, 140.0) == pytest.approx(-132.0)
    assert seat("front", 597.0, 0.0, row=140.0) == pytest.approx(170.4 - D, abs=1e-3)


@needs_node
def test_a_point_outside_the_plan_has_no_surface_under_it_and_answers_zero_as_a_point_off_the_body_does():
    # plan (2, 5) is beyond the flange's corner arc; the extrusion would read the flange top under it
    assert seat("top", 2.0, 5.0) == 0
    assert seat("front", 2.0, 0.0, row=100.0) == 0
    assert seat("rear", 2.0, 0.0, row=100.0) == 0


@needs_node
def test_a_plan_housing_without_halves_seats_too():
    ch = {k: v for k, v in THREE.items() if k != "halves"}
    assert seat("top", 22.0, 33.0, chassis=ch) == pytest.approx(-132.0)


# ---- the recorder for the golden numbers ----------------------------------------------------------------------

def write_today():
    """Regenerate fixtures/plan_outline/open-as-today.json from the code as it stands. Only for a change that
    is meant to alter what a housing without a plan outline opens or seats as:
        PYTHONPATH=spec/tools:spec/tests python3 spec/tests/test_plan_open_js.py --write-today
    """
    out = {"devices": {label: open_state(ch) for label, ch in devices().items()}, "closed": closed_plan_digests()}
    TODAY.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print("wrote", TODAY)


if __name__ == "__main__":
    if "--write-today" in sys.argv:
        write_today()
    else:
        print(write_today.__doc__)
