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
    assert out["sheet"] is True


@pytest.mark.parametrize("key", ["box", "unknown", "missing"])
def test_anything_else_is_a_box(out, key):
    assert out[key] is False


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


# --- the wiring ----------------------------------------------------------------
#
# The functions above are pure and the tests above prove them. What they do not
# prove is that anything CALLS them: with the call sites reverted, every test in
# this file stayed green while the lacer panel drew as a solid painted box. The
# honest check is a built scene - vertex counts off a GLB - and the suite has no
# browser to build one in. Until it does, these read the three call sites, so a
# revert is a red test and not a picture nobody looked at.

KIT = SPEC.parent / "kit"


def _code(name):
    """The file without its line comments, so a commented-out call does not count."""
    return "\n".join(line.split("//")[0] for line in (KIT / name).read_text().splitlines())


def test_a_cavity_learns_it_is_in_a_sheet_from_the_faces_root():
    assert "dataset.shell === 'sheet'" in _code("relief.js")


def test_a_sheets_floor_is_drawn_from_both_sides():
    assert "c.sheet ? THREE.DoubleSide : THREE.FrontSide" in _code("relief.js")


def test_a_handle_is_built_from_where_it_stands():
    assert "const z0 = standsFrom(o);" in _code("relief.js")
    assert _code("relief.js").count("z0 + z]") == 2


def test_the_viewer_hides_a_sheets_six_faces():
    code = _code("viewer3d.js")
    branch = code.split("sheetShell(devIndex.chassis)) {", 1)
    assert len(branch) == 2, "viewer3d no longer asks whether the chassis is a sheet"
    assert "m.visible = false" in branch[1].split("} else {", 1)[0]
