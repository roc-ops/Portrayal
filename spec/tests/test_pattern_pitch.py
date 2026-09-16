"""`pattern-pitch` - a decor rect states its own louvre pitch.

A pattern is a tile, and every face used to get one vendor's tile. `slots-h` is
14 x 8 because that is the louvre pitch of the first hardware it was drawn for,
so a MaiaEdge PBC bezel - eight rows of louvres in the 24mm its window leaves -
could only be drawn with three, and the most recognisable texture on the face
came out as somebody else's grille.

The scale must be DERIVED from the tile's own width and height, never from a
second copy of them written down beside it. That is this library's most repeated
defect: two names for one number, held apart and never compared.
"""
import re
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

from portrayal import render


def _svg(decor):
    view = {"size": {"w": 200.0, "h": 50.0}, "panel": {"decor": decor}}
    d = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
         "chassis": {"width": 200.0, "height": 50.0, "depth": 100.0},
         "views": {"front": view}}
    out = render.render_view(d, "front", view, render.Library([str(LIB)]), config={})
    return out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")


def _transform(svg, fill_of):
    """The patternTransform of whatever pattern the named rect is filled with."""
    m = re.search(rf'<(?:rect|path) id="{fill_of}"[^>]*fill="url\(#([^)]+)\)"', svg)
    assert m, f"{fill_of} is not filled from a pattern:\n{svg[:1200]}"
    p = re.search(rf'<pattern[^>]*id="{re.escape(m.group(1))}"[^>]*>', svg)
    assert p, f"pattern {m.group(1)} was referenced but never defined"
    t = re.search(r'patternTransform="([^"]*)"', p.group(0))
    return m.group(1), (t.group(1) if t else None)


def _tile(svg, pid):
    p = re.search(rf'<pattern[^>]*id="{re.escape(pid)}"[^>]*>', p_str := svg)
    assert p, p_str[:400]
    w = re.search(r'width="([\d.]+)"', p.group(0)).group(1)
    h = re.search(r'height="([\d.]+)"', p.group(0)).group(1)
    return float(w), float(h)


def test_a_rect_with_no_pitch_still_gets_the_plain_pattern():
    """Every vent field already in the library is untouched by this."""
    svg = _svg([{"id": "v", "at": [10.0, 10.0], "size": [100.0, 20.0],
                 "pattern": "slots-h", "vent": 20}])
    pid, transform = _transform(svg, "v")
    assert pid == "portrayal-slots-h", "an unmodified rect must use the base tile"
    assert transform is None


def test_the_pitch_scales_the_tile_it_was_measured_against():
    """23 x 3 against a 14 x 8 tile is 5 columns and 8 rows in 115 x 24."""
    svg = _svg([{"id": "v", "at": [16.5, 8.5], "size": [115.0, 24.0],
                 "pattern": "slots-h", "pattern-pitch": [23.0, 3.0], "vent": 20}])
    pid, transform = _transform(svg, "v")
    assert pid != "portrayal-slots-h"
    m = re.search(r"scale\(([\d.eE+-]+) ([\d.eE+-]+)\)", transform)
    assert m, transform
    # the factor is written to six significant figures, so it can be out by
    # ~3e-6 - a thousandth of a millimetre across the whole 115mm field
    assert abs(float(m.group(1)) - 23.0 / 14.0) < 1e-5, transform
    assert abs(float(m.group(2)) - 3.0 / 8.0) < 1e-5, transform


def test_the_scale_comes_off_the_tile_and_not_off_a_copy_of_its_size():
    """THE POINT OF THE FEATURE, stated as a test.

    Asking for a pitch equal to the tile's own declared width and height must
    come out as scale(1 1). If the factor were divided by a constant written
    beside the pattern rather than read from it, editing the pattern would leave
    that constant behind and every pitch on every face would be quietly wrong.
    """
    svg = _svg([{"id": "v", "at": [0.0, 0.0], "size": [100.0, 20.0],
                 "pattern": "slots-h", "pattern-pitch": [14.0, 8.0], "vent": 20}])
    pid, transform = _transform(svg, "v")
    tw, th = _tile(svg, "portrayal-slots-h")
    m = re.search(r"scale\(([\d.eE+-]+) ([\d.eE+-]+)\)", transform)
    assert (tw, th) == (14.0, 8.0), "the base slots-h tile moved; update this test"
    assert abs(float(m.group(1)) - 1.0) < 1e-9, transform
    assert abs(float(m.group(2)) - 1.0) < 1e-9, transform


def test_pitch_and_offset_travel_together_translate_first():
    """Offset then scale: the SCALED tile's origin lands on the rect's corner.

    The other order scales the offset too, so a lattice asked to start at the
    rect's own corner starts somewhere else entirely - and the further the pitch
    is from the tile's own, the further off it lands.
    """
    svg = _svg([{"id": "v", "at": [16.5, 8.5], "size": [115.0, 24.0],
                 "pattern": "slots-h", "pattern-offset": [16.5, 8.5],
                 "pattern-pitch": [23.0, 3.0], "vent": 20}])
    _pid, transform = _transform(svg, "v")
    assert re.match(r"^translate\(16\.5 8\.5\) scale\(", transform), transform


def test_two_rects_at_the_same_pitch_share_one_pattern():
    """Both windows of a bezel carry the same louvres; the file says so once."""
    svg = _svg([{"id": "a", "at": [10.0, 8.5], "size": [60.0, 24.0],
                 "pattern": "slots-h", "pattern-pitch": [23.0, 3.0], "vent": 20},
                {"id": "b", "at": [120.0, 8.5], "size": [60.0, 24.0],
                 "pattern": "slots-h", "pattern-pitch": [23.0, 3.0], "vent": 20}])
    a, _ = _transform(svg, "a")
    b, _ = _transform(svg, "b")
    assert a == b
    assert len(re.findall(rf'<pattern[^>]*id="{re.escape(a)}"', svg)) == 1


def test_offset_alone_still_only_translates():
    """The two devices already using `pattern-offset` must render as they did."""
    svg = _svg([{"id": "v", "at": [10.0, 10.0], "size": [100.0, 20.0],
                 "pattern": "holes", "pattern-offset": [2.5, 1.25], "vent": 20}])
    _pid, transform = _transform(svg, "v")
    m = re.search(r"scale\(([\d.eE+-]+) ([\d.eE+-]+)\)", transform)
    assert transform.startswith("translate(2.5 1.25)"), transform
    assert abs(float(m.group(1)) - 1.0) < 1e-9 and abs(float(m.group(2)) - 1.0) < 1e-9
