"""The Explorer lets a reader try a colour on a programmable-colour lamp (#1271).

A lamp marked `programmable` is one whose colour the user chooses. A reader
looking at such a model in the Explorer cannot tell what that means from a grey
ring, so the tree row of each marked lamp carries a colour box: the choice
paints that lamp in the drawing and in the 3D scene, and is a viewing choice
only - it is not written into the model, the location or any export.

js/programmable-demo.mjs runs the three small functions in kit/states.js on a
fake DOM. The page's wiring is held here by reading kit/index.html, the way
test_viewer_page.py holds the rest of the page; a real face built from a
synthetic marked device shows the page's selector finds the lamps the build
marks. What a browser alone shows (the box under a pointer, the scene
repainted) is looked at by hand.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from test_programmable_light import TEMPLATE, build, marked_text

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
SCRIPT = ROOT / "spec/tests/js/programmable-demo.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


# --- the three functions ---------------------------------------------------------

def test_only_a_lamp_marked_true_is_programmable(out):
    """The note when there is one, an empty string when the mark has none, and
    nothing at all for a lamp that is not marked (or says `false`)."""
    assert out["of"] == {"led-a": "Etherlighting", "led-b": "", "led-c": None,
                         "led-d": None, "led-e": ""}
    assert out["none"] == [None, None, None]


def test_a_demo_colour_is_an_opaque_hex_colour(out):
    assert out["hex"] == {"#ff00ff": "#ff00ff", "#F0F": "#ff00ff", "#FF00FF80": None,
                          "red": None, "rgb(1,2,3)": None, "": None, "null": None,
                          "#12345": None, "#gggggg": None}


def test_the_scene_is_given_only_the_colours_of_marked_lamps_on_the_drawing(out):
    """A colour for an unmarked lamp, for a lamp not on the drawing or that is
    not a colour is not passed on."""
    assert out["colours"] == {"led-a": "#00ff00", "led-e": "#0000ff"}
    assert out["fromMap"] == {"led-a": "#123456"}
    assert out["empty"] == [{}, {}, {}]


# --- the page ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def page():
    return (KIT / "index.html").read_text()


def test_the_row_of_a_marked_lamp_gets_a_colour_box_and_no_other_row_does(page):
    assert "programmableOf" in page and "demoHex" in page and "demoColours" in page
    assert 'type = \'color\'' in page or 'type="color"' in page or "type='color'" in page
    # the box is made only for an element the states module calls programmable
    assert re.search(r"programmableOf\(node\.el\)", page)


def test_the_choice_paints_the_lamp_the_way_a_declared_state_colour_does(page):
    """Through the lamp-colour variable every lamp that declares states is
    painted from (lint rule L74), never by a fill of its own."""
    assert "setProperty('--led-color'" in page
    assert "removeProperty('--led-color')" in page


def test_the_scene_hears_the_colours_and_a_new_device_forgets_them(page):
    assert "setLampColors(" in page
    assert re.search(r"shell\.on\('device',[^;]*DEMO\.clear\(\)", page, re.S)


def test_the_choice_is_a_viewing_choice_and_reaches_no_link(page):
    """It does not travel in the location, the fields or the swaps."""
    body = page[page.index("A DEMO COLOUR"):page.index("// end of the demo colour")]
    for word in ("cfgFields", "writeLocation", "replaceState", "swapDelta", "localStorage"):
        assert word not in body, word


# --- a real face --------------------------------------------------------------------

def _marked(out_dir):
    root = ET.fromstring((out_dir / "ex-1u.base.front.svg").read_text())
    return [e for e in root.iter() if e.get("data-programmable") == "true"
            and e.get("data-class") != "programmable-ring"]


@pytest.fixture(scope="module")
def lit(tmp_path_factory):
    return _marked(build(tmp_path_factory.mktemp("lit"), marked_text())[2])


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    return _marked(build(tmp_path_factory.mktemp("plain"), TEMPLATE.read_text())[2])


@pytest.mark.heavy
def test_the_lamps_the_build_marks_are_the_lamps_the_page_would_find(lit):
    """Every element the build marks carries the path the page keys its colour
    by; the lamp that takes the mark back is not among them."""
    assert lit, "the synthetic device marks lamps"
    assert all(e.get("data-path") for e in lit)
    assert "led-port-4" not in {e.get("data-path") for e in lit}


@pytest.mark.heavy
def test_an_unmarked_face_offers_no_colour_box(plain):
    assert plain == []
