"""The latch outline follows its colour, derived from the fill (#482).

The four generic transceivers carry one colour field, `latch-color`, on the
bail or pull tab, and the outline was a literal no field moved - so a red latch
was drawn with the default's edge. `data-stroke-derive="<key>"` draws a node's
stroke as a fixed darker shade of that key's colour.

The shade is ONE rule written twice, render.py `stroke_shade` for the build and
kit/fields.js `strokeShade` for a viewer that changes a colour afterwards. Two
copies of a rule drift, so this holds them to identical output: each channel
times 61/100, rounded half up in integers, `#rgb` and `#rrggbb` accepted, and
anything else answered with no shade at all.
"""
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from portrayal.render import fill_from_attrs, stroke_shade

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/stroke-derive.mjs"
GENERICS = ["sfp-lc/v1", "sfp-lc-simplex/v2", "qsfp-lc/v1", "qsfp-dd-lc/v1"]

INPUTS = ["#000000", "#ffffff", "#6f6f6f", "#c22f2f", "#2255aa", "#3d7bd6",
          "#abc", "#ABC", "#FfEe00", " #6f6f6f ", "#010101", "#808080",
          "red", "rgb(1,2,3)", "#12345", "#1234567", "6f6f6f", "", "#ggg"]


@pytest.fixture(scope="module")
def js():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), json.dumps(INPUTS)], capture_output=True,
                       text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_rule_is_the_documented_one():
    assert stroke_shade("#6f6f6f") == "#444444", "the default's outline moved"
    assert stroke_shade("#000") == "#000000"
    assert stroke_shade("#ffffff") == "#9c9c9c"
    assert stroke_shade("#c22f2f") == "#761d1d"
    assert stroke_shade("#2255aa") == "#153468"
    assert stroke_shade("#abc") == stroke_shade("#aabbcc") == stroke_shade("#AABBCC")
    for bad in ("red", "rgb(1,2,3)", "#12345", "6f6f6f", "", None, "#ggg"):
        assert stroke_shade(bad) is None, bad


def test_python_and_js_give_identical_hex(js):
    py = [stroke_shade(c) for c in INPUTS]
    assert js["shades"] == py
    assert sum(1 for s in py if s) >= 10, "the parity check compared almost nothing"


def test_every_channel_value_agrees(js):
    """All 256 values of a channel, not a sample - the half-up edge is where two
    languages' rounding would part company."""
    colours = [f"#{v:02x}{v:02x}{v:02x}" for v in range(256)]
    p = subprocess.run(["node", str(SCRIPT), json.dumps(colours)], capture_output=True,
                       text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])["shades"]
    assert got == [stroke_shade(c) for c in colours]


def test_runtime_derives_and_restores(js):
    assert js["set"]["stroke"] == "#761d1d" and js["set"]["fill"] == "#c22f2f"
    assert js["changed"]["stroke"] == "#153468", "an upper-case hex must shade the same"
    assert js["noShade"]["fill"] == "red" and js["noShade"]["stroke"] == "#444444"
    assert js["cleared"]["stroke"] == "#444444" and js["cleared"]["fill"] == "#6f6f6f"
    assert not any(k.startswith("data-portrayal-") for k in js["cleared"])


def _node(stroke="#20406f"):
    root = ET.Element("g")
    ET.SubElement(root, "rect", {"id": "bail", "fill": "#6f6f6f", "stroke": stroke,
                                 "data-fill-from": "latch-color",
                                 "data-stroke-derive": "latch-color"})
    return root, root[0]


def test_the_build_derives_from_the_value():
    root, n = _node()
    fill_from_attrs(root, {"latch-color": "#c22f2f"})
    assert (n.get("fill"), n.get("stroke")) == ("#c22f2f", "#761d1d")


def test_the_build_derives_from_the_drawn_default_when_unset():
    for attrs in ({}, {"latch-color": ""}, {"latch-color": None}):
        root, n = _node()
        fill_from_attrs(root, attrs)
        assert (n.get("fill"), n.get("stroke")) == ("#6f6f6f", "#444444"), attrs


def test_a_blank_colour_is_an_empty_one():
    """A whitespace-only value used to paint fill="" - an invisible node - where
    the runtime trims it and leaves the drawing. One rule for both."""
    root = ET.Element("g")
    a = ET.SubElement(root, "rect", {"fill": "#6f6f6f", "stroke": "#8c1f1f",
                                     "data-fill-from": "c", "data-stroke-from": "c"})
    b = ET.SubElement(root, "rect", {"fill": "#6f6f6f", "stroke": "#20406f",
                                     "data-stroke-derive": "c"})
    fill_from_attrs(root, {"c": "   "})
    assert (a.get("fill"), a.get("stroke")) == ("#6f6f6f", "#8c1f1f")
    assert b.get("stroke") == "#444444", "a blank value must derive from the drawn default"


def test_a_colour_with_no_shade_leaves_the_stroke():
    root, n = _node("#123456")
    fill_from_attrs(root, {"latch-color": "red"})
    assert (n.get("fill"), n.get("stroke")) == ("red", "#123456")


@pytest.mark.parametrize("c", GENERICS)
def test_the_generic_latch_follows_its_fill(c):
    """And the standalone skin is already right: its literal outline is the shade
    of its literal fill, so a skin opened on its own draws what the build does."""
    art = (ROOT / "library/components/generic" / c / "skins/default.svg").read_text()
    tags = re.findall(r'<rect\b[^>]*data-fill-from="latch-color"[^>]*>', art)
    assert len(tags) == 1, c
    tag = tags[0]
    assert 'data-stroke-derive="latch-color"' in tag, f"{c}: the outline does not follow the fill"
    fill = re.search(r'\bfill="([^"]+)"', tag).group(1)
    stroke = re.search(r'\bstroke="([^"]+)"', tag).group(1)
    assert stroke == stroke_shade(fill), f"{c}: literal stroke {stroke} is not the shade of {fill}"


def test_every_derived_outline_in_the_library_is_drawn_as_its_shade():
    seen = 0
    for svg in (ROOT / "library/components").glob("*/*/v*/skins/*.svg"):
        text = svg.read_text(errors="replace")
        for tag in re.findall(r'<[a-z]+\b[^>]*data-stroke-derive="[^"]+"[^>]*>', text):
            key = re.search(r'data-stroke-derive="([^"]+)"', tag).group(1)
            if f'data-fill-from="{key}"' not in tag:
                continue                 # its fill is on another node; the build reads that one
            seen += 1
            fill = re.search(r'\bfill="([^"]+)"', tag)
            stroke = re.search(r'\bstroke="([^"]+)"', tag)
            assert fill and stroke, f"{svg}: a derived outline needs a literal fill and stroke"
            assert stroke.group(1) == stroke_shade(fill.group(1)), svg
    assert seen >= len(GENERICS), "the sweep found fewer derived outlines than the generics carry"
