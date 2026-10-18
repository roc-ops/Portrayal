"""kit/relief.js for recessed facets: the pocket floor cleared under a sunk facet,
facetZ / facetInfo below 0, and a sunk tooth's skirt ending at its own base
(docs/tilted-facets-design.md, Recessed facets)."""
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/recessed-facets.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def o():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_pocket_floor_is_cleared_under_each_sunk_facet(o):
    # the face and its return, at their footprints; not the proud facet (it
    # is outside the pocket), not the proud facet INSIDE the pocket (its root
    # is at the pocket's mouth, so v1 builds it as before), not the facet that
    # runs out of the pocket (L117 refuses it), not a plain sunk out
    assert o["clears"] == [
        {"kind": "rect", "x": 0, "y": 62, "w": 25, "h": 14, "facet": "c--face-1"},
        {"kind": "rect", "x": 0, "y": 76, "w": 25, "h": 8, "facet": "c--return-1"},
    ]
    assert o["noFacets"] == 0


def test_the_clear_is_relative_to_the_pockets_own_lift(o):
    assert o["liftedPocket"] == ["a"]


def test_the_floor_raster_is_cleared_in_its_own_pixels(o):
    # pocket origin (0, 60), 4 px/mm: the face at y 62 -> 8 px, 14 mm -> 56 px
    assert o["raster"]["calls"] == [[0, 8, 100, 56], [0, 64, 100, 32]]
    assert o["raster"]["returnsCanvas"] is True
    assert o["raster"]["noneCalls"] == 0


def test_facet_z_with_a_negative_lift_is_the_sunk_surface(o):
    f = o["facetZ"]
    assert f["root"] == -12
    assert f["mid"] == pytest.approx(-12 + 7 * math.tan(math.radians(30)), abs=1e-3)
    assert f["proud"] == pytest.approx(f["expectProud"], abs=1e-3)
    assert f["proud"] == pytest.approx(-3.917, abs=1e-3)


def test_facet_info_reads_a_root_below_the_plate(o):
    fi = o["facetInfo"]
    assert fi["lift"] == -12
    assert fi["z0"] == pytest.approx(fi["expectZ0"], abs=1e-3)
    assert fi["base"] == 0


def test_a_sunk_tooth_narrower_than_its_pocket_skirts_to_its_base(o):
    s = o["skirtNarrow"]
    # both sides border open pocket and are built in full; the root edge is
    # zero height and the apex is inside the tooth (its return is as tall)
    assert s["edges"] == {"top": 0, "right": 3, "bottom": 0, "left": 3}
    assert s["basesAtLift"] is True
    assert s["zmin"] == -12 and s["zmax"] == pytest.approx(2.25, abs=1e-3)


def test_a_sunk_tooth_as_wide_as_its_pocket_builds_no_skirt_in_the_pocket_walls(o):
    s = o["skirtSpan"]
    # beside each side is the plate: segments whose top is below the mouth
    # are inside the solid, and the one that rises above it skirts only
    # down to the mouth - never in the pocket wall's plane below it
    assert s["edges"] == {"top": 0, "right": 1, "bottom": 0, "left": 1}
    assert s["sideBases"] == [0, 0]
    assert s["sideVertsAboveMouth"] is True


def test_a_sunk_tooth_with_no_pocket_reads_the_plate_beside_it(o):
    assert o["skirtNoPocket"] == {"top": 0, "right": 1, "bottom": 0, "left": 1}


def test_a_proud_tooth_builds_the_skirt_it_did_before(o):
    assert o["skirtProud"] == {"edges": {"top": 0, "right": 3, "bottom": 0, "left": 3},
                               "paired": True, "idxAsBefore": True, "allAtBase": True}
    assert o["outHeightDefault"] == 0
    assert o["outHeightNone"] == -12


@pytest.mark.parametrize("case", ["wellDeep", "wellLone", "wellNarrow"])
def test_the_floor_is_cleared_where_each_well_crosses_it(o, case):
    """I1: a well runs back along the facet normal and meets the floor (and the
    back 0.25 behind it) down-slope of its facet, past the facet's footprint.
    Every crossing lies inside a clear, which footprints alone do not give."""
    w = o[case]
    assert w["n"] >= 4
    assert w["covered"] is True
    assert w["byFootprintsAlone"] is False
    assert w["inPocket"] is True
    assert w["wellClears"] >= 1


def test_a_well_clears_only_the_pocket_its_facet_stands_in(o):
    assert o["wellElsewhere"] == 0
    assert o["wellProud"] == 0


def test_floor_clears_are_scoped_by_owner(o):
    assert o["owner"] == {"deviceWell": 0, "ownPocket": 1, "nested": 1, "otherCard": 0}


PLAIN_SHELL = {"walls": True, "floor": True, "back": True, "depth": 28}


def test_a_pocket_with_no_wall_builds_the_shell_it_always_did(o):
    assert o["shellPlain"] == PLAIN_SHELL
    assert o["shellWallZero"] == PLAIN_SHELL
    assert o["shellWallPastFloor"] == PLAIN_SHELL       # a wall at or past the floor is not a wall


def test_a_pocket_with_a_wall_keeps_its_floor_and_back_at_depth(o):
    assert o["shellWalled"] == {**PLAIN_SHELL, "wallDepth": 12}
    # the floor is clamped short of the far face; the plate is not
    assert o["shellWallClamped"]["depth"] == 98 and o["shellWallClamped"]["wallDepth"] == 12


def test_a_passage_or_a_sheet_ignores_a_wall(o):
    assert "wallDepth" not in o["shellWallSeeThrough"]
    assert "wallDepth" not in o["shellWallSheet"]


def test_the_walls_run_from_the_face_to_the_wall_only(o):
    s = o["span"]
    assert s["plain"] == {"top": 0, "bottom": -28, "depth": 28, "openBelow": False}
    assert s["walled"] == {"top": 0, "bottom": -12, "depth": 12, "openBelow": True}
    assert s["lifted"] == {"top": 10, "bottom": -2, "depth": 12, "openBelow": True}


def test_the_pocket_a_sunk_facet_stands_in_reports_its_wall_only_when_it_has_one(o):
    assert o["pocketOfPlain"] == ["floor", "h", "mouth", "w", "x", "y"]
    assert o["pocketOfWalled"] == {"x": 0, "y": 60, "w": 25, "h": 120, "floor": -28, "mouth": 0,
                                   "wall": 12}


def test_beside_a_tooth_as_wide_as_a_walled_pocket_the_skirt_is_built_below_the_wall(o):
    s = o["skirtWall"]
    # the plate is solid from the mouth to the wall (6 deep): above the mouth, as before
    # (the one segment that rises through it); below the wall the side is open
    # interior, so the tooth's side is skirted there, three segments a side, base to wall
    assert s["edges"] == {"top": 0, "right": 4, "bottom": 0, "left": 4}
    assert s["underSides"] == ["left"] * 3 + ["right"] * 3
    assert s["underBases"] == [-12] * 6
    assert s["underZ"] == [-12, -6]
    assert s["zmin"] == -12


def test_a_pocket_with_no_wall_or_a_wide_one_skirts_as_before(o):
    assert o["skirtWallless"] == {"edges": {"top": 0, "right": 1, "bottom": 0, "left": 1}, "under": 0}
    assert o["skirtWallNarrow"] == {"edges": {"top": 0, "right": 3, "bottom": 0, "left": 3}, "under": 0}


def test_clears_are_mirrored_on_a_flipped_face(o):
    m = o["mirror"]
    base = {"kind": "rect", "w": 10, "h": 14, "facet": "a"}
    assert m["none"] == [{**base, "x": 15, "y": 62}]
    assert m["x"] == [{**base, "x": 35, "y": 62}]          # 10 + 50 - 25
    assert m["y"] == [{**base, "x": 15, "y": 124}]         # 60 + 140 - 76
    assert m["both"] == [{**base, "x": 35, "y": 124}]
