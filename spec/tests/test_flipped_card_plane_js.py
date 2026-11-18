"""kit/relief.js: a facet's footprint replayed on a module's crop of a flipped face
(the underside) is mirrored within the crop, so the plane is cut in the strip under
the wedge and not beside it."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/flipped-card-plane.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def o():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_flat_face_replays_the_footprint_as_drawn(o):
    assert o["flatFace"] == {"x": 37.5, "y": 60, "w": 25, "h": 30}
    # card origin (37.5, 20), 4 px/mm: 40 mm down the card is row 160
    assert o["flatFacePx"] == [0, 160, 100, 120]
    assert o["flatSame"] is True


def test_a_flipped_face_replays_it_mirrored_within_the_crop(o):
    # the card's facet band is at card y 40 to 70; the crop is turned half a turn, so
    # the band is at 30 to 60 of the crop, face y 50 to 80, and not at y 60 to 90
    assert o["flippedBoth"] == {"x": 37.5, "y": 50, "w": 25, "h": 30}
    assert o["flippedBothPx"] == [0, 120, 100, 120]


def test_each_flipped_axis_is_mirrored_on_its_own(o):
    assert o["flippedX"] == {"x": 37.5, "y": 60, "w": 25, "h": 30}
    assert o["flippedY"] == {"x": 37.5, "y": 50, "w": 25, "h": 30}
    assert o["narrow"] == {"x": 50, "y": 60, "w": 10, "h": 30}


def test_the_mirrored_punch_keeps_its_facet_and_the_recorded_one_is_untouched(o):
    assert o["keepsFacet"] == "card--housing"
    assert o["theInputIsKept"] == [37.5, 60, 25, 30]


def test_a_shape_punch_is_mirrored_within_the_crop_and_carries_the_flips(o):
    # A 10 x 8 mm pocket at card x 3, y 80 is, turned within its 25 x 100 crop, at x 12, y 12.
    assert o["shapeFlipped"] == {"kind": "shape", "svg": "<svg/>", "x": 49.5, "y": 32, "w": 10, "h": 8,
                                 "flipX": True, "flipY": True}
    assert o["shapeOneAxis"] == {"kind": "shape", "svg": "<svg/>", "x": 49.5, "y": 100, "w": 10, "h": 8,
                                 "flipX": True, "flipY": False}


def test_a_shape_punch_on_a_flat_face_and_any_other_punch_are_left_as_drawn(o):
    assert o["shapeFlat"] is True
    assert o["otherSame"] is True
