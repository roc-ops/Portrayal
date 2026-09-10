"""A frontier can hold a carrier and something seated inside it.

THE FACE ARRIVES ALREADY NESTED. `render.py` seats every configured `default:`
at build time, so a compiled drawing holds its nesting before any override is
applied - 248 level-2 bay groups across 52 files in the dist. `nestedBays` walks
`[data-class="bay"]` and level-limits nothing, so one call hands back every level
at once.

`applyAllOverrides` therefore cannot treat a frontier as one level. Applied
together, a deeper bay's `at` was read off the carrier the shallower one is about
to replace, and `seen` then guarantees it is never re-derived: the occupant lands
where the OLD carrier's bay was.

THE PREMISE THIS CORRECTS WAS MINE. #225 said, in the PR and in
`nested-bay-depth.mjs`'s own docstring, that each level only becomes visible once
the level above it has been populated. That holds for nesting an override
CREATES and fails for nesting the face already has - which is most of it.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/nested-bay-frontier.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_deeper_bay_waits_for_the_carrier_above_it_to_settle():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["ppm1"] == "so/carrier-b2@1", (
        "the level-2 carrier was not replaced, so nothing below it can be stale "
        f"and this test is asserting nothing: {out['ppm1']}")

    # THE NUMBER THAT GOES WRONG. carrier-b2 declares optic-1 at [7,3]; carrier-b,
    # the one just replaced, declared it at [1,1]. `translate(1,1)` means the
    # level-3 bay was resolved against the carrier that is no longer there.
    assert out["opticTransform"] == "translate(7,3)", (
        f"the seated occupant is at {out['opticTransform']}, not translate(7,3). "
        "Its bay was derived before the carrier above it was replaced, and "
        "`seen` will never let it be derived again.")

    assert out["applied"] == 3

    # ppm-1 and ppm-10 are SIBLINGS - same level, and the second's path is a
    # string prefix of nothing, but the first's path IS a string prefix of the
    # second's. Without the `+ '/'` separator in the descendant test, ppm-10
    # reads as nested inside ppm-1 and is deferred a pass; bounded to one pass
    # there is no next one, and the override is silently dropped.
    assert out["boundedApplied"] == 2, (
        f"one bounded pass applied {out['boundedApplied']} of 2 same-level bays. "
        "1 means a sibling was mistaken for a descendant (the `+ '/'` guard); "
        "3 means the levels were not separated at all.")
