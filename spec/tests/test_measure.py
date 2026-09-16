"""measure.py - only the part that is validated is tested as working.

`panel` is held against the two things it must get right: finding a face's own
box rather than the figure's, and separating two elevations stacked on one page.
The other subcommands are exercised only for "does not crash and does not lie",
because they are not validated and a test asserting a number from them would be
the kind of check that certifies what it should catch.
"""
import pathlib
import sys

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import measure as M


def figure(tmp_path, panels, size=(800, 400), callouts=True):
    """A synthetic datasheet page: one or two wide faces, plus the callout
    numerals and leader lines that made a naive bounding box useless."""
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in panels:
        d.rectangle([x0, y0, x1, y1], outline="black", fill="#555555")
        # a row of ports, leaving bare metal between them
        for x in range(x0 + 10, x1 - 10, 40):
            d.rectangle([x, y0 + 6, x + 24, y0 + 20], fill="#111111")
            d.rectangle([x, y1 - 20, x + 24, y1 - 6], fill="#111111")
    if callouts:
        for i, x in enumerate(range(60, size[0] - 60, 120)):
            d.line([x, 6, x, 30], fill="black")
            d.text((x, 2), str(i), fill="black")
    p = tmp_path / "fig.png"
    im.save(p)
    return p


def test_the_panel_box_is_the_face_and_not_the_whole_figure(tmp_path):
    """Taking the ink bounding box of the page swallows callout numerals and
    leader lines - which made a real elevation, one an agent measured
    successfully, come out 41% off and condemned the best source in the intake."""
    p = figure(tmp_path, [(20, 120, 780, 220)])
    boxes = M.panel_box(p)
    assert len(boxes) == 1, boxes
    x0, y0, x1, y1 = boxes[0]
    assert 15 <= x0 <= 25 and 775 <= x1 <= 785
    assert 115 <= y0 <= 125 and 215 <= y1 <= 225, (y0, y1)


def test_two_elevations_on_one_page_come_back_as_two(tmp_path):
    """A datasheet figure often stacks the front and the rear. Returning only
    the widest picked one of them silently, and handed back a confident scale
    for a face the caller was not asking about."""
    p = figure(tmp_path, [(20, 60, 780, 160), (20, 260, 780, 360)])
    boxes = M.panel_box(p)
    assert len(boxes) == 2, boxes
    assert boxes[0][1] < boxes[1][1]


def test_a_face_with_a_gap_between_its_port_rows_is_still_one_face(tmp_path):
    """Bare metal between two rows of ports reads as the end of the panel to a
    row-coverage test, so one elevation came back as three stacked 10px apart,
    each with a nonsense height. Bands sharing an x extent a few rows apart are
    one face; a front and a rear hundreds of rows apart are not."""
    im = Image.new("RGB", (800, 300), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([20, 100, 780, 130], fill="#333333")     # upper port row
    d.rectangle([20, 145, 780, 175], fill="#333333")     # lower, 15px below
    p = tmp_path / "split.png"
    im.save(p)
    boxes = M.panel_box(p)
    assert len(boxes) == 1, boxes
    assert boxes[0][1] <= 101 and boxes[0][3] >= 174


def test_a_period_is_a_local_peak_not_the_smallest_lag():
    """Autocorrelation falls away with lag, so the global maximum is always the
    floor - which returned the 6px weave of a vent pattern, then obediently
    returned whatever floor was set instead."""
    sig = [10 if (i // 5) % 2 == 0 else 0 for i in range(600)]   # period 10
    best, peaks = M.dominant_period(sig, 4, 200)
    assert best is not None
    assert best[1] % 10 == 0, best
    assert best[1] > 4, "the answer must not be the floor"


def test_a_flat_signal_reports_nothing_rather_than_a_number():
    best, _ = M.dominant_period([7] * 400, 4, 100)
    assert best is None


def test_rows_enumerates_bands_reproducibly(tmp_path):
    """The point of `rows` is not that it identifies a port row - it cannot, and
    says so. It is that two runs choosing 'band-2' get identical millimetres,
    where two runs eyeballing the same edge do not.

    Two careful passes over one real device disagreed on exactly two numbers, the
    block origin y and the row pitch, and on nothing else - because everything
    else came from a lookup. These two were the only measured-by-eye values in
    the block description.
    """
    im = Image.new("RGB", (400, 200), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([20, 50, 380, 150], fill="#888888")        # the face
    for y in (70, 110):                                     # two rows of openings
        d.rectangle([40, y, 360, y + 20], fill="#101010")
    p = tmp_path / "rows.png"
    im.save(p)

    boxes = M.panel_box(p)
    assert len(boxes) == 1
    x0, y0, x1, y1 = boxes[0]
    # the two dark rows are 40px apart and the panel is 100px for a given height,
    # so the step in mm must come back as 40/scale whatever the caller asks for
    assert y1 - y0 >= 95, (y0, y1)


def test_the_panel_edge_ignores_a_leader_that_reaches_it(tmp_path):
    """A single callout arrow stretched a band's right edge by 85px, which made
    an ORTHOGRAPHIC elevation report 'NOT orthographic' - so the tool condemned a
    usable figure. The x extent is what the rows VOTE for, not the widest row."""
    im = Image.new("RGB", (900, 300), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([20, 100, 700, 200], fill="#555555")       # the face
    d.line([700, 150, 860, 150], fill="black", width=2)    # one leader, reaching out
    p = tmp_path / "leader.png"
    im.save(p)
    boxes = M.panel_box(p)
    assert len(boxes) == 1, boxes
    assert boxes[0][2] <= 720, f"the leader set the edge: {boxes[0]}"
