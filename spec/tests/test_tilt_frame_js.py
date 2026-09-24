"""kit/relief.js tiltFrame / unproject / facetZ (docs/superpowers/specs/2026-09-24-tilted-facets-design.md)."""
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/tilt-frame.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_tilt_frame():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    o = json.loads(p.stdout.strip().splitlines()[-1])

    c30, s30 = math.cos(math.radians(30)), math.sin(math.radians(30))
    c45, s45 = math.cos(math.radians(45)), math.sin(math.radians(45))

    # Anchor stays at anchor for all facings
    assert o["up"]["anchorPt"] == [10, 50, 2]
    assert o["down"]["anchorPt"] == [10, 50, 0]
    assert o["left"]["anchorPt"] == [10, 50, 0]
    assert o["right"]["anchorPt"] == [10, 50, 0]

    # Axis step: 10 mm along the tilted axis
    # up: 10 mm down (y+10) compresses y and lifts z
    assert o["up"]["axisStep"][1] == pytest.approx(50 + 10 * c30, abs=1e-3)
    assert o["up"]["axisStep"][2] == pytest.approx(2 + 10 * s30, abs=1e-3)

    # down: 10 mm up (y-10) compresses y and lowers z
    assert o["down"]["axisStep"][1] == pytest.approx(50 + 10 * c30, abs=1e-3)
    assert o["down"]["axisStep"][2] == pytest.approx(0 - 10 * s30, abs=1e-3)

    # left: 10 mm right (x+10) compresses x and lifts z
    assert o["left"]["axisStep"][0] == pytest.approx(10 + 10 * c45, abs=1e-3)
    assert o["left"]["axisStep"][2] == pytest.approx(0 + 10 * s45, abs=1e-3)

    # right: 10 mm right (x+10) compresses x and lowers z
    assert o["right"]["axisStep"][0] == pytest.approx(10 + 10 * c45, abs=1e-3)
    assert o["right"]["axisStep"][2] == pytest.approx(0 - 10 * s45, abs=1e-3)

    # Local z: 1 mm out of part's face equals normal vector
    # up: normal = (0, -s, c), so at anchor+local_z = anchor + (0, -s30, c30)
    assert o["up"]["localZ"] == [10, round(50 - s30, 3), round(2 + c30, 3)]

    # down: normal = (0, s, c)
    assert o["down"]["localZ"] == [10, round(50 + s30, 3), round(0 + c30, 3)]

    # left: normal = (-s, 0, c), so (10-s45, 50, 0+c45)
    assert o["left"]["localZ"] == [round(10 - s45, 3), 50, round(0 + c45, 3)]

    # right: normal = (s, 0, c), so (10+s45, 50, 0+c45)
    assert o["right"]["localZ"] == [round(10 + s45, 3), 50, round(0 + c45, 3)]

    # Orthonormality: all columns unit length and orthogonal
    for facing in ['up', 'down', 'left', 'right']:
        f = o[facing]
        assert f["col0Mag"] == pytest.approx(1.0, abs=1e-3)
        assert f["col1Mag"] == pytest.approx(1.0, abs=1e-3)
        assert f["col2Mag"] == pytest.approx(1.0, abs=1e-3)
        assert f["dot01"] == pytest.approx(0.0, abs=1e-3)
        assert f["dot02"] == pytest.approx(0.0, abs=1e-3)
        assert f["dot12"] == pytest.approx(0.0, abs=1e-3)

    # Unprojection
    assert o["unprojUp"]["y"] == pytest.approx(60) and o["unprojUp"]["h"] == pytest.approx(10)
    assert o["unprojUp"]["x"] == 12 and o["unprojUp"]["w"] == 5

    # facetZ: distance from root edge times tan(deg)
    # up: root at y=40, proud edge at y=70; at py=70, d = py - r.y = 70-40 = 30
    assert o["facetZUp"] == pytest.approx(30 * math.tan(math.radians(30)), abs=1e-3)

    # left: root at x=0, proud edge at x=25; at px=25, d = px - r.x = 25-0 = 25
    assert o["facetZLeft"] == pytest.approx(25 * math.tan(math.radians(45)), abs=1e-3)

    # right: root at x=25, proud edge at x=0; at px=0, d = r.x + r.w - px = 25+0-0 = 25
    assert o["facetZRight"] == pytest.approx(25 * math.tan(math.radians(45)), abs=1e-3)
