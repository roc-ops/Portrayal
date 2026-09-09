"""The override walk follows the frontier down, however deep it goes.

`applyAllOverrides` seats what it knows, looks again, and repeats while looking
still finds something new. It cannot know the nested bays up front: which ones
exist is a property of the carrier CURRENTLY seated, so each level only becomes
visible once the level above it has been populated.

It ran ONCE and buried every nested swap in 3D; then TWICE, which covers the two
levels the library actually has. Two was never the number - it was the depth of
today's deepest carrier. The moment a component that declares bays appears in
another's `accepts` list a third level exists, and a pass that stops at two skips
it silently: the 2D drawing swaps, the scene built from the fetched text does
not, and nothing reports anything.

NOTHING IN THE LIBRARY IS THREE LEVELS DEEP TODAY, which is why the fixture is
hand-built and why this test exists at all. Resolved against the built index: 670
`accepts` entries across the 84 nested bays, all of them resolving, and not one
naming a component that itself declares bays. A fix for a depth the library
cannot yet reach would otherwise ship untested.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/nested-bay-depth.mjs"
DIST = ROOT / "library" / "dist"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_walk_reaches_every_level_and_stops_on_its_own():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    # one device bay plus all three nested levels
    assert out["applied"] == 1 + out["levels"], (
        f"the walk applied {out['applied']} of {1 + out['levels']} overrides. "
        "Short means it stopped before the deepest level; over means a bay it "
        "had already applied was revisited, which the `seen` set exists to "
        "prevent and which would re-seat an occupant it just seated."
    )

    # `bounded` runs the same fixture with maxDepth=1 - which is exactly what
    # the two-pass version did - so the difference IS the gap this closes
    assert out["bounded"] == 2, (
        f"bounded to one nested pass the walk applied {out['bounded']}, not 2. "
        "That figure is the old two-pass behaviour and is here to show what the "
        "loop buys; if it moves, the bound has stopped bounding."
    )
    assert out["applied"] > out["bounded"], (
        "the loop reached no deeper than a single nested pass, so it is not "
        "looping at all"
    )


def test_the_library_still_has_no_three_level_carrier():
    """The premise the fixture rests on, checked rather than assumed.

    If this ever fails it is GOOD NEWS - somebody modelled a carrier that
    accepts a carrier - but the hand-built fixture above stops being the only
    coverage, and a real one should be added beside it.
    """
    f = DIST / "components.json"
    if not f.exists():
        pytest.skip("components.json not built")
    comps = json.loads(f.read_text())["components"]
    by_ref = {"%s/%s@%s" % (c["ns"], c["name"], c["major"].lstrip("v")): c
              for c in comps}

    unresolved, deep = [], []
    for ref, c in by_ref.items():
        for bay_id, bay in (c.get("bays") or {}).items():
            for acc in bay.get("accepts") or []:
                target = by_ref.get(acc)
                if target is None:
                    unresolved.append(f"{c['name']}/{bay_id} -> {acc}")
                elif target.get("bays"):
                    deep.append(f"{c['name']}/{bay_id} -> {acc}")

    assert not unresolved, (
        "nested bays naming components the index does not carry, so the "
        f"resolver cannot offer them: {unresolved[:5]}")
    assert not deep, (
        "a carrier now accepts a carrier, so three-level nesting is reachable "
        f"in real data: {deep[:5]}. That is fine - the walk handles it - but "
        "spec/tests/js/nested-bay-depth.mjs is a hand-built fixture, and this "
        "case deserves a real one beside it.")
