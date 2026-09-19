"""The cable point's arithmetic, checked against hand sums under bare node,
plus the DOM wrapper against a hand-built fake tree (see cable-points.mjs)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/cable-points.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_resolver_sums_the_ancestor_chain():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["bare"] == {"name": "cable", "at": [6.75, 4.25],
                           "dir": "rear", "lift": 0, "out": 0, "z": 0}
    assert out["lifted"]["z"] == 10.0
    # 10.0 of lift on the way up, plus 14.3 the outermost body stands proud
    assert out["stacked"]["z"] == 24.3
    assert out["noDir"]["dir"] is None
    assert out["junk"]["z"] == 0, "a junk lift must be 0, never NaN"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_cable_points_resolves_the_fake_drawing():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    points = {pt["path"]: pt for pt in out["points"]}

    # exactly three connectors survive: A, B, and C (where the boot beat the
    # plug) - not four, which would mean the boot failed to displace the plug
    assert set(points) == {"cage-a", "cage-b", "cage-c/plug/boot"}

    # a single marker resolves to its own position, direction and lift-only z
    assert points["cage-a"]["at"] == [1, 2]
    assert points["cage-a"]["dir"] == "front"
    assert points["cage-a"]["z"] == 2.5

    # no data-cp-dir comes back null, not undefined/missing
    assert points["cage-b"]["dir"] is None
    assert points["cage-b"]["z"] == 0

    # two markers under one connector (plug + boot): the outermost - the
    # boot's, 5mm further out than the plug's - is the one that survives
    assert "cage-c/plug" not in points, \
        "the plug's marker must lose to the boot's when a boot is seated"
    assert points["cage-c/plug/boot"]["z"] == 15
    assert points["cage-c/plug/boot"]["at"] == [3, 3.2]
    assert points["cage-c/plug/boot"]["dir"] == "rear"

    # a drawing with no cable markers at all returns [], not a throw
    assert out["empty"] == []
