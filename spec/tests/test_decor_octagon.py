"""`shape: octagon` - the chamfered window a formed bezel is cut with.

Decor and cutouts could draw a rectangle, a rounded rectangle, a D-sub shell and
a stadium slot, and nothing else. A MaiaEdge PBC's front bezel is cut with two
OCTAGONAL windows - flat top, 45-degree chamfer, short vertical end, chamfer
back, flat bottom - and drawing them as rounded rectangles got the silhouette of
the most recognisable thing on the device wrong. This is the same move `d-sub`
and `slot` already made: one more value the two helpers share, so the vocabulary
means one thing in decor and in cutouts alike.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import render  # noqa: E402


def _pts(d):
    """The path's absolute points, as (x, y) floats."""
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", d)]
    return list(zip(nums[0::2], nums[1::2]))


def test_an_octagon_has_eight_corners():
    p = render._octagon_path(0, 0, 132, 29)
    assert p.startswith("M") and p.rstrip().endswith("Z")
    assert len(_pts(p)) == 8, p


def test_the_chamfer_is_proportional_to_the_short_axis():
    """A squat window and a tall one both want a chamfer that reads as a chamfer.

    Deriving it from the short axis keeps the helper's signature identical to
    `_dsub_path` and `_slot_path`, which is what lets one `shape:` value mean the
    same thing in decor and in cutouts.
    """
    pts = _pts(render._octagon_path(0, 0, 132, 29))
    xs = sorted({round(x, 3) for x, _ in pts})
    ys = sorted({round(y, 3) for _, y in pts})
    c = round(29 * 0.35, 3)
    assert xs == [0.0, c, round(132 - c, 3), 132.0], xs
    assert ys == [0.0, c, round(29 - c, 3), 29.0], ys


def test_it_stays_inside_its_box():
    """The shape a caller asked for is the box it gave, chamfered - never larger."""
    for w, h in ((132, 29), (29, 132), (40, 40)):
        for x, y in _pts(render._octagon_path(10, 5, w, h)):
            assert 10 <= x <= 10 + w and 5 <= y <= 5 + h, (w, h, x, y)


def test_a_square_octagon_is_regular_enough_to_look_like_one():
    pts = _pts(render._octagon_path(0, 0, 40, 40))
    assert len({round(x, 3) for x, _ in pts}) == 4
    assert len({round(y, 3) for _, y in pts}) == 4


def test_decor_and_cutouts_offer_the_same_shapes():
    """One vocabulary, two places. `d-sub` and `slot` are already in both; a
    third value that reached only one of them would be the drift this test
    exists to stop."""
    import json
    s = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    view = s["properties"]["views"]["additionalProperties"]["properties"]
    dec = set(view["panel"]["properties"]["decor"]["items"]["properties"]["shape"]["enum"])
    cut = set(view["panel"]["properties"]["cutouts"]["items"]["properties"]["shape"]["enum"])
    assert "octagon" in dec and "octagon" in cut
    assert dec == cut, (sorted(dec), sorted(cut))
