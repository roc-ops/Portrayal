"""The open state of a stepped housing: the body split at the seam, and the lid turned about it.

A housing that states `chassis.section` and `chassis.halves` is a stepped body (kit/section.js).
Open, it is two parts: the seam is the plane `base.stands` from the base's `outer` face, each half
is the stepped body on its side of it (the section extruded, the fins cut back and the ribs added,
the same arrays as the closed body), and the lid turns about the line where the seam meets the hinge
face's outline (kit/housing.js). Every number below is recomputed here from the raw arrays and from
the section; the module is never asked to check its own arithmetic. The test devices are
`spec/tests/fixtures/opening-section` and `fixtures/fins`, synthetic boxes, never library devices.

What is held: the two parts together are the body (sum of volumes, of areas, closed edges), the cap
is planar at the seam and faces the other half, the bounds of each part with its ribs and its
`outside` ribs, the pivot line, the hand-computed pose of the lid at 90, 110 and 180 degrees, the
camera fit over the real bounds, that a seam which divides nothing is refused, and that a housing
with no section builds its box halves exactly as before.
"""
import json
import math
import pathlib
import shutil
import subprocess
import tempfile

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
OPEN = ROOT / "spec/tests/fixtures/opening-section/lib/devices/fixture/stepped-open/device.yaml"
OUTSIDE = ROOT / "spec/tests/fixtures/fins/lib/devices/fixture/finned-outside/device.yaml"
CLAM = ROOT / "spec/tests/fixtures/halves/lib/devices/fixture/clam/device.yaml"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

CHASSIS = yaml.safe_load(OPEN.read_text())["chassis"]
W, H, D = CHASSIS["width"], CHASSIS["height"], CHASSIS["depth"]
SECTION = CHASSIS["section"]
FINS = CHASSIS["fins"]
HALVES = CHASSIS["halves"]
OUT = yaml.safe_load(OUTSIDE.read_text())["chassis"]
SEAM_INDEX = 6

SCRIPT = """
import * as S from %s;
import * as Hs from %s;
const cases = JSON.parse(process.argv[2]);
const out = cases.map(c => {
  try {
    if (c.fn === 'arrays') return {ok: S.sectionArrays(c.section, c.W, c.H, c.D, c.fins, c.clip)};
    if (c.fn === 'split') return {ok: S.splitSection(c.section, c.W, c.H, c.D, c.fins, c.halves)};
    if (c.fn === 'halves') return {ok: S.sectionHalves(c.chassis, c.W, c.H, c.D)};
    if (c.fn === 'body') return {ok: S.sectionBody(c.chassis, c.W, c.H, c.D)};
    if (c.fn === 'plan') {
      const split = c.halvesOf ? S.sectionHalves(c.chassis, c.W, c.H, c.D).split : undefined;
      const plan = Hs.housingPlan(c.halves, c.size, split);
      return {ok: {plan, bounds: plan ? Hs.openBounds(plan) : null,
                   lid: plan && c.corners ? c.corners.map(p => Hs.lidPoint(plan, p)) : null,
                   plates: plan && c.bays ? ['base', 'lid'].map(n => Hs.bayPlates(plan, n, c.bays)) : null}};
    }
    return {error: 'unknown fn'};
  } catch (e) { return {error: String(e.message || e)}; }
});
console.log(JSON.stringify(out));
"""


def run(cases):
    with tempfile.TemporaryDirectory() as tmp:
        script = pathlib.Path(tmp) / "t.mjs"
        script.write_text(SCRIPT % (json.dumps((KIT / "section.js").as_uri()),
                                    json.dumps((KIT / "housing.js").as_uri())))
        p = subprocess.run(["node", str(script), json.dumps(cases)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def one(case):
    got = run([case])[0]
    assert "ok" in got, got
    return got["ok"]


def split(chassis=None, halves=None, w=None, h=None, d=None):
    c = chassis or CHASSIS
    return one({"fn": "split", "section": c["section"], "W": w or c["width"], "H": h or c["height"],
                "D": d or c["depth"], "fins": c.get("fins"), "halves": halves or c["halves"]})


def whole(chassis=None):
    c = chassis or CHASSIS
    return one({"fn": "arrays", "section": c["section"], "W": c["width"], "H": c["height"],
                "D": c["depth"], "fins": c.get("fins")})


def with_seam(stands, outer="top", hinge="rear"):
    return {"base": {"outer": outer, "stands": stands}, "lid": {"hinge": hinge, "angle": 180.0, "stands": H - stands}}


# --- measuring the arrays ------------------------------------------------------------------

def triangles(a, group=None):
    idx = a["indices"]
    ranges = [(g["start"], g["start"] + g["count"]) for g in a["groups"]
              if group is None or g["materialIndex"] == group]
    out = []
    for lo, hi in ranges:
        for i in range(lo, hi, 3):
            out.append([tuple(a["positions"][3 * j:3 * j + 3]) for j in idx[i:i + 3]])
    return out


def cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def area(tri):
    c = cross(sub(tri[1], tri[0]), sub(tri[2], tri[0]))
    return 0.5 * math.sqrt(sum(v * v for v in c))


def volume(a):
    """Signed volume by the divergence theorem: the sum of each triangle's tetrahedron on the origin."""
    total = 0.0
    for t in triangles(a):
        c = cross(t[1], t[2])
        total += sum(t[0][i] * c[i] for i in range(3)) / 6.0
    return total


def surface(a, group=None):
    return sum(area(t) for t in triangles(a, group))


def bounds(a):
    pos = a["positions"]
    return [min(pos[i::3]) for i in range(3)], [max(pos[i::3]) for i in range(3)]


def shoelace(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def open_edges(a):
    """Undirected edges (by rounded position) used by other than two triangles: a closed shell has none."""
    seen = {}
    key = lambda p: tuple(round(v, 4) for v in p)
    for t in triangles(a):
        for p, q in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted((key(t[p]), key(t[q]))))
            seen[e] = seen.get(e, 0) + 1
    return [e for e, n in seen.items() if n != 2]


def plain(chassis=None):
    """The fixture's chassis without the fins: the closed shells are then exact."""
    c = dict(chassis or CHASSIS)
    c.pop("fins", None)
    return c


# --- the two parts are the body ------------------------------------------------------------

@needs_node
def test_the_two_parts_together_are_the_body_of_the_section():
    s = split(plain())
    body = shoelace([tuple(p) for p in SECTION]) * W
    assert volume(s["base"]["arrays"]) + volume(s["lid"]["arrays"]) == pytest.approx(body, rel=1e-9)
    # a part alone: the upper casting (14 to 250 over 132 rows) and the flange up to the seam at 144
    upper = (250 - 14) * 132 + 281 * (144 - 132)
    assert volume(s["base"]["arrays"]) == pytest.approx(upper * W, rel=1e-9)


@needs_node
def test_with_fins_the_two_parts_still_sum_to_the_whole_body():
    s = split()
    w = whole()
    assert volume(s["base"]["arrays"]) + volume(s["lid"]["arrays"]) == pytest.approx(volume(w), rel=1e-9)
    # the surface is the body's plus the cap twice, the seam's section across the width
    cap = surface(s["base"]["arrays"], SEAM_INDEX)
    assert cap == pytest.approx(W * 281.0, rel=1e-9)
    assert surface(s["base"]["arrays"]) + surface(s["lid"]["arrays"]) == pytest.approx(surface(w) + 2 * cap, rel=1e-9)


@needs_node
def test_each_part_without_ribs_is_a_closed_shell_the_cap_included():
    """A rib is five faces on the surface it stands on, so a part with ribs is open at their roots
    exactly as the closed body is; without fins each part is closed."""
    s = split(plain())
    assert open_edges(s["base"]["arrays"]) == [] and open_edges(s["lid"]["arrays"]) == []


@needs_node
def test_the_cap_is_planar_at_the_seam_and_faces_the_other_half():
    s = split(plain())
    for part, normal in (("base", -1.0), ("lid", 1.0)):
        a = s[part]["arrays"]
        caps = triangles(a, SEAM_INDEX)
        assert caps, part
        assert {round(p[1], 9) for t in caps for p in t} == {0.0}, part       # H/2 - 144
        i = next(g for g in a["groups"] if g["materialIndex"] == SEAM_INDEX)
        for k in range(i["start"], i["start"] + i["count"]):
            vi = a["indices"][k]
            assert a["normals"][3 * vi:3 * vi + 3] == [0, normal, 0], (part, k)
        for t in caps:                                  # wound to agree with the stored normal
            c = cross(sub(t[1], t[0]), sub(t[2], t[0]))
            assert c[1] * normal > 0, (part, t)


@needs_node
def test_the_groups_ascend_by_material_and_cover_the_indices():
    s = split()
    for part in ("base", "lid"):
        a = s[part]["arrays"]
        mats = [g["materialIndex"] for g in a["groups"]]
        assert mats == sorted(mats) and SEAM_INDEX in mats
        assert sum(g["count"] for g in a["groups"]) == len(a["indices"])
        assert len(a["positions"]) == len(a["normals"]) == 3 * len(a["uvs"]) // 2


@needs_node
def test_a_part_is_cut_not_stretched():
    """No vertex of the base is below the seam and none of the lid above it, and each keeps the
    body's own rows of the section (the upper casting's top edge, the lower casting's bottom)."""
    s = split(plain())
    (blo, bhi), (llo, lhi) = bounds(s["base"]["arrays"]), bounds(s["lid"]["arrays"])
    assert (blo[1], bhi[1]) == (0.0, 144.0) and (llo[1], lhi[1]) == (-144.0, 0.0)
    assert (blo[0], bhi[0]) == (-W / 2, W / 2)
    assert (blo[2], bhi[2]) == (-140.5, 140.5)
    assert (llo[2], lhi[2]) == (-140.5, 140.5)          # the flange is the widest row of both


@needs_node
def test_the_bounds_carried_are_the_arrays_own():
    s = split()
    for part in ("base", "lid"):
        lo, hi = bounds(s[part]["arrays"])
        assert s[part]["min"] == pytest.approx(lo) and s[part]["max"] == pytest.approx(hi)
        assert s[part]["size"] == pytest.approx([b - a for a, b in zip(lo, hi)])
        assert s[part]["center"] == pytest.approx([(a + b) / 2 for a, b in zip(lo, hi)])


# --- the ribs go with the half they stand on ------------------------------------------------

@needs_node
def test_the_ribs_of_the_top_are_the_bases_and_those_of_the_bottom_the_lids():
    """The bottom ribs stand 48 beyond the cut-back lower surface and the top ribs 29 beyond the
    cut-back upper one; the body's own edges are at 0 and 288, so the ribs are inside the box."""
    s = split()
    w = whole()
    wlo, whi = bounds(w)
    (blo, bhi), (llo, lhi) = bounds(s["base"]["arrays"]), bounds(s["lid"]["arrays"])
    assert bhi[1] == pytest.approx(whi[1]) and llo[1] == pytest.approx(wlo[1])
    assert blo[1] == pytest.approx(0.0) and lhi[1] == pytest.approx(0.0)
    # the 41 top ribs' tips, two triangles each, at the top of the box: all in the base, none in the lid
    tips = lambda a: [t for t in triangles(a) if all(abs(p[1] - H / 2) < 1e-6 for p in t)]
    assert len(tips(s["base"]["arrays"])) == 82 and tips(s["lid"]["arrays"]) == []


@needs_node
def test_ribs_outside_the_box_are_inside_the_bounds_of_their_part():
    chassis = {**OUT, "halves": {"base": {"outer": "top", "stands": 20.0},
                                 "lid": {"hinge": "rear", "angle": 180.0, "stands": 20.0}}}
    s = split(chassis)
    (blo, bhi), (llo, lhi) = bounds(s["base"]["arrays"]), bounds(s["lid"]["arrays"])
    assert (blo[1], bhi[1]) == (0.0, 40.0)               # 20 of casting above the seam and 20 of ribs
    assert (llo[1], lhi[1]) == (-30.0, 0.0)              # 20 of casting below it and 10 of ribs
    w = whole(chassis)
    assert volume(s["base"]["arrays"]) + volume(s["lid"]["arrays"]) == pytest.approx(volume(w), rel=1e-9)
    assert s["base"]["size"][1] == 40.0 and s["lid"]["size"][1] == 30.0


WINGED = {
    "width": 60.0, "height": 40.0, "depth": 50.0,
    "section": [[10, 0], [40, 0], [40, 5], [50, 5], [50, 40], [0, 40], [0, 5], [10, 5]],
    "fins": [{"on": "top", "span": [5.0, 55.0], "core": 15.0, "rib": 4.0, "gap": 4.0}],
    "halves": {"base": {"outer": "top", "stands": 8.0}, "lid": {"hinge": "rear", "stands": 32.0}},
}


@needs_node
def test_a_seam_through_the_ribs_cuts_each_rib_and_caps_it():
    """The top field cuts the casting back 15 mm over its edge (x 10 to 40) and the wings either
    side of it (rows 5 to 15) stay; six ribs stand 15 tall on the cut surface, so a seam 8 down
    runs through the wings and through every rib. Each rib is in both parts, closed at the seam,
    and the two together are the body."""
    s = split(WINGED)
    w = whole(WINGED)
    assert volume(s["base"]["arrays"]) + volume(s["lid"]["arrays"]) == pytest.approx(volume(w), rel=1e-9)
    # the cap of the base: the two wings, 10 wide, and six ribs 4 thick over the 30 of the edge
    cap = surface(s["base"]["arrays"], SEAM_INDEX)
    assert cap == pytest.approx(60.0 * 20.0 + 6 * 4.0 * 30.0, rel=1e-9)
    assert surface(s["lid"]["arrays"], SEAM_INDEX) == pytest.approx(cap, rel=1e-9)
    assert {round(p[1], 9) for t in triangles(s["base"]["arrays"], SEAM_INDEX) for p in t} == {12.0}   # 20 - 8
    # the pivot is the wings' rear edge, 50, at the seam row
    assert s["pivot"] == pytest.approx([0.0, 12.0, 25.0 - 50.0])


@needs_node
def test_a_seam_in_the_cut_back_stretch_with_no_body_there_is_refused():
    """The fixture's top field cuts the whole upper casting's width back 29 mm: a seam 10 down
    leaves the base with nothing."""
    got = run([{"fn": "split", "section": SECTION, "W": W, "H": H, "D": D, "fins": FINS,
                "halves": with_seam(10.0)}])[0]
    assert "outline" in got["error"]


# --- the pivot line -------------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("stands,outer,hinge,expect", [
    (144.0, "top", "rear", [0.0, 0.0, D / 2 - 281.0]),        # the flange's rear edge
    (144.0, "top", "front", [0.0, 0.0, D / 2 - 0.0]),         # the flange's front edge
    (100.0, "top", "rear", [0.0, 188 - 144.0, D / 2 - 250.0]),    # the upper casting's rear wall
    (100.0, "top", "front", [0.0, 44.0, D / 2 - 14.0]),
    (100.0, "bottom", "rear", [0.0, 144 - 188.0, D / 2 - 253.0]),   # the seam is 188 down: the lower casting
    (100.0, "bottom", "front", [0.0, -44.0, D / 2 - 28.0]),
])
def test_the_lid_turns_about_the_seam_row_on_the_hinge_faces_outline(stands, outer, hinge, expect):
    """The line is parallel to the extrusion, at the seam height, where the outline of the hinge
    face meets the seam plane: the section's rearmost x (or foremost) in the seam's row. In the
    flange that is the flange's edge; in a casting, its wall."""
    s = split(plain(), with_seam(stands, outer, hinge))
    assert s["pivot"] == pytest.approx(expect)


# --- what cannot be split ------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("halves", [
    with_seam(132.0), with_seam(155.0), with_seam(0.0), with_seam(288.0), with_seam(300.0),
    with_seam(144.0, outer="front"), with_seam(144.0, outer="left"),
    with_seam(144.0, hinge="top"), with_seam(144.0, hinge="left"),
], ids=["on the flange's edge", "on its lower edge", "on the top", "on the bottom", "past the bottom",
        "front is not the base", "left is not the base", "hinge on the top", "hinge on the left"])
def test_a_seam_that_divides_nothing_or_a_face_that_does_not_open_is_refused(halves):
    got = run([{"fn": "split", "section": SECTION, "W": W, "H": H, "D": D, "fins": FINS,
                "halves": halves}])[0]
    assert "error" in got, got
    assert run([{"fn": "halves", "chassis": {**CHASSIS, "halves": halves}, "W": W, "H": H, "D": D}]
               )[0]["ok"]["refused"]


@needs_node
def test_sectionHalves_gives_the_split_for_a_housing_that_opens_and_nothing_for_one_that_does_not():
    got = run([
        {"fn": "halves", "chassis": CHASSIS, "W": W, "H": H, "D": D},
        {"fn": "halves", "chassis": plain_of_halves(), "W": W, "H": H, "D": D},
        {"fn": "halves", "chassis": {k: v for k, v in CHASSIS.items() if k != "section"}, "W": W, "H": H, "D": D},
        {"fn": "halves", "chassis": None, "W": W, "H": H, "D": D},
    ])
    assert got[0]["ok"]["split"]["pivot"] == pytest.approx([0.0, 0.0, -140.5])
    assert got[1]["ok"] is None and got[2]["ok"] is None and got[3]["ok"] is None


def plain_of_halves():
    return {k: v for k, v in CHASSIS.items() if k != "halves"}


# --- the closed body is as it was ----------------------------------------------------------

@needs_node
def test_a_clip_that_is_not_asked_for_builds_the_body_as_before():
    a = whole()
    b = one({"fn": "arrays", "section": SECTION, "W": W, "H": H, "D": D, "fins": FINS, "clip": None})
    assert a == b
    assert all(g["materialIndex"] != SEAM_INDEX for g in a["groups"])


# --- the lid's pose ------------------------------------------------------------------------

def rot_x(p, pivot, deg):
    """Rotate p about the line through `pivot` along +x by `deg`: y and z turn, x stays."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    y, z = p[1] - pivot[1], p[2] - pivot[2]
    return (p[0], pivot[1] + y * c - z * s, pivot[2] + y * s + z * c)


def hand_corners(split_, angle):
    """The eight corners of the lid's bounds after it turns, worked out here from the bounds the
    lid has closed and the pivot, by a rotation about x: the hinge is on the rear, the halves are
    stacked along y."""
    lo, hi = split_["lid"]["min"], split_["lid"]["max"]
    return [rot_x((x, y, z), split_["pivot"], angle) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
            for z in (lo[2], hi[2])]


@needs_node
@pytest.mark.parametrize("angle", [90.0, 110.0, 180.0])
def test_the_lid_ends_up_where_a_hand_computed_turn_puts_it(angle):
    halves = {"base": HALVES["base"], "lid": {**HALVES["lid"], "angle": angle}}
    chassis = {**plain(), "halves": halves}
    s = split(chassis)
    got = one({"fn": "plan", "chassis": chassis, "W": W, "H": H, "D": D, "halves": halves, "halvesOf": True,
               "size": {"w": W, "h": H, "d": D},
               "corners": [[x * s["lid"]["size"][0] / 2, y * s["lid"]["size"][1] / 2, z * s["lid"]["size"][2] / 2]
                           for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]})
    plan = got["plan"]
    assert plan["lid"]["center"] == pytest.approx(
        rot_x(tuple(s["lid"]["center"]), s["pivot"], angle), abs=1e-6)
    expect = sorted(tuple(round(v, 6) for v in p) for p in hand_corners(s, angle))
    assert sorted(tuple(round(v, 6) for v in p) for p in got["lid"]) == pytest.approx(expect, abs=1e-5)
    # the lid's own bounds after the turn: closed it was 144 deep below the seam, 281 front to back
    ys = [p[1] for p in expect]
    zs = [p[2] for p in expect]
    if angle == 90.0:
        assert (min(ys), max(ys)) == pytest.approx((-281.0, 0.0), abs=1e-6)
        assert (min(zs), max(zs)) == pytest.approx((-140.5 - 144.0, -140.5), abs=1e-6)
    if angle == 180.0:
        assert (min(ys), max(ys)) == pytest.approx((0.0, 144.0), abs=1e-6)
        assert (min(zs), max(zs)) == pytest.approx((-140.5 - 281.0, -140.5), abs=1e-6)


@needs_node
def test_the_lid_at_zero_degrees_is_the_closed_lid():
    halves = {"base": HALVES["base"], "lid": {**HALVES["lid"], "angle": 0.0}}
    chassis = {**plain(), "halves": halves}
    plan = one({"fn": "plan", "chassis": chassis, "W": W, "H": H, "D": D, "halves": halves, "halvesOf": True,
                "size": {"w": W, "h": H, "d": D}})["plan"]
    assert plan["lid"]["center"] == pytest.approx(plan["lid"]["closedCenter"])


@needs_node
def test_a_lid_that_states_no_angle_opens_flat():
    halves = {"base": HALVES["base"], "lid": {"hinge": "rear", "stands": 144.0}}
    chassis = {**plain(), "halves": halves}
    plan = one({"fn": "plan", "chassis": chassis, "W": W, "H": H, "D": D, "halves": halves, "halvesOf": True,
                "size": {"w": W, "h": H, "d": D}})["plan"]
    assert plan["lid"]["angle"] == pytest.approx(math.pi)


@needs_node
@pytest.mark.parametrize("angle", [90.0, 110.0, 180.0])
def test_the_camera_fit_holds_both_parts_ribs_included(angle):
    """openBounds is the box the camera frames: it holds every corner of the base's bounds and of
    the turned lid's, ribs that stand outside the box included, and no more."""
    halves = {"base": {"outer": "top", "stands": 20.0}, "lid": {"hinge": "rear", "angle": angle, "stands": 20.0}}
    chassis = {**OUT, "halves": halves}
    s = split(chassis)
    got = one({"fn": "plan", "chassis": chassis, "W": 60.0, "H": 40.0, "D": 50.0, "halves": halves,
               "halvesOf": True, "size": {"w": 60.0, "h": 40.0, "d": 50.0}})
    corners = []
    blo, bhi = s["base"]["min"], s["base"]["max"]
    corners += [(x, y, z) for x in (blo[0], bhi[0]) for y in (blo[1], bhi[1]) for z in (blo[2], bhi[2])]
    corners += hand_corners(s, angle)
    lo, hi = got["bounds"]["min"], got["bounds"]["max"]
    for i in range(3):
        assert lo[i] == pytest.approx(min(c[i] for c in corners), abs=1e-6)
        assert hi[i] == pytest.approx(max(c[i] for c in corners), abs=1e-6)
    assert bhi[1] == 40.0                                  # the ribs standing out of the top are in


@needs_node
def test_the_bay_plates_stand_on_the_casting_not_on_the_rib_tips():
    """A plate is a stand-in for a module on the floor of its half. The floor of a stepped half is
    the casting's own surface, the core the ribs stand on, not the tips: the top ribs are 29 tall and
    the bottom ones 48, so the base's plates are 115 (144 - 29) from the middle and the lid's -96."""
    bays = [{"id": "a", "half": "base", "at": [10.0, 10.0], "size": {"w": 100.0, "h": 60.0}},
            {"id": "b", "half": "lid", "at": [10.0, 10.0], "size": {"w": 100.0, "h": 60.0}}]
    got = one({"fn": "plan", "chassis": CHASSIS, "W": W, "H": H, "D": D, "halves": HALVES, "halvesOf": True,
               "size": {"w": W, "h": H, "d": D}, "bays": bays})
    base, lid = got["plates"]
    parts = got["plan"]["split"]
    top = base[0]["center"][1] + parts["base"]["center"][1] + base[0]["size"][1] / 2
    bottom = lid[0]["center"][1] + parts["lid"]["center"][1] - lid[0]["size"][1] / 2
    assert top == pytest.approx(144.0 - 29.0, abs=1e-6)
    assert bottom == pytest.approx(144.0 - 240.0, abs=1e-6)
    # and the half's body is the casting, whose bounds are inside the part's
    for name in ("base", "lid"):
        body = got["plan"][name]["body"]
        assert all(b <= p + 1e-6 for b, p in zip(body["size"], got["plan"][name]["size"]))


# --- a box with no section is as it was ----------------------------------------------------

CLAM_CHASSIS = yaml.safe_load(CLAM.read_text())["chassis"]


@needs_node
@pytest.mark.parametrize("angle", [None, 90.0, 110.0, 180.0])
def test_the_plain_box_fixture_builds_its_halves_exactly_as_before(angle):
    halves = json.loads(json.dumps(CLAM_CHASSIS["halves"]))
    if angle is None:
        del halves["lid"]["angle"]
    else:
        halves["lid"]["angle"] = angle
    size = {"w": 200.0, "h": 100.0, "d": 120.0}
    chassis = {**{k: v for k, v in CLAM_CHASSIS.items() if k != "halves"}, "halves": halves}
    a = one({"fn": "plan", "chassis": chassis, "W": 200.0, "H": 100.0, "D": 120.0, "halves": halves, "size": size})
    assert a["plan"] is not None and "split" not in a["plan"] and "mesh" not in a["plan"]["base"]
    # the same call with the split asked for builds from the box: there is no section to split
    b = one({"fn": "plan", "chassis": chassis, "W": 200.0, "H": 100.0, "D": 120.0, "halves": halves, "size": size,
             "halvesOf": False})
    assert a == b
    assert a["plan"]["base"]["size"] == [200.0, 100.0, 50.0] and a["plan"]["lid"]["size"] == [200.0, 100.0, 70.0]
    assert a["plan"]["lid"]["pivot"] == [0, 50.0, -10.0]
    assert a["plan"]["lid"]["closedCenter"] == [0, 0, 25.0]


def _library_devices(n):
    from portrayal import libwalk
    out = []
    for path in libwalk.iter_devices(ROOT / "library"):
        ch = (yaml.safe_load(pathlib.Path(path).read_text()) or {}).get("chassis") or {}
        if ch.get("width") and ch.get("height") and ch.get("depth") and "section" not in ch and "halves" not in ch:
            out.append((str(path), ch))
        if len(out) == n:
            break
    return out


@needs_node
def test_three_library_devices_get_no_split_and_no_open_state():
    devices = _library_devices(3)
    assert len(devices) == 3
    got = run([{"fn": "halves", "chassis": ch, "W": ch["width"], "H": ch["height"], "D": ch["depth"]}
               for _, ch in devices])
    assert [g["ok"] for g in got] == [None, None, None]
    sizes = [{"w": ch["width"], "h": ch["height"], "d": ch["depth"]} for _, ch in devices]
    plans = run([{"fn": "plan", "halves": None, "size": s} for s in sizes])
    assert [p["ok"]["plan"] for p in plans] == [None, None, None]


# --- a real build ---------------------------------------------------------------------------

@pytest.mark.heavy
@needs_node
def test_the_published_chassis_of_the_fixture_opens_from_its_section(tmp_path):
    """The build carries `section`, `fins` and `halves` of the device as written, and the kit cuts
    the body from them: the split of the published chassis is the split of the written one."""
    import warmrender
    lib = ROOT / "spec/tests/fixtures/opening-section/lib"
    out = tmp_path / "o"
    r = warmrender.run(["python3", str(ROOT / "spec/tools/portrayal/render.py"), str(OPEN), "--library", str(lib),
                        "--library", str(ROOT / "spec/tests/fixtures/halves/lib"), "--library", str(ROOT / "library"),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    meta = json.loads((out / "stepped-open.configs.json").read_text())
    chassis = meta["chassis"]
    assert chassis["halves"] == HALVES and chassis["section"] == SECTION and chassis["fins"] == FINS
    got = one({"fn": "halves", "chassis": chassis, "W": chassis["w"], "H": chassis["h"], "D": chassis["d"]})
    assert got["split"]["pivot"] == pytest.approx([0.0, 0.0, -140.5])
    assert got["split"]["base"]["size"] == pytest.approx(split()["base"]["size"])


# --- the viewer applies it, and only when there is a split ---------------------------------

def _src(name):
    return (KIT / name).read_text()


def test_the_viewer_builds_the_open_halves_from_the_split_only_for_a_section():
    src = _src("viewer3d.js")
    assert "sectionHalves" in src
    body = src.split("function applyHousing() {")[1].split("const setHousing")[0]
    # the split is asked for before the plan, and the box halves are what is built without one
    assert body.index("sectionHalves(") < body.index("housingPlan(")
    assert "new THREE.BoxGeometry(...h.size)" in body              # the box halves, as before
    assert "BufferGeometry" in body and "plan.split" in body or "split.base" in body


def test_the_viewer_hides_the_cap_as_a_box_half_hides_its_open_face():
    body = _src("viewer3d.js").split("function applyHousing() {")[1].split("const setHousing")[0]
    assert "visible: false" in body


def test_the_closed_state_is_not_touched():
    body = _src("viewer3d.js").split("function applyHousing() {")[1].split("const setHousing")[0]
    # nothing is built before the early return for a closed box or one without a plan
    assert body.index("if (!plan || HOUSING !== 'open')") < body.index("BufferGeometry")
