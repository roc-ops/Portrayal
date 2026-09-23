"""kit/optical.js: a fibre path's endpoint, far end and row label.

The explorer reads optical.ends out of components.json (front numbers are
optical_ports.front_label's) and turns a selected path into the fibre it is,
the path of the fibre's other end, and the words its row shows.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/fibre-ends.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_module_of_a_path(out):
    assert out["module"] == "bay-1/module"
    assert out["moduleNested"] == "front-6/module/slot-2/module"
    assert out["moduleNone"] is None


def test_a_path_names_its_fibre_front_or_rear(out):
    assert out["front"] == {"module": "bay-1/module", "endpoint": "lc01.1"}
    assert out["rear"] == {"module": "bay-1/module", "endpoint": "rear:mtp2.2"}
    assert out["notFibre"] is None and out["screw"] is None


def test_the_far_end_is_a_path(out):
    assert out["farFront"] == "bay-1/module/mtp2/2"
    assert out["farRear"] == "bay-1/module/lc01/1"
    assert out["farUnknown"] is None


def test_rows_say_where_a_fibre_goes(out):
    assert out["labelFront"] == "1 → rear mtp2 · 2"
    assert out["labelRear"] == "2 → front 1"
    assert out["connRear"] == "front 1-3"
    assert out["connFront"] is None and out["connNone"] is None


def test_a_splitters_common_end_fans_out(out):
    # K4: a fan-out `to` (a list) gives an array of far paths, one per branch.
    assert out["farSplit"] == ["bay-1/module/split/1", "bay-1/module/split/2"]
    assert out["labelSplit"] == "1 → split · 1, split · 2"
