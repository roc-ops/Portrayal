"""A plan projection from a FRONT bay is turned half a turn.

A plan is drawn with its own face - a riser's slot wall, a card's bracket - at
the top, where the rear is in every top view. That is right for a module seated
in the rear. The first front-I/O server in the library, the Supermicro
SYS-111E-FDWTR, seats its risers and supplies in the front, and without a turn
its riser bracket lay along the fan row and its cards ran out through the front
wall. `plan: {rotate: 180}` on the bay turns the plan in place and offsets the
occupants of its own bays from the opposite corner.

Reads the built faces rather than a fixture: what it watches is where the
projection LANDS, which is the thing that was wrong.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"


def _groups(name):
    f = DIST / name
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    out = {}
    for tag in re.findall(r"<g [^>]*data-projection=\"1\"[^>]*>", f.read_text()):
        gid = re.search(r'\bid="([^"]+)"', tag).group(1)
        m = re.search(r"translate\(([-\d.]+),([-\d.]+)\)( rotate\(180 )?", tag)
        out[gid] = (float(m.group(1)), float(m.group(2)), bool(m.group(3)))
    assert out, f"{name} carries no projection at all"
    return out


def test_a_front_seated_riser_and_its_cards_are_turned_and_stay_in_the_chassis():
    g = _groups("sys-111e-fdwtr.cards.top.svg")
    depth = 429.0
    for gid in ("riser-lhs-plan", "riser-rhs-plan", "psu-1-plan", "psu-2-plan",
                "riser-lhs-slot-1-plan", "riser-lhs-slot-2-plan", "riser-rhs-slot-3-plan"):
        x, y, turned = g[gid]
        assert turned, f"{gid} is seated in the front and was not turned"
    # the cards run BACK from the front wall: a full-height card plan is 173.8
    # long, and before the turn slot 3's lay 253..427 with its bracket inboard
    # and slots 1 and 2 began at the riser's inboard end
    for gid, length in (("riser-lhs-slot-1-plan", 173.8), ("riser-rhs-slot-3-plan", 173.8)):
        x, y, _ = g[gid]
        assert depth - 3 <= y + length <= depth, (gid, y)


def test_a_rear_seated_riser_is_left_as_it_lies():
    g = _groups("sys-111e-wr.cards.top.svg")
    for gid in ("riser-lhs-plan", "riser-rhs-plan", "psu-1-plan",
                "riser-lhs-slot-1-plan", "riser-rhs-slot-3-plan"):
        x, y, turned = g[gid]
        assert not turned, gid
        assert y <= 1.0, (gid, y)          # at the rear wall, the top of the view
