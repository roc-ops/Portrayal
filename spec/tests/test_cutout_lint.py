"""L63: the rule that existed as a test, where a modelling run never looked.

THREE INDEPENDENT RUNS OF ONE DEVICE MADE THIS EXACT MISTAKE and all three
passed lint. The rule was real and already written - `test_cutout_derivation` -
but a modelling agent does not run the test suite, so it sat somewhere nobody
working on a device would see it. The agent on the third run said it plainly: it
ran lint seven times and never saw the three holes it had drawn wrong.

A rule nobody encounters is not enforcement, it is documentation.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint as L

LIB = [str(ROOT / "library")]


def run(doc):
    with L.collecting() as _found:
        L.lint_device_cutout_derivation("t", doc, LIB)
    return [w for w in _found.warnings if "L63" in w]


def view(placements, cutouts):
    return {"views": {"front": {
        "panel": {"cutouts": list(cutouts)},
        "components": {"placements": list(placements)}}}}


LAMP = {"ref": "common/led-dot@1", "id": "led-1", "at": [30.0, 10.0]}   # 2.0 x 2.0


def test_a_hole_drawn_with_clearance_is_caught():
    """The defect itself: a 2.0mm lamp given a 2.4mm hole, centred - which is
    what 'draw the opening you can see' produces, and what three runs did."""
    hits = run(view([LAMP], [{"id": "led-1", "at": [29.8, 9.8], "size": [2.4, 2.4]}]))
    assert len(hits) == 1, hits
    assert "[2.4, 2.4]" in hits[0] and "[2.0, 2.0]" in hits[0]
    assert "RESTATES" in hits[0]


def test_a_hole_equal_to_the_declared_aperture_is_silent():
    assert run(view([LAMP], [{"id": "led-1", "at": [30.0, 10.0],
                              "size": [2.0, 2.0]}])) == []


def test_a_face_that_punches_nothing_is_not_nagged():
    """Most devices declare no cutouts at all. A rule that demanded them would
    fire on the majority of the library and be switched off."""
    assert run(view([LAMP], [])) == []


def test_a_placement_with_no_matching_cutout_is_not_this_rules_business():
    """L39 already asks whether a part on a punched panel has a hole. This rule
    only compares holes that exist against the parts that own them."""
    assert run(view([LAMP], [{"id": "something-else", "at": [0, 0],
                              "size": [5, 5]}])) == []


def test_a_component_that_declares_no_size_is_skipped_not_guessed_at():
    hits = run(view([{"ref": "nope/missing@9", "id": "x", "at": [0, 0]}],
                    [{"id": "x", "at": [0, 0], "size": [3, 3]}]))
    assert hits == []


def test_the_message_says_what_the_hole_should_be():
    """A warning that only says something is wrong makes the reader go and work
    out the right answer, which is where the mistake came from."""
    hits = run(view([LAMP], [{"id": "led-1", "at": [29.5, 9.5], "size": [3.0, 3.0]}]))
    assert hits
    assert "declares an opening of [2.0, 2.0] at [30.0, 10.0]" in hits[0]
