"""L64: nothing is bolted to, or printed on, a hole.

A vent field is a perforation - the metal is absent - so a legend printed there
is printed on nothing and a jack seated there is mounted to nothing. Every case
this rule was written from was found by a person opening a finished drawing: the
S9600-72XC's 1PPS legend inside a 296mm vent strip, its SYNC and SYS lamps inside
another, and its model name in the middle of a third.

The tests that matter are the two a rule written after the fact usually skips:
does it fire on the ACTUAL defects, and does it stay quiet on everything sitting
right beside them that is already correct - which here means paint order, because
a vent is usually the widest rectangle on a face and most of a faceplate is drawn
on top of one.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]

VENT = {"at": [10.0, 10.0], "size": [60.0, 30.0], "pattern": "vent", "vent": 25}
LAMP = {"ref": "common/led-dot@1", "id": "led-sys", "at": [30.0, 20.0]}   # 2 x 2


def run(decor, placements=(), silkscreen=(), cutouts=()):
    L.WARNINGS.clear()
    doc = {"views": {"front": {
        "panel": {"decor": list(decor), "cutouts": list(cutouts)},
        "components": {"placements": list(placements)},
        "silkscreen": list(silkscreen)}}}
    L.lint_device_air_aperture("t", doc, LIB)
    return [w for w in L.WARNINGS if "L64" in w]


def test_a_lamp_on_a_vent_is_caught():
    """THE DEFECT THIS EXISTS FOR - a 2mm lamp in the middle of a 60x30 hole."""
    hits = run([VENT], [LAMP])
    assert len(hits) == 1, hits
    assert "led-sys" in hits[0] and "100%" in hits[0]


def test_a_legend_on_a_vent_is_caught():
    """The reviewer's second screenshot: a model name printed on perforation."""
    m = {"at": [30.0, 25.0], "text": "S9600-72XC", "font-size": 2.8,
         "anchor": "middle", "for": "chassis"}
    hits = run([VENT], silkscreen=[m])
    assert len(hits) == 1, hits
    assert "printed on nothing" in hits[0]


def test_a_plate_painted_over_the_vent_makes_it_solid_again():
    """PAINT ORDER, WHICH IS THE WHOLE DIFFICULTY. A vent is usually the widest
    rectangle on a face and nearly everything is drawn on top of one. The
    S9600-72XC lays its bottom vent from x=44 to x=406 and then paints the QSFP
    cage panels over it, so port lamps that OVERLAP the vent by area are sitting
    on solid green metal. Asking `does this overlap a vent` reports those; asking
    `what is the topmost thing under this point` does not.

    The same fact rescues the 1PPS jack on that device: its nut washer is drawn
    after the vent, so the jack is mounted on the washer and only its LEGEND,
    which has no washer under it, is over air.
    """
    plate = {"at": [25.0, 15.0], "size": [20.0, 12.0], "fill": "#b0b5bb"}
    assert run([VENT, plate], [LAMP]) == []
    # and the order is what does it - the same plate UNDER the vent rescues
    # nothing, because then the perforation is what a viewer sees
    assert run([plate, VENT], [LAMP]) != []


def test_an_outline_hides_nothing():
    """A stroked rect draws a line, not a surface. Treating it as cover would
    silence anything that happens to sit inside a bezel outline."""
    outline = {"at": [25.0, 15.0], "size": [20.0, 12.0], "stroke": "#000",
               "stroke-width": 0.3}
    assert run([VENT, outline], [LAMP]) != []


def test_a_declared_cutout_is_the_authors_answer():
    """The third remedy: the metal really is punched through the perforation
    here. Saying so with a cutout is what makes that a statement rather than an
    oversight, and it silences the rule."""
    cut = {"id": "led-sys", "at": [29.9, 19.9], "size": [2.2, 2.2]}
    assert run([VENT], [LAMP], cutouts=[cut]) == []


def test_a_part_beside_the_vent_is_silent():
    """The half that matters most. A rule that nags at correct work as well as
    wrong teaches nothing except to switch it off."""
    beside = {"ref": "common/led-dot@1", "id": "led-ok", "at": [4.0, 20.0]}
    assert run([VENT], [beside]) == []


def test_a_part_grazing_the_edge_is_silent():
    """Most of the footprint has to be over air. A lamp overlapping a vent's
    edge by a hair is a measurement question, not a mounting one."""
    grazing = {"ref": "common/led-dot@1", "id": "led-edge", "at": [8.6, 20.0]}
    assert run([VENT], [grazing]) == []


def test_a_face_with_no_vent_is_not_examined():
    plate = {"at": [10.0, 10.0], "size": [60.0, 30.0], "fill": "#b0b5bb"}
    assert run([plate], [LAMP]) == []
