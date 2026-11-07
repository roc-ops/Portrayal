"""The M5 pan head must read against the bracket it sits on (#1003).

`common/pan-screw-m5@1` is black, true to the part (FS's render shows black
heads on a black bracket), and the side plate of the FS DIN rail brackets is a
near-identical dark grey. Colour is not the lever, so the head's outer edge has
to carry it: the stroke that draws the head's rim must stand clear of what lies
behind it in the 2D side views, which is the bracket plate and, through the
slot, the panel's flange.

The margin is a contrast ratio of 3:1, the floor WCAG 2.1 (1.4.11, non-text
contrast) sets for a graphical object a reader has to see, computed on the
relative luminance of the two sRGB colours. On main the rim (#3a3e43) is 1.6:1
against the plate and 1.7:1 against the flange, which is the ring "hardly seen"
in the issue; 3:1 is the least that makes a ring plainly visible, and a rim
chosen for it is not so bright that the black head stops reading as black.

Built, not read off the skins: the colour a viewer sees is the one in the
rendered side view.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import warmrender

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
SVG = "{http://www.w3.org/2000/svg}"
DEVICES = ("dinrail2u", "dinrail4u")
SIDE_VIEWS = ("left", "right")
MARGIN = 3.0


def _luminance(hex_colour):
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", hex_colour), hex_colour
    chans = []
    for i in (1, 3, 5):
        c = int(hex_colour[i:i + 2], 16) / 255
        chans.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2]


def contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.fixture(scope="module", params=DEVICES)
def built(request, tmp_path_factory):
    name = request.param
    out = tmp_path_factory.mktemp(f"legible-{name}")
    dev = LIB / "devices/fs" / name / "device.yaml"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    return name, out


def _rim(head):
    """The colour of the outermost ring of a head: the stroke of its first circle."""
    circle = head.find(f"{SVG}circle")
    assert circle is not None and circle.get("stroke"), "a head with no stroked outer circle"
    return circle.get("stroke")


def test_the_head_rim_stands_clear_of_the_plate_and_the_flange(built):
    name, out = built
    measured = 0
    for view in SIDE_VIEWS:
        root = ET.parse(out / f"{name}.base.{view}.svg").getroot()
        plate = next(p for p in root.iter(f"{SVG}path") if (p.get("id") or "").endswith("--plate"))
        flange = next(r for r in root.iter(f"{SVG}rect") if r.get("id") == "flange")
        behind = {"plate": plate.get("fill"), "flange": flange.get("fill")}
        heads = [g for g in root.iter(f"{SVG}g") if (g.get("id") or "").endswith("--head")]
        assert len(heads) == 2, (name, view)
        for head in heads:
            for what, fill in behind.items():
                ratio = contrast(_rim(head), fill)
                assert ratio >= MARGIN, (
                    f"{name} {view} {head.get('id')}: rim {_rim(head)} on the {what} {fill} "
                    f"is {ratio:.2f}:1, under {MARGIN}:1")
                measured += 1
    assert measured == 8


def _dark_stages():
    """The explorer's stage swatches that are dark, read from kit/shell.js (read only)."""
    src = (ROOT / "kit/shell.js").read_text()
    table = re.search(r"STAGE_SWATCHES\s*=\s*\[(.*?)\];", src, re.S).group(1)
    colours = re.findall(r"\['(#[0-9a-fA-F]{6})'", table)
    dark = [c for c in colours if _luminance(c) < 0.18]
    assert {"#101214", "#3b3f45"} <= set(dark), colours
    return dark


def _heads(out, name):
    for view in SIDE_VIEWS:
        root = ET.parse(out / f"{name}.base.{view}.svg").getroot()
        heads = [g for g in root.iter(f"{SVG}g") if (g.get("id") or "").endswith("--head")]
        assert len(heads) == 2, (name, view)
        for head in heads:
            yield view, head


def test_the_head_rim_stands_clear_of_the_dark_stages(built):
    """Where a head's edge meets the stage (a bracket drawn on the explorer's dark grounds)."""
    name, out = built
    stages = _dark_stages()
    for view, head in _heads(out, name):
        for stage in stages:
            ratio = contrast(_rim(head), stage)
            assert ratio >= MARGIN, (
                f"{name} {view} {head.get('id')}: rim {_rim(head)} on the stage {stage} "
                f"is {ratio:.2f}:1, under {MARGIN}:1")


def test_the_head_marks_stand_clear_of_the_head(built):
    """The recess and the dome ring are seen against the head's own fill."""
    name, out = built
    for view, head in _heads(out, name):
        fill = head.find(f"{SVG}circle").get("fill")
        ring = head.findall(f"{SVG}circle")[1]
        recess = head.find(f"{SVG}path")
        for what, el in (("dome ring", ring), ("recess", recess)):
            stroke = el.get("stroke")
            ratio = contrast(stroke, fill)
            assert ratio >= MARGIN, (
                f"{name} {view} {head.get('id')}: {what} {stroke} on the head {fill} "
                f"is {ratio:.2f}:1, under {MARGIN}:1")


def test_the_rim_is_thick_enough_to_see(built):
    """A rim of 0.3 mm is about a pixel at 2x; 0.5 is plainly a line."""
    name, out = built
    for view, head in _heads(out, name):
        rim = head.find(f"{SVG}circle")
        width = float(rim.get("stroke-width"))
        assert width >= 0.5, (name, view, head.get("id"), width)


def test_the_head_keeps_its_black_fill(built):
    """The fix is in how the head is drawn, not in its colour."""
    name, out = built
    for view in SIDE_VIEWS:
        root = ET.parse(out / f"{name}.base.{view}.svg").getroot()
        for head in (g for g in root.iter(f"{SVG}g") if (g.get("id") or "").endswith("--head")):
            assert head.find(f"{SVG}circle").get("fill") == "#1d1f22", (name, view)
            assert head.get("data-z-color") == "#1d1f22", (name, view)
