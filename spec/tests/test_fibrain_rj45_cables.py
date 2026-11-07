"""The Fibrain HD RJ45 modules seat in their holders in the 1U frame and take a cable, by the
rack kit (spec/tests/js/fibrain-rj45-cables.mjs). Read from library/dist, so it skips on a tree
that has not been built."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
JS = ROOT / "spec/tests/js/fibrain-rj45-cables.mjs"


def test_the_rj45_modules_seat_in_the_frame_and_take_a_cable_against_the_rack_kit():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    if not (DIST / "components.json").exists() or not (DIST / "xpu.configs.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    p = subprocess.run(["node", "--test", str(JS)], capture_output=True, text=True, cwd=str(JS.parent),
                       env={**os.environ, "PORTRAYAL_DIST": str(DIST)})
    assert p.returncode == 0, p.stdout[-6000:] + p.stderr[-2000:]
