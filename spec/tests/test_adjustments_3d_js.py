"""Adjustable positions, step 4: the kit, in 3D.

docs/adjustable-positions-design.md section 6. The relief of a node is built
from its box and its depth keys, and a position changes both: `dx` and `dy`
move the node, and `dz` changes the depth it is built at - `data-depth` for a
well, `data-z-lift` (the sign reversed) and the heights that go with it for
anything else. The scene is rebuilt, as it is for a switch position.

TWO PATHS, AND BOTH ARE HELD. The REBUILD path measures a fresh document with
the position applied first (relief.js extractRelief). The REPAINT path redraws
a face from its own last output when something else on it changes
(restyleText), and must leave a moved part where it stands: not back at its
default, and not moved a second time.

WHAT RUNS HERE, AND WHAT DOES NOT. WebGL does not run under node, and
neither does the layout extractRelief measures with. So this suite holds:
the documents a scene is built from, moved through the real registry; the
repaint, through relief.js's own restyleText; and the decision between the
two paths, as the function viewer3d.js asks (fields.js positionsChanged), by
what it answers. It reads from source only that viewer3d.js and extractRelief
call those in the right place. The built scene itself - vertex positions at
the default and at both ends, by both paths - is measured in a browser by
spec/tests/browser/viewer3d-adjustments.html, which is run by hand: its
header says when.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/adjustments-3d.mjs"
VIEWER = (ROOT / "kit/viewer3d.js").read_text()
RELIEF = (ROOT / "kit/relief.js").read_text()

# position -> what the front and side documents hold at it
POSITIONS = {"min": 20, "max": 180}


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def at(s, tint="#6f6f6f", finish="#d0d3d6"):
    """What the two documents hold with the panel at `s` mm."""
    shift = s - 60
    return {
        "front": {
            "panel": {"transform": "translate(10.0,0.0)", "data-depth": f"{s:g}"},
            "rail": {"transform": "translate(20.0,15.0)", "data-z-lift": f"{-s:g}"},
            "rail--rail": {"data-z-out": f"{7.5 - s:g}"},
            "badge": {}, "badge--face": {"fill": tint}},
        "side": {
            "stud": {"transform": (f"translate({shift:g} 0) " if shift else "")
                     + "translate(63.0,17.0)", "data-z-lift": "1.5"},
            "stud--head": {"fill": finish}}}


# --- the rebuild path ---------------------------------------------------------------------

def test_a_fresh_document_is_measured_where_the_registry_puts_it(out):
    assert out["rebuild"]["default"] == at(60) == out["built"]
    for name, s in POSITIONS.items():
        assert out["rebuild"][name] == at(s), name


def test_dz_is_the_depth_of_a_well_and_the_lift_of_what_stands_in_it(out):
    """The floor goes to the position; the rail is on that floor, and its 7.5
    rises from there. A stud moves in the plane and keeps its own lift."""
    for name, s in POSITIONS.items():
        front = out["rebuild"][name]["front"]
        assert float(front["panel"]["data-depth"]) == s
        assert float(front["rail"]["data-z-lift"]) == -s
        assert float(front["rail--rail"]["data-z-out"]) - float(front["rail"]["data-z-lift"]) == 7.5
        assert out["rebuild"][name]["side"]["stud"]["data-z-lift"] == "1.5"


def test_a_stop_name_and_a_refused_value_in_the_registry(out):
    assert out["rebuild"]["stop"] == at(180)
    assert out["rebuild"]["refused"] == at(60)


def test_a_face_built_moved_is_moved_from_where_it_was_built(out):
    assert out["rebuildFromBuilt20"]["panel"]["data-depth"] == "60"
    assert out["rebuildFromBuilt20"]["rail"]["data-z-lift"] == "-60"
    assert out["rebuildFromBuilt20"]["rail--rail"]["data-z-out"] == "-52.5"


# --- the repaint path -----------------------------------------------------------------------

def test_a_repaint_leaves_a_moved_part_where_it_stands(out):
    """Another part's field changed. The face is redrawn from its own last
    output: the new colours are there, and the position is neither lost nor
    applied a second time."""
    assert out["repaint"]["at180"] == at(180)
    assert out["repaint"]["front"] == at(180, tint="#c22f2f")["front"]
    assert out["repaint"]["side"] == at(180, finish="#101010")["side"]


def test_three_repaints_move_nothing_further(out):
    assert out["repaintThrice"]["front"] == out["repaint"]["front"]
    assert out["repaintThrice"]["side"] == out["repaint"]["side"]


def test_a_repaint_takes_a_new_position_from_where_the_part_was_built(out):
    assert out["repaintTo20"]["front"] == at(20, tint="#c22f2f")["front"]
    assert out["repaintTo20"]["side"]["stud"] == at(20)["side"]["stud"]


def test_a_position_that_leaves_the_registry_is_put_back_as_built(out):
    assert out["repaintCleared"]["front"] == out["built"]["front"]
    assert out["repaintCleared"]["side"] == out["built"]["side"]
    assert out["repaintCleared"]["stash"] is False


def test_a_fragment_cut_from_a_face_is_left_where_it_was_built(out):
    """A relief piece is rasterised from its own node, already moved, with no
    root to say what moves: nothing moves it again."""
    assert out["fragmentUntouched"] is True


def test_two_viewers_hold_two_positions(out):
    assert out["scopes"] == ["180", "20"]


# --- the order viewer3d.js and relief.js do it in ----------------------------------------------

def _body(src, start, end="\n}\n"):
    i = src.index(start)
    return src[i:src.index(end, i)]


def test_a_face_is_moved_before_it_is_measured():
    """extractRelief reads the depth of a well and the lift of what stands in
    it off the document, so the position is applied first: after the fields
    (it is one) and before the tools that measure."""
    body = _body(RELIEF, "export async function extractRelief(")
    move = body.index("applyNodeAdjustments(svg, scope);")
    assert body.index("applyNodeFields(svg, scope);") < move
    assert move < body.index("nodeTools(svg, {back})")
    assert move < body.index("svg.outerHTML")


def test_a_repaint_applies_the_position_too():
    body = _body(RELIEF, "export function restyleText(")
    assert body.index("applyNodeFields(div, scope);") < body.index("applyNodeAdjustments(div, scope);")


def test_a_change_of_position_is_told_from_any_other_change(out):
    """THE DECISION, BY WHAT IT ANSWERS. A position set, moved or cleared at
    the path of its carrier moves a part; the same position, another part's
    field, the id at another path and another key of the carrier do not."""
    c = out["changed"]
    assert (c["set"], c["moved"], c["cleared"], c["second"]) == (True, True, True, True)
    assert (c["same"], c["sameWithOthers"], c["otherPart"], c["notTheCarrier"],
            c["carrierOtherKey"], c["emptyMaps"]) == (False,) * 6
    assert c["noAdjustments"] == [False, False, False]


def test_a_changed_position_rebuilds_the_scene():
    """A position is a field of no component: the viewer learns which path and
    key it is from configs.json, asks fields.js whether the change moves a
    part (the test above), and rebuilds as it does for a switch."""
    body = _body(VIEWER, "async function applyFieldsNow(map) {", "\n  }\n")
    assert "const slides = positionsChanged(devIndex && devIndex.adjustments, was, FIELDS);" in body
    assert body.index("const was = FIELDS;") < body.index("FIELDS = next;")
    rebuild = re.search(r"if \(slides \|\| .*positional\(e\.svgText\)\)\) \{\s+await build\(CFG\);",
                        body)
    assert rebuild, "a changed position no longer reaches build()"
    # the registry is loaded before the first face of a build is fetched
    # (test_viewer3d_build_registries.py), so the rebuild reads the position
    assert body.index("setNodeFields(FIELDS, SCOPE);") < rebuild.start()


def test_a_moved_part_is_picked_where_it_stands():
    body = _body(VIEWER, "async function buildHitIndex(", "\n  }\n")
    assert body.index("applyNodeAdjustments(svg, SCOPE);") < body.index("svg.getScreenCTM()")
