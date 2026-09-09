"""A lifted cavity must punch the surface it was lifted onto.

The cavity loop in relief.js skips the FACE punch for a lifted cavity, because it
recesses from a raised part whose own geometry already covers the face. That is
right, and it was only half the job: nothing then punched the raised part, so the
well sat at the correct depth behind an unbroken surface.

smartoptics/dcp-404 is the case that found it - a faceplate standing 44 mm proud
of its chassis with four QSFP cages lifted onto it. A cage is a PURE CAVITY with
no `out` of its own, so it had no raised feature to be seen by and simply
vanished. Its QSFP-DD neighbour looked like it worked and did not: what showed
was its collar, an `out` the lift raised to 45, while its bay was buried exactly
like the other four. That near-miss is why the symptom read as "port 5 renders,
ports 1-4 do not" rather than "no lifted cavity renders", which is what it was.

The rule is a pure function of two rectangles and two depths, so it is checked in
node rather than a browser, the way relief-scope and rack-face-width are.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/cavity-seats-on.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_lifted_cavity_seats_only_on_the_surface_it_was_lifted_onto():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["seatedCage"] is True, (
        "a cage lifted 44 onto a plate standing 44 proud does not seat on it - "
        "this is the DCP-404 case and the whole reason the rule exists"
    )

    # the four ways a cavity is NOT this surface's business
    assert out["unlifted"] is False, \
        "an unlifted cavity is the face's business; punching the plate too holes it for nothing"
    assert out["wrongHeight"] is False, \
        "a cavity lifted to a different height belongs to some other surface"
    assert out["above"] is False, \
        "a cavity lifted higher than this surface stands cannot be seated on it"
    assert out["outsideRight"] is False and out["outsideBelow"] is False, \
        "a cavity outside the surface's footprint never belonged to it"
    assert out["straddles"] is False, \
        "a cavity straddling the edge is not within it; punching would cut past the surface"
    assert out["flatSurface"] is False, \
        "a surface that does not stand proud has nothing to be lifted onto"
    assert out["zeroOnZero"] is False, (
        "an unlifted cavity on a surface standing 0 proud passes every clause but "
        "the lift guard, and must still be rejected - it is punched out of the face"
    )

    assert out["flushCorner"] is True, \
        "a cavity flush with the surface's own bounds is within it, to the tolerance"
