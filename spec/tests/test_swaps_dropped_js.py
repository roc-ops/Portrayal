"""The loader says which swaps it left out (kit/redirects.js `droppedSwaps`)
and the explorer's shell hands that report to the page that asked."""
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent / "js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("name", ["swaps-dropped.mjs"])
def test_swaps_dropped_module(name):
    p = subprocess.run(["node", "--test", str(JS / name)], capture_output=True, text=True,
                       cwd=str(JS))
    assert p.returncode == 0, p.stdout + p.stderr
    assert "# pass" in p.stdout and "# fail 0" in p.stdout
