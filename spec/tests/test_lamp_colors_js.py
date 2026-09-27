"""A lamp in the host's colour in 3D (#664, part 2).

In 2D a mark's `lamp` is any hex, written on the lamp as an inline
`--led-color`. In 3D a lamp is part of a face texture, and `setStates` only
adds `state-*` classes, so a custom colour never reached the texture and the
lamp showed its stylesheet default. relief.js now keeps a per-viewer lamp
colour registry and paints it into the text every texture is drawn from;
viewer3d's `setLampColors` repaints through it. These hold the registry and
the paint, on the fake DOM through the real modules.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/lamp-colors.mjs"
MARK = "/*portrayal-lamp*/"
END = "/*portrayal-lamp-end*/"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_colour_is_hex_or_nothing(out):
    """It lands in a CSS value slot, so anything but a hex is refused, by path."""
    assert out["rejected"] == ["led-psu"]
    assert out["registry"] == {"led-sys": "#ff00ff", "led-fan": "#2bb3c8"}


def test_a_lamp_takes_the_colour_inline_and_keeps_its_own_style(out):
    sys_, fan, psu = out["set"]["sys"], out["set"]["fan"], out["set"]["psu"]
    assert sys_["style"] == f"{MARK}--led-color:#ff00ff{END}"
    assert fan["style"] == f"opacity:0.9;{MARK}--led-color:#2bb3c8{END}"
    assert "style" not in psu, "a refused colour painted anyway"


def test_a_colour_taken_out_puts_the_drawing_back(out):
    assert out["changed"]["sys"]["style"] == f"{MARK}--led-color:#00ff00{END}"
    assert out["changed"]["fan"]["style"] == "opacity:0.9", "the lamp's own style was lost"
    assert "data-portrayal-lamp" not in out["changed"]["fan"]
    assert "style" not in out["cleared"]["sys"]
    assert out["cleared"]["fan"]["style"] == "opacity:0.9"


def test_a_lamp_that_is_off_stays_unlit(out):
    """As in 2D (`mark.state !== 'off'`): the colour never lights a lamp that is out."""
    assert "style" not in out["off"]["sys"]
    assert "--led-color:#2bb3c8" in out["off"]["fan"]["style"]


def test_each_viewer_has_its_own_colours(out):
    assert out["otherScope"] == {}


def test_the_unlit_copy_of_a_blinking_lamp_loses_the_colour(out):
    """lamps.js draws a blink's off half from an unlit copy of the art; with
    the host's colour left in it the lamp would never go dark."""
    assert out["stripped"] == '<svg><!--art--><g class="state-on" style="opacity:0.9;"><circle/></g></svg>'
    quiet = out["base"].split("<!--art-->")[1]
    assert quiet.startswith('<g class="" style="opacity:0.9;">'), quiet
    assert "--led-color:#ff00ff" in out["base"], "the lit copy above it must keep the colour"


def test_the_hex_rule_is_the_2d_marks_rule():
    """relief.js repeats marks.js's HEX_RE rather than importing the 2D module;
    the two must accept exactly the same colours."""
    rx = lambda f, name: re.search(rf"{name}\s*=\s*(/[^\n;]+/i)", (ROOT / f).read_text()).group(1)
    assert rx("kit/relief.js", "LAMP_HEX") == rx("kit/marks.js", "HEX_RE")


def test_a_dome_cut_below_the_lamp_carries_the_colour(out):
    """relief.js scopeWrap rebuilds a lamp's group around the art of a dome or
    lens cut out beneath it. It carried the group's class (so the state rule
    applied) and not the host's colour, so after a rebuild the face showed the
    custom colour around a dome in the stylesheet's own - found on the S9700-23D
    in the browser harness. The wrapper carries the marked colour, and only
    while one is registered."""
    w = out["wrapped"]
    assert 'class="state-ok"' in w and 'data-path="led-sys"' in w, w
    assert f"{MARK}--led-color:#ff00ff{END}" in w, w
    assert "--led-color" not in out["wrappedCleared"], out["wrappedCleared"]


def test_a_mark_colour_is_one_a_material_reads(out):
    """three's Color.setStyle reads #rgb and #rrggbb and leaves a material
    white for anything else, so a mark given #rrggbbaa drew white and was not
    reported. markHex keeps the colour and drops the alpha (#667)."""
    assert out["markHex"] == {
        "#F0a": "#f0a", "#f0a8": "#f0a", "#FF00AA": "#ff00aa", "#ff00aa80": "#ff00aa",
        "red": None, "#ff00a": None, "": None, "null": None}
