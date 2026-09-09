"""What a bay opening is off the panel, the module seated in it is too.

`relief.js`'s `liftOf` sums `data-z-lift` up the ANCESTOR chain. A component
bay's occupant is appended to the INSTANCE group rather than beside its opening
- deliberately, so the bay's `at` stays a plain local coordinate with no
composed transform - so it inherits nothing from whatever group the opening
lives in. On a carrier whose plate stands proud that buries it.

smartoptics/dcp-f-a22 is the case that found it: two PPM bays in a block 44 off
the chassis, with the modules seated in them sitting at the panel plane behind
unbroken metal. That is smartoptics/dcp-404's blank-face failure again, and it
is the one place restructuring the skin cannot reach - the fix has to be in
render.py, which copies the opening's lift onto the occupant.

The failure is invisible to every other gate. The contract is right, the skin is
right, lint and devicelock pass, and the compiled 2D drawing looks correct;
only the 3D view is wrong. Hence a test on the compiled output.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"

# component, and the bays whose openings declare a lift
LIFTED_BAYS = {
    "smartoptics--dcp-f-a22--v1--default.svg": ("dcp-f-a22", ["ppm-1", "ppm-2"]),
}


def attrs_of(text, el_id):
    m = re.search(r'<\w+([^>]*\bid="%s"[^>]*)>' % re.escape(el_id), text)
    return m.group(1) if m else None


@pytest.mark.parametrize("fname,inst,bays", [(f, i, b) for f, (i, b) in sorted(LIFTED_BAYS.items())])
def test_a_lifted_bays_occupant_is_lifted_with_it(fname, inst, bays):
    f = DIST / fname
    if not f.exists():
        pytest.skip(f"{fname} not built")
    text = f.read_text()
    for bay in bays:
        opening = attrs_of(text, f"{inst}--{bay}")
        assert opening, f"{fname}: no opening element {inst}--{bay}"
        lift = re.search(r'data-z-lift="([^"]+)"', opening)
        assert lift, (
            f"{fname}: {bay}'s opening declares no data-z-lift, so this test is "
            "asserting nothing. Either the contract lost its relief feature or "
            "the feature stopped reaching the node."
        )
        occ = attrs_of(text, f"{inst}--{bay}--module")
        assert occ, (
            f"{fname}: bay {bay} has no seated module, so the propagation cannot "
            "be checked. Give the bay a `default:`."
        )
        got = re.search(r'data-z-lift="([^"]+)"', occ)
        assert got and got.group(1) == lift.group(1), (
            f"{fname}: {bay}'s opening is lifted {lift.group(1)} but the module "
            f"seated in it carries {got.group(1) if got else 'no lift'}. The "
            "module will sit at the panel plane behind the raised plate and "
            "vanish from 3D."
        )


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
    text = f.read_text()

    ramp = attrs_of(text, "dcp-f-a22--body-ramp")
    square = attrs_of(text, "dcp-f-a22--body-square")
    assert ramp and square, "the A22 face is not two blocks any more"

    assert 'data-z-profile-y="' in ramp, "the ramp block lost its slope"
    assert 'data-z-profile-y="' not in square, (
        "the square block acquired a profile. ppm-1 opens at y 2.5 and the ramp "
        "runs to 8.9, so a profile here cuts through the top 6.4 of bay 1."
    )
    out = [re.search(r'data-z-out="([^"]+)"', a) for a in (ramp, square)]
    assert all(out), "both blocks must stand proud, or they are not one plate"
    assert out[0].group(1) == out[1].group(1), (
        "the two blocks stand proud by different amounts (%s vs %s). They are "
        "welded halves of one plate; a step between them is not a shape the "
        "hardware has." % (out[0].group(1), out[1].group(1))
    )
