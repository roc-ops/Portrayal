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
