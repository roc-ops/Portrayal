"""The kit's half of a sheet body (docs/cable-managers-design.md section 4).

render.py leaves a sheet face's faceplate unfilled and says `shell: sheet` in
configs.json. viewer3d asks relief.js `sheetShell` what that makes the chassis,
and anything it does not recognise - an index from before the key, a shell
value from a newer build - is the box it always was: wrong, and visible.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/sheet-shell.mjs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def out():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_sheet_chassis_is_a_sheet(out):
    assert out["sheet"] == {"sheet": True, "thickness": 1.5}


def test_a_sheet_with_no_gauge_gets_a_nominal_one(out):
    assert out["noThickness"] == {"sheet": True, "thickness": 1.5}


@pytest.mark.parametrize("key", ["box", "unknown", "missing"])
def test_anything_else_is_a_box(out, key):
    assert out[key] == {"sheet": False, "thickness": 0}


def test_a_well_in_a_sheet_is_its_floor_and_nothing_round_it(out):
    """The tray. Walls and a back are a box's; built here they are the solid
    block in front of the host that a sheet body exists to avoid."""
    assert out["sheetWell"] == {"walls": False, "floor": True, "back": False, "depth": 42}
    assert out["sheetWellDeep"]["depth"] == 42      # clamped short of the far face, as any well
    assert out["boxWell"] == {"walls": True, "floor": True, "back": True, "depth": 42}


def test_a_handle_in_a_well_stands_on_the_wells_floor(out):
    """`uhandle` was built from the face plane whatever it stood in, so a ring
    `in:` a 42 mm well hung 42 mm above the floor it was drawn on."""
    assert out["standsOnFloor"] == -42
    assert out["standsOnFace"] == 0


def test_a_face_a_sheet_does_not_draw_is_open_air(out):
    assert out["missingFaceBox"] == "#3a3f44"
    assert out["missingFaceSheet"] is None
