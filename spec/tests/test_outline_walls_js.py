"""A cavity that names its outline node is walled along that outline.

relief.js always PUNCHED a `relief.cavity` in its node's shape, and then built
the walls as a box round the shape's bounding rect. On an RJ45 that box is most
of the housing: the stepped face beside the latch slot stood in front of
nothing, and the floor 18.6 mm back repainted the whole face, so in 3D every
jack read as two stencils with air between them. `outlineWalls` extrudes the
outline instead, and the floor and back are cut to it.

The walls are a pure function of rings and a face-to-world map, so they are
checked in node rather than a browser, the way cavity-seats-on is.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/outline-walls.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_rj45_outline_keeps_its_twelve_corners(out):
    # sampled every 0.05 mm, as ringsOf is for a cavity, and thinned: the
    # three-tier opening has twelve corners and no wall between them
    assert out["corners"] == 12 and out["quads"] == 12, out


def test_the_walls_run_from_the_mouth_to_the_floor(out):
    assert out["zs"] == [-18.6, 0], out


def test_every_wall_faces_out_of_the_cavity(out):
    # as a BoxGeometry's faces do, so a `walls: inside` cavity's BackSide still
    # shows the inside; whichever way the path was drawn, and on a mirrored face
    assert out["outward"] == 1, "walls face into the cavity"
    assert out["reversedOutward"] == 1, "an outline drawn the other way round flips its walls"
    assert out["mirroredOutward"] == 1, "a mirrored face flips its walls"


def test_an_island_in_the_cavity_is_walled_facing_into_it(out):
    assert out["islandQuads"] == 8, out
    assert out["shellOutward"] == 1, out
    assert out["holeOutward"] == 0, "an island's walls face away from it, out of the cavity"


def test_no_outline_builds_nothing(out):
    assert out["empty"] == 0
