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

    # no `out` key at all - a cable point lands on the reference plane via
    # the lift sum alone
    assert out["bare"] == {"name": "cable", "at": [6.75, 4.25],
                           "dir": "rear", "lift": 0, "z": 0}
    assert out["lifted"]["z"] == 10.0
    # 10.0 of lift on the way up; stray `out` keys on the ancestors are not
    # summed and not read from the outermost entry
    assert out["stacked"]["z"] == 10.0
    assert "out" not in out["stacked"]
    assert out["noDir"]["dir"] is None
    assert out["junk"]["z"] == 0, "a junk lift must be 0, never NaN"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_cable_points_resolves_the_fake_drawing():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    points = {pt["path"]: pt for pt in out["points"]}

    # every connector survives exactly once, at the path that won it
    assert set(points) == {
        "cage-a", "cage-b", "cage-c/plug/boot",
        "sfp-lc/tx", "sfp-lc/rx", "sfp-1", "sfp-10",
        "cage-g/plug/boot",
    }
    assert "out" not in points["cage-a"]

    # a single marker resolves to its own position, direction and lift-only z
    assert points["cage-a"]["at"] == [1, 2]
    assert points["cage-a"]["dir"] == "front"
    assert points["cage-a"]["z"] == 2.5

    # no data-cp-dir comes back null, not undefined/missing
    assert points["cage-b"]["dir"] is None
    assert points["cage-b"]["z"] == 0

    # two markers on one chain (plug + boot): the outermost - the boot's,
    # 5mm further out than the plug's - is the one that survives
    assert "cage-c/plug" not in points, \
        "the plug's marker must lose to the boot's when a boot is seated"
    assert points["cage-c/plug/boot"]["z"] == 5
    assert points["cage-c/plug/boot"]["at"] == [3, 3.2]
    assert points["cage-c/plug/boot"]["dir"] == "rear"

    # two markers under a SHARED LEADING SEGMENT that are NOT on one chain
    # (siblings, "sfp-lc/tx" and "sfp-lc/rx") must both survive - grouping by
    # leading segment alone would wrongly collapse an LC duplex to one point
    assert points["sfp-lc/tx"]["z"] == 3
    assert points["sfp-lc/rx"]["z"] == 4

    # "sfp-1" is not a chain-prefix of "sfp-10" - the trailing "/" boundary
    # must keep them apart
    assert set(points) >= {"sfp-1", "sfp-10"}

    # an exact z tie on one chain (plug vs boot) breaks on the longer,
    # deeper path - the boot's - not on iteration order
    assert "cage-g/plug" not in points, \
        "a z tie must break toward the deeper (boot) path, not the plug's"
    assert points["cage-g/plug/boot"]["z"] == 0

    # a drawing with no cable markers at all returns [], not a throw
    assert out["empty"] == []
