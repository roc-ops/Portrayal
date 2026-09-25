"""kit/relief.js for open-frame faces: cavityShell and openFrameFaces
(spec/tests/test_open_frame.py has the render.py side)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/open-frame.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def o():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_pocket_has_walls_a_floor_and_a_back_clamped_short_of_the_far_face(o):
    assert o["pocket"] == {"walls": True, "floor": True, "back": True, "depth": 298}
    assert o["shallowPocket"] == {"walls": True, "floor": True, "back": True, "depth": 12}


def test_an_open_bays_mouth_is_a_six_millimetre_collar(o):
    assert o["hollow"] == {"walls": True, "floor": False, "back": False, "depth": 6}


def test_a_rear_passage_has_walls_and_no_floor_or_back(o):
    assert o["seeThrough"] == {"walls": True, "floor": False, "back": False, "depth": 298}


def test_an_open_frame_mouth_builds_nothing(o):
    assert o["openFrame"] == {"walls": False, "floor": False, "back": False, "depth": 0}


def test_open_frame_faces_are_read_off_the_drawings(o):
    assert sorted(o["faces"]) == ["front", "rear"]
    assert o["noFaces"] == []
