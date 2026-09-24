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
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    assert o["anchorStays"] == [10, 50, 2]
    assert o["tenBelow"] == [10, round(50 + 10 * c, 3), round(2 + 10 * s, 3)]
    # up-facing: the part's outward normal leans UP (towards smaller y)
    assert o["normalOut"] == [10, round(50 - s, 3), round(2 + c, 3)]
    # left-facing: the proud edge is the left, so moving right goes back towards the plate
    c45 = math.cos(math.radians(45))
    assert o["leftTenRight"][0] == pytest.approx(10 + 10 * c45, abs=1e-3)
    assert o["leftTenRight"][2] == pytest.approx(-10 * c45, abs=1e-3)
    assert o["unproj"]["y"] == pytest.approx(60) and o["unproj"]["h"] == pytest.approx(10)
    assert o["unproj"]["x"] == 12 and o["unproj"]["w"] == 5
    assert o["facetZ"] == pytest.approx(30 * math.tan(math.radians(30)), abs=1e-3)
