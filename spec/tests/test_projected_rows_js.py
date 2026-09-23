"""A face lists what it draws, including what only a projection draws.

A seated FHD cassette's back - its MTP bulkheads - is drawn on the rear face
as a projection: `data-of="bay-1/module/mtp1"` and no `data-path`, so a part
seen from two faces stays one part. The explorer's tree was built from
`data-path` alone, which is right for the cassette itself (the front lists
it) and wrong for the bulkheads, which no face draws as a part: they were on
no row anywhere, and a click on one selected the rear cutout it is seen
through. The rules are kit/swap.js's `faceEntries` and `ownerPath`, which
shell.js's buildTree, hit test and select call.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/projected-rows.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_face_lists_the_parts_only_a_projection_draws(out):
    assert out["paths"] == ["chassis", "cutout:back-1", "bay-1/module",
                            "bay-1/module/mtp1", "bay-1/module/mtp2", "psu-1"]
    assert out["projected"] == ["bay-1/module", "bay-1/module/mtp1", "bay-1/module/mtp2"]


def test_a_projection_of_a_drawn_part_is_that_part(out):
    assert out["psuFromPart"], "psu-1 must row from its own data-path, not its projection"


def test_a_projection_nests_under_what_it_is_drawn_in(out):
    assert out["moduleHost"] == "cutout:back-1"


def test_a_click_names_the_nearest_part_or_projected_part(out):
    assert out["clickPlug"] == "bay-1/module/mtp2", "a click on a rear MTP selected something else"
    assert out["clickBezel"] == "bay-1/module"
    assert out["clickHole"] == "cutout:back-1"
    assert out["clickNothing"] is None and out["nul"] is None


def test_a_swapped_back_rows_as_the_built_one_does(out):
    s = out["swap"]
    assert s["applied"] == 1
    assert s["wrap"] == {"id": "bay-1-rear", "transform": "translate(337.955,6.5)",
                         "data-class": "cassette", "data-media": "fiber",
                         "data-projection": "1", "data-of": "bay-1/module"}, \
        "the swapped projection lost its root's class and media, which the tree rows it by"
    assert s["paths"] == ["cutout:back-1", "bay-1/module", "bay-1/module/mtp1", "bay-1/module/mtp2"]
    assert s["leftover"] == []
