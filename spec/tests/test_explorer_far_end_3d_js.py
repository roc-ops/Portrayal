"""kit/path-index.js: which projections the 3D scene's path index records.

A rear fibre is drawn only as a projection, so selecting it in 3D used to land
on the cassette. The index records a projection under the path it is of, and
only where no face draws that path as a part.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/explorer-far-end-3d.mjs"


def test_projection_records_in_node():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", "--test", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stdout + p.stderr
