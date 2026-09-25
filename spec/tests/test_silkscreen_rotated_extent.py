"""A rotated legend's box is the renderer's rotation of its upright box.

render.py draws a rotated silkscreen mark as `rotate(deg x y)` about its `at`.
SVG turns clockwise on screen, so an upright mark's caps (-y) end up RIGHT of
the baseline at 90 and LEFT of it at 270 / -90. The lint had the two swapped,
and XM-7380's upright CONSOLE legend - painted 1.2mm clear of the USB port on
its right - was reported as 4.5mm inside it.

These read the transform off the renderer rather than restating the
convention, so the two cannot drift apart again without a failure here.
"""
import math
import re
from pathlib import Path

import pytest

from portrayal import lint, render

LIB = Path(__file__).resolve().parents[2] / "library"
NS = "{http://www.w3.org/2000/svg}"


def _drawn_transform(mark):
    dev = {"format": 1, "kind": "device", "name": "t", "version": "0.1.0",
           "maturity": "draft", "manufacturer": "T", "model": "T",
           "chassis": {"width": 60.0, "height": 40.0, "depth": 100.0},
           "views": {"front": {"size": {"w": 60.0, "h": 40.0}, "silkscreen": [mark]}}}
    out = render.render_view(dev, "front", dev["views"]["front"],
                             render.Library([str(LIB)]))
    root = out[0] if isinstance(out, tuple) else out
    texts = [e for e in root.iter(f"{NS}text") if e.get("data-class") == "silkscreen"]
    assert len(texts) == 1, "the fixture draws exactly one legend"
    return texts[0].get("transform")


def _rotate_box(box, deg, cx, cy):
    """The axis-aligned box of `box` turned by SVG's rotate(deg cx cy)."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    x0, y0, x1, y1 = box
    pts = [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c)
           for x in (x0, x1) for y in (y0, y1)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


@pytest.mark.parametrize("rotate", [90, -90, 270, 180])
@pytest.mark.parametrize("anchor", ["start", "middle", "end"])
def test_rotated_extent_is_the_renderers_rotation_of_the_upright_one(rotate, anchor):
    mark = {"text": "CONSOLE", "at": [30.0, 20.0], "anchor": anchor,
            "rotate": rotate, "font-size": 1.6}
    tr = _drawn_transform(mark)
    got = re.fullmatch(r"rotate\((\S+) (\S+) (\S+)\)", tr or "")
    assert got, f"the renderer rotates the legend about its `at`: {tr!r}"
    deg, cx, cy = map(float, got.groups())
    upright = lint._text_extent({**mark, "rotate": 0})
    want = _rotate_box(upright, deg, cx, cy)
    assert lint._text_extent(mark) == pytest.approx(want, abs=1e-9)


def test_caps_fall_left_at_minus_90_and_right_at_90():
    """The two sides stated outright, so a reader need not trust the algebra:
    CONSOLE on XM-7380 (`rotate: -90`, anchored at the baseline x) inks x
    LESS than its `at`, and the mirror mark at 90 inks x greater."""
    base = {"text": "CONSOLE", "at": [373.3, 9.0], "anchor": "end", "font-size": 1.6}
    x0, _, x1, _ = lint._text_extent({**base, "rotate": -90})
    assert x1 - 373.3 < 0.2 < 373.3 - x0, "caps LEFT of the baseline"
    x0, _, x1, _ = lint._text_extent({**base, "rotate": 90})
    assert 373.3 - x0 < 0.2 < x1 - 373.3, "caps RIGHT of the baseline"
