"""A drawing's viewBox must cover the panel it draws.

The bug this locks: the region-extent code unpacked its box as `x, y, w, h`,
shadowing the VIEW's own w and h for the remainder of render_view. Everything
downstream that asked "how big is this panel" got the last region's box instead.
The C100G rear came out 420.8 x 471.5 against a 432.95 x 571.0 panel - one line
card clipped off the right edge and BOTH PEMs outside the drawing entirely,
present in the tree and invisible in the image.

Why nothing caught it: every element was still emitted at the correct
coordinate, so no rule about positions or sizes could see anything wrong. The
data was right and the window onto it was too small. A test that reads the
manifest and the output and compares the two is the only thing that can tell.

It also silently corrupts 3D, because the face texture is rasterised from this
SVG - which is how it was found: the owner reported cards apparently 30% too
wide and PEMs missing from a view whose YAML places them correctly.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
DEVICES = ROOT / "library" / "devices"
VB = re.compile(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"')


def cases():
    out = []
    for dev in sorted(DEVICES.glob("*/*/device.yaml")):
        d = yaml.safe_load(dev.read_text()) or {}
        for vname, view in (d.get("views") or {}).items():
            size = (view or {}).get("size")
            if size:
                out.append((d["name"], vname, size["w"], size["h"]))
    return out


@pytest.mark.parametrize("name,view,w,h", cases())
def test_viewbox_covers_the_declared_panel(name, view, w, h):
    files = sorted(DIST.glob(f"{name}.*{view}.svg")) + [DIST / f"{name}.{view}.svg"]
    files = [f for f in files if f.exists()]
    if not files:
        pytest.skip(f"{name}.{view} not built")
    for f in files:
        m = VB.search(f.read_text()[:4096])
        assert m, f"{f.name}: no viewBox"
        x, y, vw, vh = (float(g) for g in m.groups())
        # the window may be LARGER than the panel - a placement can legitimately
        # hang off the edge, and that is what the extents pass is for - but it
        # may never be smaller, and it must include the panel's own origin.
        assert x <= 0 and y <= 0, f"{f.name}: viewBox origin {x},{y} excludes the panel"
        assert vw + x >= w - 0.01, (
            f"{f.name}: viewBox is {vw:g} wide from {x:g} but the panel is {w:g} - "
            f"{w - (vw + x):.2f} mm of it is outside the drawing")
        assert vh + y >= h - 0.01, (
            f"{f.name}: viewBox is {vh:g} tall from {y:g} but the panel is {h:g} - "
            f"{h - (vh + y):.2f} mm of it is outside the drawing")
