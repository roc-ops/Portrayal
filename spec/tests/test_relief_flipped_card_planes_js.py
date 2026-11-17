"""kit/relief.js: a card's plane on a flipped face (the underside) is the half turn of the
plane an unflipped face gives. That holds for the first cut and after a restyle. It holds
centred and off centre, closed and open-backed, with a facet's clear and a shape punch."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/relief-flipped-card-planes.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

# Card y 40 to 70 turned half a turn on a 100 mm card is y 30 to 60. The mark moves to the far corner.
FLAT_STRIP, FLAT_MARK = [0, 40, 25, 70], [1, 1, 8, 8]
TURNED_STRIP, TURNED_MARK = [0, 30, 25, 60], [17, 92, 24, 99]
FLAT_POCKET, TURNED_POCKET = [3, 80, 13, 88], [12, 12, 22, 20]   # the 10 x 8 mm pocket at card x 3, y 80


@pytest.fixture(scope="module")
def o():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


POS = ("centred", "off")
BACK = ("closed", "open")


@pytest.mark.parametrize("back", BACK)
@pytest.mark.parametrize("pos", POS)
def test_the_restyle_re_cut_keeps_the_first_cuts_orientation(o, pos, back):
    r = o[f"{pos}-{back}-restyled"]["flipped"]
    assert r["clear"] == [TURNED_STRIP], "the restyled strip is not turned with the face"
    assert r["mark"] == TURNED_MARK, "the restyled mark is not turned with the face"
    if pos == "centred":
        # a centred card's first cut was right already: a restyle must leave it as it is
        assert r["hash"] == o[f"centred-{back}-first"]["flipped"]["hash"], "a restyle changed the plane"


@pytest.mark.parametrize("back", BACK)
def test_an_off_centre_plane_reads_the_cards_own_art(o, back):
    c = o[f"off-{back}-first"]
    r = c["flipped"]
    assert r["greyFrac"] < 0.1 and r["blueFrac"] > 0.4, "the plane reads the face background"
    assert r["mark"] == TURNED_MARK, "no mark in the corner a centred card shows"
    assert r["clear"] == [TURNED_STRIP], "no strip under the wedge"
    assert c["isHalfTurnOfFlat"], "not the half turn of the unflipped plane"


@pytest.mark.parametrize("pos", POS)
def test_a_shape_punch_replays_mirrored_in_the_open_backed_loop(o, pos):
    c = o[f"{pos}-open-first-pocket"]
    assert c["flipped"]["clear"] == [TURNED_POCKET, TURNED_STRIP], "the shape cut the wrong place"
    assert c["isHalfTurnOfFlat"], "not the half turn of the unflipped plane"


def test_every_plane_on_a_flipped_face_is_the_half_turn_of_the_unflipped_one(o):
    off = [k for k, c in o.items() if not c["isHalfTurnOfFlat"]]
    assert not off, f"not the half turn of the unflipped plane: {off}"


# The same cases on an unflipped face, hashed on the tree before the fixes: they must not move.
GOLDEN = {"plain": "a0563ba6fead597f27cb2fa0", "pocket": "c4638085c09ee6651843ddea"}


def test_an_unflipped_face_gives_what_it_gave(o):
    for key, c in o.items():
        assert c["flat"]["clear"] == [FLAT_STRIP] + ([FLAT_POCKET] if "pocket" in key else []), key
        assert c["flat"]["mark"] == FLAT_MARK, key
        # a plane on an unflipped face is the same wherever the card stands and however it was cut
        assert c["flat"]["hash"] == GOLDEN["pocket" if "pocket" in key else "plain"], key
