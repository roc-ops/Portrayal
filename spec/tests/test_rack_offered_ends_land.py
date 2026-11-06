"""What the rack kit offers as a power, ground or other cable end can be given to a cable (spec/tests/js/offered-ends-land.mjs).

Every device of the library in every configuration, one item beside a second of the same device, and each end
the kit lists for it taken as the end of a cable: accepted and not loose, or the row says it cannot be given.
Read from library/dist, so it skips on a tree that has not been built."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
JS = ROOT / "spec/tests/js/offered-ends-land.mjs"


@pytest.mark.heavy
def test_an_end_the_kit_offers_lands_or_says_it_cannot():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    if not (DIST / "components.json").exists() or not (DIST / "rack.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    p = subprocess.run(["node", "--test", str(JS)], capture_output=True, text=True, cwd=str(JS.parent),
                       env={**os.environ, "PORTRAYAL_DIST": str(DIST)})
    assert p.returncode == 0, p.stdout[-6000:] + p.stderr[-2000:]
