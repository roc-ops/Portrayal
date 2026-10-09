"""An outlet's state shown on its lamp, in 2D and 3D (#934, the kit half).

docs/pdu-model-design.md section 3.2. A switched PDU outlet declares `[on,
off]`, and the lamp that shows it is its own part, placed with `for:` naming
the outlet. One rule in kit/states.js (boundLamps, expandStates) carries a
state set on the outlet's path to that lamp, and every place a state is
applied asks it: a marks document (marks.js apply), the Explorer's chips
(kit/index.html, with states.js offIsSet for what `off` does) and the 3D
scene (relief.js applyNodeStates, viewer3d.js setStates). js/outlet-states.mjs
runs the real modules on a fake DOM; render.py's half (`data-lamped` and the
fallback rule) is held here too.
"""
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from portrayal import render

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/outlet-states.mjs"
KIT = ROOT / "kit"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


# --- the rule ------------------------------------------------------------------

def test_a_lamp_is_bound_to_an_outlet_that_declares_states(out):
    """Not the seated plug or the silkscreen (no states), a lamp whose states
    are prose, a port's lamp (the port declares none of its own), or a lamp
    naming another drawing."""
    assert out["bound"] == {"outlet-a1": ["lamp-a1"], "relay-1": ["lamp-r1"]}


def test_the_map_expansion(out):
    assert out["expanded"] == {"outlet-a1": "state-off", "outlet-a2": "state-on",
                               "eth0": "state-up", "lamp-a1": "state-off"}
    assert out["lampWins"]["lamp-a1"] == "state-on", "a lamp the map states itself wins"
    assert out["byPaths"] == {"outlet-a1": "state-on", "lamp-a1": "state-on"}
    assert out["empty"] == {}


def test_the_off_chip_sets_a_state_on_an_outlet_and_a_declared_off(out):
    """An outlet always takes `state-off` (anything with a lamp bound to it,
    or a power outlet without one, which the stylesheet dims); a lamp that declares a colour for
    off takes it; a lamp or a plain element with none clears."""
    assert out["offIsSet"] == {"outlet-a1": True, "outlet-a2": True, "lamp-a1": True,
                               "led-plain": False, "breaker-a/rocker": False, "eth0": False,
                               "relay-1": True}
    assert out["paintsOff"]["plain"] is True


# --- 2D ------------------------------------------------------------------------

def test_a_mark_on_an_outlet_reaches_its_lamp_and_nothing_else(out):
    m = out["marks"]
    assert "state-off" in m["a1"].split()
    assert m["lamp"] == "state-off", "the lamp takes the state and nothing else of the mark"
    assert m["plug"] == m["silk"] == "", "a seated plug and silkscreen are not lamps"
    assert m["ethLamp"] == "", "a port declares no states, so its beside-lamp is not reached"
    assert m["far"] == ""
    assert m["counts"] == [1, 1, 1], "a lamp reached by expansion is not counted as marked"
    assert out["marksClearExact"], "clear() did not put the drawing back exactly"
    assert "state-on" in out["marksLater"].split() and "state-off" not in out["marksLater"]


def test_a_custom_lamp_colour_is_not_shown_on_a_lamp_that_is_off(out):
    assert out["marksOffColour"] is None
    assert out["marksOnColour"] == "--led-color:#ff00ff"


# --- 3D ------------------------------------------------------------------------

def test_the_scene_applies_the_same_expansion(out):
    t = out["three"]
    assert t == {"a1": "state-off", "lamp": "state-off", "plug": "", "a2": "state-on"}
    assert out["threeBindings"] == {"outlet-a1": ["lamp-a1"], "relay-1": ["lamp-r1"]}
    assert out["threePiece"] == "state-off", \
        "a relief piece holding only the lamp was not lit from the face's bindings"
    assert out["threePieceUnbound"] == ""
    assert out["threeCleared"] == 0


def test_a_custom_lamp_colour_stays_off_in_3d_when_its_outlet_is_off(out):
    assert out["threeOffColour"]["lamp"] is None
    assert "--led-color:#00ff00" in out["threeOffColour"]["plain"]


def test_the_viewer_measures_a_change_on_the_expanded_maps():
    """applyStatesNow repaints the textures whose text holds a CHANGED path; a
    lamp's relief piece does not hold its outlet's path, so the change is
    measured after the expansion. And each build reads the bindings afresh."""
    src = (KIT / "viewer3d.js").read_text()
    body = src[src.index("async function applyStatesNow"):]
    body = body[:body.index("\n  }\n")]
    assert re.search(r"expandStates\(STATES, binds\)", body)
    assert re.search(r"expandStates\(next, binds\)", body)
    assert "lampBindings(SCOPE)" in body
    build = src[src.index("async function build(cfg)"):]
    assert build.index("clearLampBindings(SCOPE)") < build.index("setNodeStates(STATES, SCOPE)")


def test_the_explorer_chips_ask_the_shared_rule():
    page = (KIT / "index.html").read_text()
    chips = page[page.index("function chips(el)"):page.index("// ------------------------------------------------------------- display badge")]
    assert "boundLamps(state.svg)" in chips
    assert "offIsSet(el, lamps)" in chips
    assert "for (const t of [el, ...lamps])" in chips


# --- the compiled drawing --------------------------------------------------------

def test_data_lamped_marks_an_outlet_with_a_lamp_and_nothing_else():
    ns = render.SVG_NS
    svg = ET.fromstring(
        f'<svg xmlns="{ns}">'
        '<g data-path="outlet-a1" data-class="inlet" data-states="on off"/>'
        '<g data-path="lamp-a1" data-class="led" data-states="on off" data-for="outlet-a1"/>'
        '<g data-path="plug-a1" data-for="outlet-a2"/>'
        '<g data-path="outlet-a2" data-class="inlet" data-states="on off"/>'
        '<g data-path="eth0" data-class="port"/>'
        '<g data-path="led-eth0" data-class="led" data-states="off link" data-for="eth0"/>'
        '<g data-path="led-far" data-class="led" data-states="on off" data-for="/rear/outlet-a2"/>'
        '<g data-path="outlet-a3" data-class="inlet" data-states="on off"/>'
        '<g data-path="lamp-a3" data-class="led" data-states="Green = on" data-for="outlet-a3"/>'
        '</svg>')
    render.mark_lamped(svg)
    got = {n.get("data-path"): n.get("data-lamped") for n in svg.iter() if n.get("data-path")}
    assert got["outlet-a1"] == "true"
    assert [p for p, v in got.items() if v] == ["outlet-a1"], \
        "prose states, a port and a cross-view target mark nothing"


def test_the_fallback_dims_an_unlamped_outlet_that_is_off():
    rule = re.search(r"^\s*(\[data-class='inlet'\]\[data-states~='off'\]\.state-off"
                     r":not\(\[data-lamped\]\))\s*\{\s*opacity:\s*([\d.]+);\s*\}",
                     render.STATE_CSS, re.M)
    assert rule, "STATE_CSS has no rule dimming an unlamped outlet that is off"
    absent = re.search(r"\.state-absent\s*\{\s*opacity:\s*([\d.]+)", render.STATE_CSS)
    assert float(rule.group(2)) != float(absent.group(1))


def test_a_rendered_pdu_marks_the_outlet_its_lamp_is_bound_to():
    """Through render_view, as a build draws it: a switched outlets group, and
    one lamp placed with `for:` and the G4's declared colours."""
    outlets = [{"id": f"outlet-a{n}", "ref": "std/c13-outlet@1", "at": [0, 30 * n],
                "group": "outlets"} for n in (1, 2)]
    lamp = {"id": "lamp-a1", "ref": "common/led-dot@1", "at": [40, 30], "for": "outlet-a1",
            "states": [{"name": "on", "color": "#22c55e"}, {"name": "off", "color": "#ef4444"}]}
    doc = {"format": 1, "kind": "device", "name": "p", "version": "1.0.0",
           "manufacturer": "Acme", "model": "P1", "profile": "power", "maturity": "modelled",
           "attrs": {"management": {"metering-scope": "outlet", "outlet-switching": True}},
           "chassis": {"width": 52, "height": 100, "depth": 53, "ru": 3, "mount": "rack-side"},
           "groups": {"outlets": {"term": "Outlet", "states": ["on", "off"]}},
           "views": {"front": {"size": {"w": 52, "h": 100},
                               "components": {"placements": [*outlets, lamp]}}}}
    svg = render.render_view(doc, "front", doc["views"]["front"],
                             render.Library([ROOT / "library"]))
    got = {n.get("data-path"): n for n in svg.iter() if n.get("data-path")}
    assert got["outlet-a1"].get("data-lamped") == "true"
    assert got["outlet-a2"].get("data-lamped") is None
    assert got["lamp-a1"].get("data-for") == "outlet-a1"
    style = svg.find(f"{{{render.SVG_NS}}}style").text
    assert "#lamp-a1.state-off" in style and "#ef4444" in style
