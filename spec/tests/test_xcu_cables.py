"""The Fibrain XCU10's adapters are couplers, by the rack kit (spec/tests/js/xcu-cables.mjs).

An XCU of each configuration on the rear rails of a four-post frame, switches
with SC optics, and a cable to each face of the same adapter: accepted when
added, routed, and read as one path through the panel; a made-up adapter is
refused. Read from library/dist, so it skips on a tree that has not been built."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
JS = ROOT / "spec/tests/js/xcu-cables.mjs"
BACK_END = ROOT / "spec/tests/js/rack-back-end.mjs"


def run_against_the_build(js, needs):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    if not all((DIST / name).exists() for name in ["components.json", *needs]):
        pytest.skip("library/dist not built - run ./build.sh")
    p = subprocess.run(["node", "--test", str(js)], capture_output=True, text=True, cwd=str(js.parent),
                       env={**os.environ, "PORTRAYAL_DIST": str(DIST)})
    assert p.returncode == 0, p.stdout[-6000:] + p.stderr[-2000:]


def test_the_xcu_adapters_are_couplers_against_the_rack_kit():
    run_against_the_build(JS, ["xcu.configs.json", "as5912-54x.configs.json"])


@pytest.mark.heavy
def test_the_back_end_of_a_rear_mounted_panel_is_placed_against_the_rack_kit():
    """The far end of an XCU10 adapter has a point, a route and a length (rack-back-end.mjs reads
    the rack at fixtures/rear-panel-back-end/ with the XCU10 and the MF-8 of the build)."""
    run_against_the_build(BACK_END, ["xcu.configs.json", "lmfs-f.configs.json", "xcu.xcu10-51id.front.elements.json"])
