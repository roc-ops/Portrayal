"""The kit's rack modules, by their own node tests (spec/tests/js/rack-*.mjs):
the rack file, fit rules, cable managers, cables, routes and the export rules,
moved from portrayal-site with their tests."""
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent / "js"
FILES = sorted(JS.glob("rack-*.mjs"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_rack_module(path):
    p = subprocess.run(["node", "--test", str(path)], capture_output=True, text=True, cwd=str(JS))
    assert p.returncode == 0, p.stdout[-4000:] + p.stderr[-2000:]


def test_rack_tests_exist():
    assert FILES, "no spec/tests/js/rack-*.mjs found"
