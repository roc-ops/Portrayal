"""A cage-only override must not be skipped by the view guard.

`applyBayOverrides` (kit/viewer3d.js) rewrites a fetched face's text before
the 3D scene is built from it, but only for the views an override map
actually touches - fetching and re-parsing every view of every config on
every build would be wasteful. That cheap guard used to look only at
`devIndex.bays`, so a cage-only override (an optic chosen for a port) named
no bay in any view, every view was skipped, and the swap that reached the 2D
DOM (shell.js) never reached the 3D one. `viewsToRewrite` is that guard,
extracted to `kit/swap.js` so it can be exercised under node without a
`three` import.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/views-to-rewrite.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_views_to_rewrite():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["cageOnly"] == ["rear-0"], \
        "a cage-only override must rewrite the view that cage is in"
    assert out["bayOnly"] == ["front-1"], \
        "a bay-only override changed behaviour"
    assert out["noBaysDevice"] == ["front-0"], \
        "a device with cages and no bays anywhere must not be skipped outright"
    assert out["nested"] == ["front-0", "front-1"], \
        "a nested override must rewrite every view with bays, not views with only cages"
    assert out["miss"] == []
    assert out["empty"] == []
    assert out["emptyDevIndex"] == []
    assert out["undefinedDevIndex"] == []
