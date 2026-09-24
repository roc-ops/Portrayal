"""A seated module's `url(#...)` references follow its ids into the bay.

`render.py` has always done this in two passes - collect the renames, then
rewrite every `url(#...)` it can see - because a definition and the reference to
it are two halves of one name. `swap.js` did the first pass only, so a runtime
swap moved `<clipPath id="drive-carrier-25--w0">` to `drive-r0--module--w0` and
left `clip-path="url(#drive-carrier-25--w0)"` behind, dangling.

SVG does not fail a dangling clip-path. It draws the element UNCLIPPED, so the
symptom was a drive carrier rendering its honeycomb vents across the whole face
instead of through three windows - with nothing in the console and no broken
id anywhere a reader would look. 47 of the library's component skins carry a
`url(#...)` reference and every one of them swaps through this path.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/swap-url-refs.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_seated_module_keeps_its_references_pointing_at_its_own_ids():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["ids"] == ["drive-r0--module--w0", "drive-r0--module--hex"], out["ids"]
    assert not out["dangling"], (
        f"{out['dangling']} named by a reference that nothing defines - "
        "SVG draws that unclipped rather than failing")
    assert out["refs"] == [
        "url(#drive-r0--module--w0)",
        "url(#drive-r0--module--hex)",
        # a reference to something outside the component is left alone
        "url(#portrayal-vent)",
    ], out["refs"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_an_optic_seated_in_a_cage_keeps_its_references_too():
    """A cage has no `module` namespace word - `rename(..., segment='')` - and
    the reference pass has to follow the spelling the ids actually took."""
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["cageIds"] == ["port-4-occupant--w0"], out["cageIds"]
    assert out["cageRefs"] == ["url(#port-4-occupant--w0)", "url(#portrayal-vent)"], out["cageRefs"]
    assert not out["cageDangling"], out["cageDangling"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_swapped_modules_tilt_reference_follows_its_facets_id():
    """`data-tilt-on` names the facet a part stands on, by id - same shape as
    `data-cp-on`, and the same bug: `rename()` moved the facet's own id into
    the bay's namespace and left `data-tilt-on` naming the old one. relief.js's
    `tiltOf` looks that id up to find the facet, so a swapped-in module with a
    tilted facet (a Nokia FWLT-B seated in an FX-4 LT bay) got no tilt on its
    parts, no punch through the facet surface, and drew its sloped teeth solid
    with no port openings."""
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["tiltIds"] == [
        "bay-3--module--facet-0",
        "bay-3--module--port-1",
        "bay-3--module--port-1-occupant",
    ], out["tiltIds"]
    assert out["tiltOns"] == [
        "bay-3--module--facet-0",
        "bay-3--module--facet-0",
        # a token naming something outside this component is left alone
        "other-component--facet-0",
    ], out["tiltOns"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_tilted_occupant_seated_straight_into_a_slot_keeps_its_reference():
    """The `segment=''` occupant path - a tilted optic seated directly, not
    composed inside a swapped-in module."""
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["tiltOccupantIds"] == [
        "port-9-occupant--facet-0", "port-9-occupant--tab",
    ], out["tiltOccupantIds"]
    assert out["tiltOccupantOns"] == ["port-9-occupant--facet-0"], out["tiltOccupantOns"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_nested_bays_tilt_reference_follows_the_id_rule_not_the_path_rule():
    """A bay nested inside a swapped module has an idBase and pathBase that
    diverge (`slot-1--module` vs `slot-1/module`); `data-tilt-on` is renamed
    by the id rule, exactly as `data-cp-on` is."""
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["tiltNestedIds"] == [
        "bay-3--module--slot-1--module--facet-0",
        "bay-3--module--slot-1--module--port-1",
    ], out["tiltNestedIds"]
    assert out["tiltNestedOns"] == [
        "bay-3--module--slot-1--module--facet-0",
    ], out["tiltNestedOns"]
