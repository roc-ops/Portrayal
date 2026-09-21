"""A sloped relief feature can take its node's own outline, not only its box.

`profile` / `profile-y` built their height field over the node's bounding box, so
a sloped moulding could only ever be a rectangle. The MaiaEdge PBC-2000's centre
pane stands 15 proud between two octagonal windows, slopes back to the faceplate
at its top and bottom, and its two ends ARE the windows' ends - chamfer,
vertical, chamfer. A rectangle either ran into the windows or stopped short of
the chamfer corners, which is exactly where somebody looking at the hardware sees
the pane's side wall.

With `shape: true` beside a profile the kit now clips the height field to the
node's outline and drops the skirt along that outline. The geometry is a pure
function, so it is checked in node the way cavity-seats-on is.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/shaped-height-field.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_surface_covers_the_outline_and_nothing_else(out):
    assert out["topArea"] == pytest.approx(out["paneArea"], rel=1e-3), (
        "the clipped surface's area is not the outline's - it either spills into "
        "the windows' notches or leaves holes in the pane"
    )
    assert out["trianglesOutside"] == 0, \
        "a triangle of the surface lies outside the node's outline"


def test_every_vertex_stands_where_the_profiles_put_it(out):
    assert out["worstZ"] < 1e-9, \
        "a surface vertex is not at the depth the profiles give its (x, y)"
    assert out["midDepth"] == 15


def test_the_wall_follows_the_outline_from_surface_to_face(out):
    assert out["skirtPairs"] == out["ringLength"], \
        "the skirt must have one surface/face pair per outline point"
    assert out["skirtOff"] < 1e-9, \
        "a skirt point is not on the surface above or the face below"


def test_a_plain_rectangle_is_what_the_box_builder_made(out):
    assert out["boxArea"] == pytest.approx(4000, rel=1e-3)


def test_windows_cut_through_the_surface(out):
    """The PBC-2000's bezel: one sloped plate, two octagonal windows through it."""
    assert out["bezelArea"] == pytest.approx(out["bezelWant"], rel=1e-3), \
        "the bezel's surface is not its outline less its windows"
    assert out["inHole"] == 0, "a triangle of the surface covers a window"
    assert out["outOfShell"] == 0, "a triangle of the surface lies outside the bezel"
    assert out["worstHZ"] < 1e-9


def test_window_walls_come_back_on_their_own(out):
    assert out["shellSkirtPairs"] == out["shellRingPoints"], \
        "the outer wall must follow the outer outline and nothing else"
    assert out["holeSkirtPairs"] == out["holeRingPoints"], (
        "each window needs its own wall, returned apart from the outer one so it "
        "can be coloured as the bead it is"
    )


def test_a_hole_that_cannot_be_cut_gets_no_wall(out):
    assert out["strayHoleWall"] == 0, \
        "an unbridged hole was left uncut but still got a wall standing on the surface"
    assert out["strayArea"] == pytest.approx(374 * 41.27, rel=1e-3)
