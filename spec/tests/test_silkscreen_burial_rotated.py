"""L21 turns a placement the way render.py draws it.

render.py draws a placement translate(at) rotate(deg w/2 h/2), so a quarter
turn lands the part centred on the same point with its width and height
swapped. L21 handled only the half turn and tested every other part lying flat
where it stands. On the XM-7380 the console USB-A - 12 x 4.5, rotate 90 - was
tested across x 371.8-383.8 where it is drawn across x 375.55-380.05, and the
upright CONSOLE legend beside it was reported 4.50mm inside it.

Pinned to the RENDERER, not to arithmetic written a second time here: the test
reads the transform render.py emits and maps the contract box through it.
"""
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import lint, render

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
ROOTS = [str(LIB)]
USB = "std/usb-a@1"          # 12 x 4.5, a readable skin, no composed parts
AT = (20.0, 10.0)


class _NoSchema:
    def iter_errors(self, _data):
        return iter(())


def _device(rotate, marks=()):
    place = {"id": "usb", "ref": USB, "at": list(AT)}
    if rotate is not None:
        place["rotate"] = rotate
    return {
        "format": 1, "kind": "device", "name": "t", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "T", "model": "T",
        "chassis": {"width": 60, "height": 30, "depth": 50},
        "views": {"front": {
            "size": {"w": 60, "h": 30},
            "silkscreen": [{"at": list(a), "text": t, "font-size": 1.5} for a, t in marks],
            "components": {"placements": [place]},
        }},
    }


def _drawn_box(rotate):
    """Where render.py puts the part: its contract box through the transform
    the compiled <g> carries."""
    d = _device(rotate)
    out = render.render_view(d, "front", d["views"]["front"], render.Library(ROOTS), config={})
    out = out[0] if isinstance(out, tuple) else out
    root = ET.fromstring(out) if isinstance(out, (str, bytes)) else out
    g = next(e for e in root.iter() if e.get("id") == "usb")
    tf = g.get("transform")
    m = re.fullmatch(r"translate\(([-\d.]+),([-\d.]+)\)"
                     r"(?: rotate\(([-\d.]+) ([-\d.]+) ([-\d.]+)\))?", tf)
    assert m, tf
    tx, ty = float(m[1]), float(m[2])
    deg, cx, cy = (float(m[3]), float(m[4]), float(m[5])) if m[3] else (0.0, 0.0, 0.0)
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    sz = lint.contract_size(USB, ROOTS)
    pts = [(tx + cx + c * (x - cx) - s * (y - cy), ty + cy + s * (x - cx) + c * (y - cy))
           for x in (0, sz["w"]) for y in (0, sz["h"])]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def _l21_boxes(rotate):
    p = _device(rotate)["views"]["front"]["components"]["placements"][0]
    return lint.placement_paint_boxes(p, ROOTS)


@pytest.mark.parametrize("rotate", [None, 90, 180, 270, -90])
def test_l21_boxes_sit_where_the_part_is_drawn(rotate):
    x0, y0, x1, y1 = _drawn_box(rotate)
    boxes = _l21_boxes(rotate)
    assert boxes
    # every painted box lies inside the drawn part...
    for bx, by, bw, bh, _, _ in boxes:
        assert bx >= x0 - 1e-6 and by >= y0 - 1e-6, (rotate, boxes, (x0, y0, x1, y1))
        assert bx + bw <= x1 + 1e-6 and by + bh <= y1 + 1e-6, (rotate, boxes, (x0, y0, x1, y1))
    # ...and together they span it: usb-a's skin paints its whole contract box
    assert min(b[0] for b in boxes) == pytest.approx(x0)
    assert min(b[1] for b in boxes) == pytest.approx(y0)
    assert max(b[0] + b[2] for b in boxes) == pytest.approx(x1)
    assert max(b[1] + b[3] for b in boxes) == pytest.approx(y1)


def test_a_quarter_turn_swaps_width_and_height_about_the_centre():
    """The XM-7380 case in miniature: 12 x 4.5 at (20, 10), turned 90, is drawn
    4.5 wide and 12 tall about the same centre (26, 12.25)."""
    assert _drawn_box(90) == pytest.approx((23.75, 6.25, 28.25, 18.25))


def _l21(tmp_path, rotate, marks):
    path = tmp_path / "device.yaml"
    path.write_text(yaml.safe_dump(_device(rotate, marks)))
    with lint.collecting() as got:
        lint.lint_device(path, _NoSchema(), ROOTS)
    return [w for w in got.warnings if "[L21]" in w]


def test_a_legend_beside_the_upright_part_is_not_buried(tmp_path):
    """Inside the flat box the old rule tested, clear of the upright one it is
    drawn as: x 20.5-22 against a part that starts at 23.75."""
    assert not _l21(tmp_path, 90, [((20.5, 14.0), "C")])
    # the same mark IS under the part when it lies flat
    assert _l21(tmp_path, None, [((20.5, 14.0), "C")])


def test_a_legend_under_the_upright_part_is_buried(tmp_path):
    """Below the flat box, inside the upright one."""
    ws = _l21(tmp_path, 90, [((25.5, 17.5), "C")])
    assert any("inside usb" in w for w in ws), ws
    assert not _l21(tmp_path, None, [((25.5, 17.5), "C")])
