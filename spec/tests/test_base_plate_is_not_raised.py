"""A component's base plate must never be raised over its own skin.

render.py raises a relief node carrying `out` (or cyl/bar/uhandle/dome) to the
end of the instance group, so that a bezel standing proud paints over the parts
the component composes. That is right for a bezel and catastrophic for a BASE
PLATE, which is the thing every other mark in the skin is drawn on.

The guard for it read "only when there ARE composed parts - otherwise this
reorders the skin's own draw order and a raised base plate paints over its own
detail". It named the failure and then guarded only half of it. With parts, the
raise fired anyway: smartoptics/dcp-404 declares `out: 2.5` on `body`, composes
cages, lamps and warning triangles, and shipped with its plate moved to the end
of the group - covering every vent and every silkscreen line on the faceplate.

It was invisible to every gate. Lint passed, devicelock passed, the whole suite
passed, and the component's own skin file was correct all along; only the
compiled output was wrong, and only a person looking at the picture caught it.
Hence this test, which looks at the compiled output.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"

# id suffix of the first drawable element in each skin, i.e. its base plate
BASE_PLATE = {
    "smartoptics--dcp-404--v1--default.svg": "body",
    "common--lc-duplex-adapter--v3--default.svg": "bezel",
}

NONDRAWING = ("title", "defs", "style", "desc", "metadata")


def top_level_ids(text):
    """Ids of the instance group's direct children, in draw order."""
    out = []
    for m in re.finditer(r"\n    <(\w+)([^>]*?)/?>", text):
        tag, attrs = m.group(1), m.group(2)
        if tag in NONDRAWING:
            continue
        idm = re.search(r'id="([^"]+)"', attrs)
        if idm:
            out.append(idm.group(1))
    return out


@pytest.mark.parametrize("fname,plate", sorted(BASE_PLATE.items()))
def test_the_base_plate_is_drawn_first(fname, plate):
    f = DIST / fname
    if not f.exists():
        pytest.skip(f"{fname} not built")
    ids = top_level_ids(f.read_text())
    assert ids, f"{fname}: no drawable children found"
    want = [i for i in ids if i.endswith(f"--{plate}")]
    assert want, f"{fname}: no element ending --{plate}; ids were {ids}"
    assert ids[0] == want[0], (
        f"{fname}: base plate {want[0]} is drawn at index {ids.index(want[0])} "
        f"of {len(ids)} instead of first. Everything before it is painted over. "
        f"Draw order: {ids}"
    )


def test_the_dcp_404_still_shows_its_silkscreen_and_vents():
    """The symptom, stated as the user saw it: the printing went missing."""
    f = DIST / "smartoptics--dcp-404--v1--default.svg"
    if not f.exists():
        pytest.skip("dcp-404 not built")
    ids = top_level_ids(f.read_text())
    body = ids.index("dcp-404--body")
    face = [i for i in ids
            if "silkscreen" in i or i.startswith("dcp-404--vent")]
    # ESTABLISH THE SUBJECT BEFORE ASSERTING ABOUT ITS ORDER. Without this the
    # test passes for the wrong reason: if the vents and the silkscreen were
    # renamed or dropped from the skin, nothing would match, `painted_over`
    # would be empty, and a face with no printing at all would read as a pass -
    # the very symptom this test exists to catch.
    assert face, (
        "no vent or silkscreen element found on the DCP-404 at all; this test "
        f"cannot say anything about draw order. Draw order: {ids}"
    )
    painted_over = [i for i in ids[:body] if i in face]
    assert not painted_over, (
        "the DCP-404's plate is in front of its own face: "
        f"{painted_over} are drawn before dcp-404--body and so are invisible"
    )
