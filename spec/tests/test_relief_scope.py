"""Two viewers on one page, same device, different occupants, both correct.

`relief.js` kept swapped-in faces in a module-level map keyed by URL, shared by
every consumer in the document, with a `clearSvgOverrides()` that took no
argument and emptied all of it. So a before/after comparison of one rack could
not be built in a single page - whichever viewer swapped last won for both, and
either one building or tearing down silently discarded the other's swaps.

The cache beside it is keyed by URL too and that is correct: the same URL really
is the same bytes. An override is the opposite - a per-viewer opinion about what
that URL should render as - and that is the distinction the scope draws.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/relief-scope.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_two_scopes_do_not_share_overrides_or_states():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["bothCorrect"] == ['<svg id="A"/>', '<svg id="B"/>'], \
        "one viewer's override reached the other"
    assert out["bSurvivesATeardown"] == '<svg id="B"/>', \
        "clearing one scope emptied another"
    assert out["aFallsBackToFetch"] == '<svg id="FETCHED"/>', \
        "a cleared scope kept serving its own stale override"

    assert out["statesA"] == [["port-1", "state-on"]]
    assert out["statesB"] == [["port-1", "state-fault"]]

    # the default scope is a scope like any other, which is what keeps the three
    # demo pages working without a line of change
    assert out["defaultIsItsOwnScope"] == ['<svg id="DEFAULT"/>', '<svg id="B"/>']
    assert out["defaultStatesUntouched"] == []
