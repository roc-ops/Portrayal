"""One request per face, and a 404 is not a drawing (#52).

`buildFaceRelief` tested whether a view existed with a HEAD and then fetched the
same URL again, so every face cost two round trips. Measured on a six-device
rack: 66 requests of which 30 were duplicates - one HEAD and one GET for each of
five faces of each device. On localhost that is 287 ms of a 7.4 s build; over a
50 ms link it is 30 serial round trips, and it scales with the devices on screen.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/svg-cache-miss.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_missing_face_costs_one_request_and_is_remembered():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["present"] == '<svg id="PRESENT"/>'

    # A 404's BODY IS NOT A DRAWING. svgSource used to call r.text() whatever the
    # status, so a not-found page was handed back to be parsed as SVG and to fail
    # somewhere further from the cause.
    assert out["missing"] == "", "a 404 page came back as if it were a drawing"
    assert out["missingIsFalsy"] is True

    # Empty string rather than null, so every existing caller degrades instead of
    # throwing - viewer3d.js:433 calls .matchAll on this directly.
    assert out["matchAllSurvives"] == 0

    # THE POINT: two URLs, four calls, two requests. No HEAD at all.
    assert out["methods"] == ["GET"], f"a probe survives: {out['methods']}"
    assert out["requests"] == 2, \
        f"asked {out['requests']} times for 2 URLs - the miss is not being memoised"
    assert out["urls"] == ["missing.svg", "present.svg"]
