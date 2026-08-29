"""L61: a legend that is ALMOST centred on the thing it names.

Written after a reviewer opened a finished drawing in an editor and found eight
defects no rule here could see - a lamp column 1.35mm high on its port, a legend
row centred on nothing, five status labels 0.21mm high on their lamps. All of it
arithmetic, none of it visible at page scale, all of it obvious at 4x.

The tests that matter are the two that a rule written after the fact usually
skips: does it fire on the ACTUAL defects, and does it stay quiet on the
deliberate placements sitting right beside them.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]


def run(doc):
    L.WARNINGS.clear()
    L.lint_device_alignment("t", doc, LIB)
    return [w for w in L.WARNINGS if "L61" in w]


def view(placements, silkscreen=()):
    return {"views": {"front": {
        "components": {"placements": list(placements)},
        "silkscreen": list(silkscreen)}}}


PORT = {"ref": "std/qsfp-dd@1", "id": "port-1", "at": [38.3, 12.0]}   # 19.0 x 10.0


def test_a_lamp_offset_from_its_port_is_caught():
    """THE DEFECT THIS EXISTS FOR. A 10.7mm lamp column centres on a 10.0mm port
    at dy -0.35. It was written at -1.7, so every lamp on the face sat 1.35mm
    high - which a reviewer described, to two decimal places, as 'a sixteenth of
    an inch too high on both rows'."""
    # `common/led-dot@1` is 2.0 x 2.0 and is in every checkout. An earlier
    # version of this test named a lane-column part that one device happened to
    # create; the next run of that device named it something else and the test
    # failed for a reason unrelated to the rule. Twice.
    # port centre is 17.0; a 2.0mm lamp centred there sits at 16.0, so 14.65 is
    # the same 1.35mm miss a reviewer found by eye.
    lamp = {"ref": "common/led-dot@1", "id": "led-p1",
            "at": [35.75, 14.65], "for": "port-1"}
    hits = run(view([PORT, lamp]))
    assert len(hits) == 1, hits
    assert "1.35mm off centre vertically" in hits[0]
    assert "led-p1" in hits[0]


def test_the_same_lamp_centred_is_silent():
    lamp = {"ref": "common/led-dot@1", "id": "led-p1",
            "at": [35.75, 16.0], "for": "port-1"}
    assert run(view([PORT, lamp])) == []


def test_a_legend_between_two_parts_is_measured_against_their_middle():
    """The numerals and arrows in the gap between two rows of ports. Their target
    is the middle of what they span, which nothing else in the file states - and
    the reason a legend row came to be centred on nothing at all."""
    lower = {"ref": "std/qsfp-dd@1", "id": "port-2", "at": [38.3, 26.5]}
    # gap runs 22.0..26.5; the pair's union centres at 24.25
    low = {"at": [47.8, 24.8], "path": "M -1 0.5 L 1 0.5 L 0 -0.5 Z",
           "for": ["port-1", "port-2"]}
    hits = run(view([PORT, lower], [low]))
    assert len(hits) == 1, hits
    assert "0.55mm off centre vertically" in hits[0]

    centred = dict(low, at=[47.8, 24.25])
    assert run(view([PORT, lower], [centred])) == []


def test_a_legend_deliberately_somewhere_else_is_left_alone():
    """A column heading under two rows of jacks, `Reset` beneath its button - not
    reaching for a centre, and a rule that nags about those gets switched off."""
    far = {"at": [47.8, 60.0], "text": "10G Mgmt", "font-size": 1.6,
           "anchor": "middle", "for": "port-1"}
    assert run(view([PORT], [far])) == []


def test_dead_centre_is_silent_and_so_is_a_gross_miss():
    """The band is deliberately narrow: below it the difference cannot be seen,
    above it the mark is not trying to line up at all."""
    lamp = {"ref": "common/led-dot@1", "id": "led-a", "at": [30.0, 15.97],
            "for": "port-1"}                     # 0.03mm out - under the floor
    assert run(view([PORT, lamp])) == []
    lamp = {"ref": "common/led-dot@1", "id": "led-b", "at": [30.0, 10.0],
            "for": "port-1"}                     # 6mm out - plainly elsewhere
    assert run(view([PORT, lamp])) == []


def test_a_mark_naming_a_part_that_is_not_placed_is_ignored():
    """`for:` may name a target in another view, or something not modelled yet.
    Neither is this rule's business."""
    m = {"at": [10.0, 10.0], "text": "X", "font-size": 2.0, "for": "nothing-here"}
    assert run(view([PORT], [m])) == []


def test_a_curved_path_is_skipped_rather_than_guessed_at():
    """The box reader handles M/L/Z with absolute coordinates, which is what the
    library uses. Anything with an arc gets no opinion rather than a wrong one."""
    assert L._path_box({"path": "M 0 0 A 1 1 0 1 0 2 0"}) is None
    assert L._path_box({"path": "M -1 0.5 L 1 0.5 L 0 -0.5 Z"}) == (-1.0, -0.5, 1.0, 0.5)


def test_a_two_line_legend_is_centred_as_a_block():
    """`GNSS` over `ANT` is ONE label, straddling the jack it names - 1.29mm
    above the centre and 1.31mm below it. Measuring each line alone reported the
    same correct legend twice as wrong, and across the corpus that shape was 642
    of 1287 warnings: half this rule's backlog, every one of them a label a
    person would have to open, measure and dismiss.

    What has to sit on the target's centre is the SET's midpoint.
    """
    # beside the port, so the rule is measuring the axis it means to: both lines
    # 1.30mm off the jack's centre, one above and one below.
    a = {"at": [34.0, 16.196], "text": "GNSS", "font-size": 1.6,
         "anchor": "middle", "for": "port-1"}
    b = {"at": [34.0, 18.796], "text": "ANT", "font-size": 1.6,
         "anchor": "middle", "for": "port-1"}
    assert run(view([PORT], [a, b])) == []
    # and each line ALONE is still a slip, so this is the set rule doing the
    # work rather than the offsets being too small to report
    assert run(view([PORT], [a])) != []


def test_a_lopsided_pair_is_still_reported():
    """THE HALF THAT KEEPS THE RULE HONEST. The S8901 carries two arrow lamps
    per port, 1.38mm out one way and 2.22mm the other. That midpoint is 0.42mm
    off centre, so the pair is not straddling anything - it is simply askew, and
    it stays reported."""
    a = {"at": [34.0, 16.116], "text": "L", "font-size": 1.6,
         "anchor": "middle", "for": "port-1"}     # 1.38 above
    b = {"at": [34.0, 19.716], "text": "R", "font-size": 1.6,
         "anchor": "middle", "for": "port-1"}     # 2.22 below
    assert run(view([PORT], [a, b])) != []
