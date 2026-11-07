"""Showing a box that opens: the open state the kit computes, and the controls.

`chassis.halves` says a device is a base and a lid (test_opening_halves.py holds
the format). kit/housing.js turns those figures into the open state a viewer
draws: each half standing `stands` from the seam, the lid turned about its hinge
edge by `angle`, the bays of each half on its floor. It reads no three.js and no
DOM, so the numbers are held here under node; the scene and the page only apply
them. The test device is `spec/tests/fixtures/halves`, a synthetic box.
"""
import json
import math
import pathlib
import shutil
import subprocess
import sys

import pytest

import warmrender

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
SCRIPT = ROOT / "spec/tests/js/housing.mjs"
FIXTURE_LIB = ROOT / "spec/tests/fixtures/halves/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/clam/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"
LIB = ROOT / "library"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

SIZE = {"w": 200.0, "h": 100.0, "d": 120.0}
HALVES = {"base": {"outer": "rear", "stands": 50.0}, "lid": {"hinge": "top", "angle": 90.0, "stands": 70.0}}
NORMAL = {"front": (0, 0, 1), "rear": (0, 0, -1), "right": (1, 0, 0),
          "left": (-1, 0, 0), "top": (0, 1, 0), "bottom": (0, -1, 0)}
META = {
    "views": ["front", "open"],
    "chassis": {"w": 200.0, "h": 100.0, "d": 120.0, "halves": HALVES},
    "bays": {"front": [],
             "open": [{"id": "lid-bay", "half": "lid", "at": [20.0, 30.0], "size": {"w": 60.0, "h": 50.0}},
                      {"id": "base-bay-a", "half": "base", "at": [20.0, 140.0], "size": {"w": 60.0, "h": 50.0}},
                      {"id": "base-bay-b", "half": "base", "at": [120.0, 140.0], "size": {"w": 60.0, "h": 50.0}}]},
}
CLOSED_BOX = {"views": ["front", "rear"], "chassis": {"w": 200.0, "h": 100.0, "d": 120.0},
              "bays": {"front": [{"id": "b", "at": [0, 0], "size": {"w": 10, "h": 10}}], "rear": []}}


def run(cases=(), metas=(), views=(), states=()):
    payload = {"cases": list(cases), "metas": list(metas), "views": list(views), "states": list(states)}
    p = subprocess.run(["node", str(SCRIPT)], input=json.dumps(payload), capture_output=True,
                       text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def case(name, halves=HALVES, size=SIZE, **kw):
    return {"name": name, "halves": halves, "size": size, **kw}


def close(a, b, tol=1e-4):
    return len(a) == len(b) and all(abs(x - y) < tol for x, y in zip(a, b))


# --- the open state ------------------------------------------------------------------------

@needs_node
def test_each_half_stands_its_own_depth_from_the_seam():
    """A base 50 deep from the back and a lid 70 deep from the seam, in a box
    120 deep: the seam is 10 behind the middle, and the closed lid is where the
    drawing's front half is."""
    plan = run([case("clam")])["clam"]["plan"]
    assert plan["base"]["size"] == [200.0, 100.0, 50.0] and plan["lid"]["size"] == [200.0, 100.0, 70.0]
    assert plan["base"]["center"] == [0, 0, -35.0]
    assert plan["lid"]["closedCenter"] == [0, 0, 25.0]
    assert plan["lid"]["pivot"] == [0, 50.0, -10.0]


@needs_node
def test_a_lid_at_zero_degrees_is_the_closed_lid():
    got = run([case("shut", {**HALVES, "lid": {**HALVES["lid"], "angle": 0.0}})])["shut"]["plan"]
    assert close(got["lid"]["center"], got["lid"]["closedCenter"])


@needs_node
def test_a_lid_that_states_no_angle_opens_flat():
    no_angle = {"base": HALVES["base"], "lid": {"hinge": "top", "stands": 70.0}}
    out = run([case("unstated", no_angle),
               case("flat", {**HALVES, "lid": {**HALVES["lid"], "angle": 180.0}})])
    assert out["unstated"]["plan"]["lid"]["angle"] == pytest.approx(math.pi)
    assert close(out["unstated"]["plan"]["lid"]["center"], out["flat"]["plan"]["lid"]["center"])


@needs_node
def test_the_lid_turns_about_its_hinge_edge():
    """At 90 degrees the lid's outer face, 60 in front of the middle and 70
    from the seam, is 70 above the hinge edge and 50 (half the lid's height)
    in front of the seam. Every point stays as far from the hinge as it was."""
    out = run([case("quarter", corner=[0, 0, 35.0]),
               case("flat", {**HALVES, "lid": {**HALVES["lid"], "angle": 180.0}}, corner=[0, 0, 35.0])])
    assert close(out["quarter"]["corner"], [0, 120.0, 40.0])
    assert close(out["flat"]["plan"]["lid"]["center"], [0, 100.0, -45.0])
    pivot = out["quarter"]["plan"]["lid"]["pivot"]
    closed = [0, 0, 60.0]
    assert math.dist(out["quarter"]["corner"], pivot) == pytest.approx(math.dist(closed, pivot), abs=1e-4)


@needs_node
@pytest.mark.parametrize("outer", sorted(NORMAL))
def test_the_lid_swings_its_outer_face_toward_the_hinge_side(outer):
    """Whatever face the base is bolted by and whichever side the lid hangs
    on, a quarter turn takes the direction the halves stand along to the
    hinge's outward normal."""
    perpendicular = [f for f, n in NORMAL.items()
                     if not any(a and b for a, b in zip(n, NORMAL[outer]))]
    assert len(perpendicular) == 4
    cases = []
    for hinge in perpendicular:
        s = [-v for v in NORMAL[outer]]
        cases.append(case(f"{outer}/{hinge}", {"base": {"outer": outer, "stands": 40.0},
                                               "lid": {"hinge": hinge, "angle": 90.0, "stands": 60.0}},
                          size={"w": 150.0, "h": 150.0, "d": 150.0}, corner=[0.0, 0.0, 0.0]))
        cases.append(case(f"{outer}/{hinge}/s", {"base": {"outer": outer, "stands": 40.0},
                                                 "lid": {"hinge": hinge, "angle": 90.0, "stands": 60.0}},
                          size={"w": 150.0, "h": 150.0, "d": 150.0}, corner=[float(v) for v in s]))
    out = run(cases)
    for hinge in perpendicular:
        base, along = out[f"{outer}/{hinge}"]["corner"], out[f"{outer}/{hinge}/s"]["corner"]
        step = [a - b for a, b in zip(along, base)]
        assert close(step, [float(v) for v in NORMAL[hinge]]), (outer, hinge, step)


@needs_node
@pytest.mark.parametrize("halves", [
    {"base": {"outer": "rear", "stands": 50.0}, "lid": {"hinge": "front", "angle": 90.0, "stands": 70.0}},
    {"base": {"outer": "rear", "stands": 50.0}, "lid": {"hinge": "rear", "angle": 90.0, "stands": 70.0}},
    {"base": {"outer": "above", "stands": 50.0}, "lid": {"hinge": "top", "angle": 90.0, "stands": 70.0}},
    {"base": {"outer": "rear", "stands": 0.0}, "lid": {"hinge": "top", "angle": 90.0, "stands": 70.0}},
    {"base": {"outer": "rear"}, "lid": {"hinge": "top", "angle": 90.0, "stands": 70.0}},
], ids=["hinge on the seam axis", "hinge on the back of the lid", "not a face", "no depth", "no stands"])
def test_halves_that_cannot_swing_give_no_plan(halves):
    assert run([case("bad", halves)])["bad"]["plan"] is None


@needs_node
def test_the_bays_of_each_half_are_plates_on_its_floor():
    out = run([case("clam", bays=META["bays"]["open"])])["clam"]
    base, lid = out["plates"]
    assert [p["id"] for p in base] == ["base-bay-a", "base-bay-b"] and [p["id"] for p in lid] == ["lid-bay"]
    plan = out["plan"]
    for plates, half in ((base, plan["base"]), (lid, plan["lid"])):
        for p in plates:
            # inside the half's own shell, against its outer face
            for c, s, h in zip(p["center"], p["size"], half["size"]):
                assert abs(c) + s / 2 <= h / 2 + 1e-6, (p, half["size"])
            assert math.isclose(sum(a * b for a, b in zip(p["center"], half["floor"])),
                                half["stands"] / 2 - 0.5, abs_tol=1e-6)
    # two bays side by side keep their gap and their order
    a, b = base
    assert b["center"][0] - a["center"][0] == pytest.approx(100.0)


# --- what a page and a tool are told ------------------------------------------------------

@needs_node
def test_describe_lists_the_halves_and_each_bays_half():
    out = run(metas=[META, CLOSED_BOX])
    assert out["describe"][0] == {
        "view": "open",
        "base": {"outer": "rear", "stands": 50.0, "bays": ["base-bay-a", "base-bay-b"]},
        "lid": {"hinge": "top", "angle": 90.0, "stands": 70.0, "bays": ["lid-bay"]}}
    assert out["describe"][1] is None


@needs_node
def test_the_toggle_selects_the_authored_open_view():
    out = run(metas=[META, CLOSED_BOX],
              views=[[0, "open", "front"], [0, "closed", "open"], [0, "closed", "front"],
                     [0, "open", "open"], [1, "open", "front"], [1, "closed", "rear"]])
    assert out["views"] == ["open", "front", "front", "open", "front", "rear"]
    assert out["view"] == ["open", None]


@needs_node
def test_a_housing_that_is_not_open_is_closed():
    assert run(states=["open", "OPEN", "closed", "", None, "ajar", 3])["state"] == [
        "open", "open", "closed", "closed", "closed", "closed", "closed"]


# --- a box that does not open is shown as it was -------------------------------------------

def test_a_device_with_no_halves_gets_no_open_state():
    """No halves: no plan, no description, no view to switch to, and the
    viewer never builds a second body (the check is in the next test)."""
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    out = run([{"name": "none", "halves": None, "size": SIZE}], metas=[CLOSED_BOX])
    assert out["none"]["plan"] is None and out["describe"] == [None] and out["view"] == [None]


def test_the_viewer_opens_only_a_box_with_halves_and_starts_closed():
    src = (KIT / "viewer3d.js").read_text()
    assert "import { housingPlan" in src or "housingPlan," in src
    assert "let HOUSING = normalizeHousing(opts.housing);" in src
    # the closed body is built as it always was; the open state is a group of its own
    assert "applyHousing()" in src and "housingGroup" in src
    # nothing the open state does is reachable unless the plan exists
    assert "if (!plan || HOUSING !== 'open')" in src
    assert "setHousing" in src.split("return {\n    load, select")[1]


def test_the_explorer_has_a_toggle_that_is_hidden_without_halves():
    page = (KIT / "index.html").read_text()
    assert "from './housing.js'" in page
    assert "const opens = !!state.meta && !!describeHalves(state.meta);" in page
    assert "housingBar.hidden = !opens;" in page
    assert "viewFor(" in page and "viewer.setHousing" in page and "v.setHousing(housing);" in page


def test_the_kit_lists_the_new_module():
    pkg = json.loads((KIT / "package.json").read_text())
    assert pkg["exports"]["./housing"] == "./housing.js"
    assert "node --check housing.js" in pkg["scripts"]["test"]
    assert "`housing.js`" in (KIT / "README.md").read_text()


# --- a real build -------------------------------------------------------------------------

@pytest.mark.heavy
@needs_node
def test_the_published_manifest_of_the_fixture_opens_in_two_halves(tmp_path):
    out = tmp_path / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(DEVICE), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    meta = json.loads((out / "clam.configs.json").read_text())
    got = run([case("clam", meta["chassis"]["halves"], {k: meta["chassis"][k[0]] for k in ("w", "h", "d")})],
              metas=[meta])
    assert got["clam"]["plan"]["base"]["size"] == [200.0, 100.0, 50.0]
    assert got["describe"][0]["lid"]["bays"] == ["lid-bay"] and got["view"] == ["open"]
