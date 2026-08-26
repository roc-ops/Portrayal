"""L21 - what buries a legend is paint, not a bounding rectangle.

The rule reads a placement's skin and tests the mark against each painted node.
Its first version used the contract `size`, and a box is a bad model of a part:
a moulded groove is drawn as an unfilled outline 258mm wide and covers nothing,
and a QSFP cage reserves a band above its aperture for four panel lamps with the
port number printed in the metal between them. Both looked like buried ink.
"""
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402

ROOTS = [str(LIB)]


def covers(boxes, x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes)


def test_an_unfilled_outline_paints_nothing():
    """casa/brand-swoop is the C100G's bezel moulding: one closed curve, `fill`
    none, stroked. The `casa systems` wordmark reads straight through it."""
    boxes = lint.paint_boxes("casa/brand-swoop@1", "default", ROOTS)
    assert boxes == []


def test_a_cage_does_not_own_the_panel_above_its_aperture():
    """common/qsfp28-cage carries the AS7726's four per-port lamps. They are
    holes in the chassis panel, and the port number is printed in the metal
    between the left and right pairs - so the cage must not paint that gap."""
    boxes = lint.paint_boxes("common/qsfp28-cage@3", "default", ROOTS)
    assert boxes, "the skin is readable"
    assert not covers(boxes, 9.25, 2.35), "the metal between the lamp pairs"
    assert covers(boxes, 2.55, 1.5), "a lamp itself still paints"
    assert covers(boxes, 9.25, 8.0), "and so does the aperture"


def test_a_skin_this_reader_cannot_be_sure_of_falls_back_to_the_box():
    """std/micro-usb draws its opening with H and V shorthands, where counting
    numbers in pairs is nonsense. Unsure must mean the whole contracted box, not
    a wrong one: the answer is None and L21 uses `size`."""
    assert lint.paint_boxes("std/micro-usb@1", "default", ROOTS) is None


def test_composed_parts_paint_too():
    """A component composes standard hardware through `parts:`, whose art is not
    in the skin. common/qsfp28-cage wraps a std/qsfp-ganged aperture at 0.25,
    4.2 - miss it and a legend could be declared legible over a hole."""
    boxes = lint.paint_boxes("common/qsfp28-cage@3", "default", ROOTS)
    assert (0.25, 4.2, 0.25 + 18.5, 4.2 + 9.58) in boxes
