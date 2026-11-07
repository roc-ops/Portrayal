"""The holes of the FS-PDUBK plate as FS's dimensioned render draws them (#939).

The render on the FS-PDUBK product page (the plate face-on, 135 across and 88.4
high, the keyhole and square-hole pitch dimensioned 31.5) shows three keyholes
and, offset half a pitch from them, four columns of square holes in two rows:
square, keyhole, square, keyhole, square, keyhole, square. There is no fourth
keyhole; the plate's far end carries the last column of squares and turns into
its lip. A pixel measurement of the render at its own pitch scale (194 px to
31.5 mm, 6.16 px/mm) puts the keyholes 39.0, 70.5 and 102.0 from the foot's end
of the plate and the squares 23.3, 54.8, 86.3 and 117.8.

Read here from the BUILT drawing (library/dist), not from the constants in the
device: the plate's path in the left and the right view, in both mounting options.
The tolerance is 1.5 mm: the render's two scales (along the plate and across it)
differ by 6 per cent and the plate's edge is read to a few pixels, so a position
is good to about a millimetre; 1.5 keeps a column from moving a whole pitch.
"""
import re
from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parents[2] / "library" / "dist"
PLATE = 135.0
TOL = 1.5
PITCH = 31.5
KEYHOLES = [39.0, 70.5, 102.0]
SQUARES = [23.3, 54.8, 86.3, 117.8]
ROWS = [10.3, 88.4 - 10.3]

# (configuration, view) -> the end the foot is at. `left` is drawn with the rear
# of the rack at its left, `right` with the front there; option 1 (front) has
# its foot at the rear end of the plate, option 2 (rear) at the front end.
FOOT = {
    ("front", "left"): "left",
    ("front", "right"): "right",
    ("rear", "left"): "right",
    ("rear", "right"): "left",
}


def plate_path(cfg, view):
    """The d of the plate's evenodd path in a built view, and its element id."""
    svg = (DIST / f"fs-pdubk.{cfg}.{view}.svg").read_text()
    m = re.search(r'<path id="(plate(?:-face)?-(?:front|rear))--(?:floor|face)"[^>]* d="([^"]+)"', svg)
    assert m, f"no plate path in the {cfg} {view} view"
    return m.group(2)


def holes(d):
    """(keyhole centres across, [(square centre across, square centre down)])."""
    keyholes, squares = [], []
    for sub in re.split(r"(?=M )", d)[2:]:  # the first subpath is the sheet's outline
        m = re.match(r"M ([\d.]+) ([\d.]+) (h|A)", sub.strip())
        assert m, sub
        x, y = float(m.group(1)), float(m.group(2))
        if m.group(3) == "h":
            w = float(re.match(r"M [\d.]+ [\d.]+ h ([\d.]+) v ([\d.]+)", sub.strip()).group(1))
            squares.append((x + w / 2, y + w / 2))
        else:
            keyholes.append(x)  # a keyhole is traced from the top of its slot, on its axis
    return sorted(keyholes), sorted(squares)


def from_foot(xs, foot):
    return sorted(x if foot == "left" else PLATE - x for x in xs)


@pytest.mark.parametrize("cfg", ["front", "rear"])
@pytest.mark.parametrize("view", ["left", "right"])
def test_three_keyholes_and_four_columns_of_squares_where_the_render_draws_them(cfg, view):
    keyholes, squares = holes(plate_path(cfg, view))
    foot = FOOT[(cfg, view)]
    assert len(keyholes) == 3, "the render draws three keyholes, and no fourth"
    assert len(squares) == 8
    columns = sorted({round(x, 3) for x, _ in squares})
    assert len(columns) == 4, "four columns of squares"
    for got, want in zip(from_foot(keyholes, foot), KEYHOLES):
        assert abs(got - want) <= TOL, (cfg, view, "keyhole", got, want)
    for got, want in zip(from_foot(columns, foot), SQUARES):
        assert abs(got - want) <= TOL, (cfg, view, "square column", got, want)
    for y in {round(y, 3) for _, y in squares}:
        assert min(abs(y - r) for r in ROWS) <= TOL, (cfg, view, "square row", y)
    assert len({round(y, 3) for _, y in squares}) == 2, "two rows"
    # the pitch is the render's dimension, 31.5, between neighbours of both kinds
    ks, cs = from_foot(keyholes, foot), from_foot(columns, foot)
    for a, b in zip(ks, ks[1:]):
        assert abs(b - a - PITCH) <= 0.1
    for a, b in zip(cs, cs[1:]):
        assert abs(b - a - PITCH) <= 0.1
    # alternate, half a pitch off: square, keyhole, square, keyhole, square, keyhole, square
    order = sorted([(x, "k") for x in keyholes] + [(x, "s") for x in columns])
    assert "".join(t for _, t in order) in ("sksksks",)


@pytest.mark.parametrize("cfg", ["front", "rear"])
def test_the_keyhole_parts_sit_on_the_keyholes_cut_in_the_plate(cfg):
    """The three placed keyhole parts (the published pdu-button slots) stand on
    the keyholes the plate's path cuts, in the left view."""
    svg = (DIST / f"fs-pdubk.{cfg}.left.svg").read_text()
    placed = sorted(float(x) + 21.3 / 2 for x in re.findall(r'<g id="keyhole-\d"[^>]*transform="translate\(([\d.]+),', svg))
    keyholes, _ = holes(plate_path(cfg, "left"))
    assert len(placed) == 3
    for p, k in zip(placed, keyholes):
        assert abs(p - k) <= 0.01
