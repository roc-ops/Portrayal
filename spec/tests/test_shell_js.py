"""kit/shell.js's createShell, mounted under node (spec/tests/js/shell-*.mjs).

The shell has a page around it and no test mounted one before #929: the load
path (overlapping loadDevice/loadStage calls, #929) and the `fields=` a link
carries (#818) are held here through the real module, over the stand-in page in
fake-shell-dom.mjs.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent / "js"
FILES = sorted(JS.glob("shell-*.mjs"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_shell_module(path):
    p = subprocess.run(["node", "--test", str(path)], capture_output=True, text=True,
                       cwd=str(JS), timeout=120)
    assert p.returncode == 0, p.stdout[-4000:] + p.stderr[-2000:]
    # node --test passes a file whose tests never registered; it must have run some
    assert "# pass 0" not in p.stdout and "# pass" in p.stdout, p.stdout[-2000:]


def test_shell_tests_exist():
    assert FILES, "no spec/tests/js/shell-*.mjs found"
