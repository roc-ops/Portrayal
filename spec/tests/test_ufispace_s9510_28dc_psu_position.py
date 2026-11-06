"""The S9510-28DC's two power-supply bays sit where UfiSpace's straight-on front photograph puts them.

The photograph is 520 px wide for the 440 mm face, so a pixel is 0.87 mm. Read from it, the left edge of
the first supply module is 5.2 mm from the chassis edge and the second is 64.2 mm, a step of 59.0 mm. The
drawn anchors are 4.5 mm and 63.2 mm, a step of 58.7 mm. A position is the difference of two edges, each
read to one pixel, so it carries 1.2 mm of error. Both anchors differ from the photograph by less than
that, so the photograph does not call for a move and the anchors stay; the layout note says so.
"""
import functools
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "ufispace" / "s9510-28dc" / "device.yaml"

PHOTOGRAPH_ERROR_MM = 1.2
# Left edge of each supply module on the photograph, from the chassis edge, in mm.
PHOTO_LEFT_EDGE_MM = {"psu-0": 5.2, "psu-1": 64.2}
CHECKED_ANCHOR_MM = {"psu-0": 4.5, "psu-1": 63.2}


@functools.lru_cache(maxsize=None)
def _device():
    return yaml.safe_load(DEVICE.read_text())


def _bays():
    return {b["id"]: b for b in _device()["views"]["front"]["components"]["bays"]}


def test_each_supply_bay_is_at_the_checked_anchor():
    """psu-0 is at 4.5 mm and psu-1 at 63.2 mm from the left of the face."""
    bays = _bays()
    for bay, anchor in CHECKED_ANCHOR_MM.items():
        assert bays[bay]["at"][0] == anchor, bay


def test_each_anchor_is_within_the_photographs_error_of_the_photograph():
    """The photograph's reading and the drawn anchor differ by less than its 1.2 mm measuring error."""
    bays = _bays()
    for bay, measured in PHOTO_LEFT_EDGE_MM.items():
        assert abs(bays[bay]["at"][0] - measured) <= PHOTOGRAPH_ERROR_MM, bay


def test_the_layout_note_says_the_anchors_were_checked_against_the_photograph():
    """The layout note records the check, the photograph's error and what it measured."""
    text = " ".join(_device()["provenance"]["layout"]["note"].split())
    assert "PSU bay anchors checked against" in text
    assert "straight-on front photograph" in text
    assert "within 1.2 mm" in text
    assert "5.2 mm" in text and "64.2 mm" in text
