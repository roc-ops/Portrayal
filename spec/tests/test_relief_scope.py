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

    # The first pass at this scoped the overrides and the lamp states and left
    # the raster density and the FRU path set module-level - the closing note on
    # roc-ops/Portrayal#31 said as much, and a downstream consumer came back still blocked. A
    # scope that owns half a viewer's state is a scope you cannot reason about.
    assert out["densitiesStaySeparate"] == [8, 4], \
        "the second configureRelief reclaimed the first scope's density"
    assert out["fruSetsStaySeparate"] == [["psu-0"], ["fan-0"]], \
        "one viewer's FRU path set reached the other"
    assert out["cropHonoursItsDensity"] == [80, 40], \
        "crop still took its density from the module instead of its caller"

    # A cover hides what is behind it - that is why it is on the device and why
    # someone wants it off. Taking one off is a per-viewer opinion like a swap or
    # a lit lamp, so it gets a seat per holder for the same reason. The hiding
    # itself needs a DOM and is checked in test_pull_3d.py.
    assert out["pullIsPerViewer"] == [["psu-1"], ["fan-0", "psu-2"]], \
        "one viewer's pulled cover reached another's scene"
    assert out["clearingOneLeavesTheOther"] == [[], ["fan-0", "psu-2"]], \
        "putting one viewer's covers back stripped another's"
    assert out["defaultPullIsEmpty"] == []

    # A cage swap (an optic chosen for a port) rewrites a fetched face's text
    # through this same per-scope map, exactly as a bay swap does - see
    # applyBayOverrides in kit/viewer3d.js. The script runs that cage path
    # itself (applyOccupantOverrides on the face viewer A fetched, stored in
    # A's scope); viewer B must still read the build's optic off the same URL.
    assert out["cageSwapApplied"] == 1, "the cage path seated nothing - vacuous"
    assert out["cageSwapStaysInItsScope"] == ["generic/sfp-lc-simplex@2", "generic/sfp-lc@1"], \
        "a cage swap set in one viewer reached another's face text"
