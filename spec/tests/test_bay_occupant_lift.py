"""What a bay opening is off the panel, the module seated in it is too.

`relief.js`'s `liftOf` sums `data-z-lift` up the ANCESTOR chain, so a module
seated in a bay on a raised carrier has to end up under that lift or it sits at
the panel plane behind unbroken metal - `smartoptics/dcp-404`'s blank-face
failure, in a place restructuring a skin cannot reach.

HOW it ends up there has already changed once. While a component bay was a bare
rect with its occupant appended elsewhere in the instance group, render.py
COPIED the opening's lift onto the occupant. Now that a component bay is a group
holding both, the lift is declared once on the group and the occupant INHERITS
it - and copying as well would count it twice, which is the defect
test_composed_lift_not_doubled.py exists to catch.

So this asserts the invariant and not the mechanism: whatever the shape, the
occupant's effective lift is the bay's. A test written against the copy failed
the moment the shape improved, while the thing it was guarding never broke.

The failure is invisible to every other gate. The contract is right, the skin is
right, lint and devicelock pass, and the compiled 2D drawing looks correct; only
the 3D view is wrong. Hence a test on the compiled output.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"

# component drawing, instance id, and the bays whose openings declare a lift
LIFTED_BAYS = {
    "smartoptics--dcp-f-a22--v1--default.svg": ("dcp-f-a22", ["ppm-1", "ppm-2"]),
}


def lift_of(el, parent):
    """relief.js's liftOf: the sum up the ancestor chain, this node included."""
    total, node = 0.0, el
    while node is not None:
        total += float(node.get("data-z-lift") or 0)
        node = parent.get(node)
    return total


@pytest.mark.parametrize("fname,inst,bays", [(f, i, b) for f, (i, b) in sorted(LIFTED_BAYS.items())])
def test_a_lifted_bays_occupant_is_lifted_with_it(fname, inst, bays):
    f = DIST / fname
    if not f.exists():
        pytest.skip(f"{fname} not built")
    root = ET.parse(f).getroot()
    parent = {c: p for p in root.iter() for c in p}
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}

    for bay in bays:
        bay_el = by_id.get(f"{inst}--{bay}")
        assert bay_el is not None, f"{fname}: no bay element {inst}--{bay}"
        declared = lift_of(bay_el, parent)
        assert declared, (
            f"{fname}: {bay} sits at no lift at all, so this test is asserting "
            "nothing. Either the contract lost its relief feature or the feature "
            "stopped reaching the node."
        )
        occ = by_id.get(f"{inst}--{bay}--module")
        assert occ is not None, (
            f"{fname}: bay {bay} has no seated module, so nothing can be "
            "checked. Give the bay a `default:`."
        )
        got = lift_of(occ, parent)
        assert got == declared, (
            f"{fname}: {bay} sits at {declared} but the module seated in it is "
            f"at {got}. Under-lifted it sits behind the raised plate and vanishes "
            "from 3D; over-lifted the carrier's lift has been counted twice."
        )


@pytest.mark.parametrize("fname,inst,bays", [(f, i, b) for f, (i, b) in sorted(LIFTED_BAYS.items())])
def test_a_bay_holds_its_opening_and_its_occupant(fname, inst, bays):
    """The shape everything downstream assumes, on a component as on a device.

    `kit/shell.js` reads occupancy as `el.querySelector('[data-ref]')` - a
    DESCENDANT query - and `swap.js` replaces an occupant with
    `g.querySelector('#<id>--module')?.remove()` then `g.appendChild(...)`.
    Against a bare rect with the occupant somewhere else, the first always says
    "open" and the second removes nothing and appends into a `<rect>`, where SVG
    will not draw it.
    """
    f = DIST / fname
    if not f.exists():
        pytest.skip(f"{fname} not built")
    root = ET.parse(f).getroot()
    parent = {c: p for p in root.iter() for c in p}
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}

    for bay in bays:
        bay_el = by_id.get(f"{inst}--{bay}")
        assert bay_el is not None, f"{fname}: no bay element {inst}--{bay}"
        assert bay_el.tag.endswith("}g"), (
            f"{fname}: {bay} is a <{bay_el.tag.split('}')[-1]}>, not a group. A "
            "swap appends the new occupant into this node; SVG draws nothing "
            "appended to a rect."
        )
        assert bay_el.get("data-class") == "bay"
        opening = by_id.get(f"{inst}--{bay}--opening")
        assert opening is not None and parent.get(opening) is bay_el, (
            f"{fname}: {bay}'s opening is not inside it"
        )
        occ = by_id.get(f"{inst}--{bay}--module")
        assert occ is not None and parent.get(occ) is bay_el, (
            f"{fname}: {bay}'s occupant is not inside it, so the tree will read "
            "the bay as open and a swap will not replace it"
        )
        assert occ.get("data-ref"), f"{fname}: {bay}'s occupant names no ref"


def test_the_a22s_two_blocks_carry_different_relief():
    """The whole reason the face is two nodes rather than one.

    `profile-y` reads down the height and knows nothing about x, so one node
    cannot slope at one end and stand square at the other. If these two ever
    collapse into one node, or the square end acquires a profile, the ramp runs
    over ppm-1 - which opens at y 2.5, inside the ramp - and the bay is cut
    through by a slope no module can seat against.
    """
    f = DIST / "smartoptics--dcp-f-a22--v1--default.svg"
    if not f.exists():
        pytest.skip("dcp-f-a22 not built")
    by_id = {el.get("id"): el for el in ET.parse(f).getroot().iter() if el.get("id")}

    ramp = by_id.get("dcp-f-a22--body-ramp")
    square = by_id.get("dcp-f-a22--body-square")
    assert ramp is not None and square is not None, "the A22 face is not two blocks any more"

    assert ramp.get("data-z-profile-y"), "the ramp block lost its slope"
    assert not square.get("data-z-profile-y"), (
        "the square block acquired a profile. ppm-1 opens at y 2.5 and the ramp "
        "runs to 8.9, so a profile here cuts through the top 6.4 of bay 1."
    )
    out = [ramp.get("data-z-out"), square.get("data-z-out")]
    assert all(out), "both blocks must stand proud, or they are not one plate"
    assert out[0] == out[1], (
        "the two blocks stand proud by different amounts (%s vs %s). They are "
        "welded halves of one plate; a step between them is not a shape the "
        "hardware has." % tuple(out)
    )
