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

    # TRUNCATION IS NOT COMPLETION. The walk leaves that loop two ways and they
    # mean opposite things: an empty frontier is done, a spent `maxDepth` is an
    # override the caller asked for and never got. Reaching everything must
    # report nothing, and being cut short must name what was lost - otherwise
    # 2D shows the swap, 3D does not, and nothing says so.
    assert out["dropped"] == [], (
        f"a walk that reached every level reported {out['dropped']} as dropped. "
        "That is the over-reporting failure: `maxDepth` reached with a non-empty "
        "frontier is not the same as an override going unapplied.")
    # optic-2 is unreached too and NO override names it, so nothing was asked of
    # it and nothing was lost. It is what separates `!seen` from
    # `!seen && named` - without it every unreached bay is also a named one and
    # this assertion cannot tell the two predicates apart.
    assert out["boundedDropped"] == ["slot-1/module/ppm-1/module/optic-1"], (
        f"a truncated walk reported {out['boundedDropped']}. Empty means the "
        "loss is silent, which is the defect. Including optic-2 means it is "
        "reporting every bay it did not reach rather than the ones an override "
        "actually named - a deep drawing nobody swapped anything in would then "
        "announce dropped overrides that never existed.")
