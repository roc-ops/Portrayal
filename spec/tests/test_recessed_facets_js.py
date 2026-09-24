"""kit/relief.js for recessed facets: the pocket floor cleared under a sunk facet,
facetZ / facetInfo below 0, and a sunk tooth's skirt ending at its own base
(docs/superpowers/specs/2026-09-24-tilted-facets-design.md, Recessed facets)."""
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


def test_a_sunk_tooths_skirt_ends_at_its_base(o):
    s = o["skirt"]
    assert s["allAtBase"] is True
    assert s["minTop"] == -12 and s["maxTop"] == pytest.approx(2.25, abs=1e-3)
    # sides border open pocket and are built in full; the root edge is zero
    # height and the apex is inside the tooth (its return is as tall)
    assert s["edges"] == {"top": 0, "right": 3, "bottom": 0, "left": 3}


def test_a_proud_tooth_builds_the_skirt_it_did_before(o):
    assert o["skirtProud"] == {"edges": {"top": 0, "right": 3, "bottom": 0, "left": 3},
                               "allAtBase": True}
    assert o["outHeightDefault"] == 0
    assert o["outHeightNone"] == -12
