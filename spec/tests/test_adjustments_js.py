"""Adjustable positions, step 3: the kit, in 2D, the half that needs no page.

docs/adjustable-positions-design.md sections 4 and 5. `adjustmentAccepts` says
whether a typed value is a position and answers with the one spelling to keep
or with a sentence; `adjustmentRows` gives the rows of a control;
`paintAdjustments` moves every member a drawing marks. They are pure functions
of kit/fields.js and are held here through the real module, on the fake DOM.

ONE RULE, WRITTEN TWICE. The build refuses a value a configuration sets
(adjustments.py `accepts`) and the kit refuses one a reader sets. The parity
test feeds one list of values to both and asks for one answer.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from portrayal import adjustments as adj

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/adjustments.mjs"

STOPS = {"front": 20, "middle": 100, "rear": 180}
ADJUSTMENTS = {
    "ranged": {"range": [20, 180], "default": 60, "stops": STOPS},
    "bare": {"range": [51.2, 271.2], "default": 161.2},
    "holes": {"default": 20, "stops": STOPS},
}
VALUES = ["60", "20", "180", "19.9", "180.1", "300", "0", "120", "120.0", "120.04", "120.05",
          "120.06", " 271.20 ", "271.2", "271.24", "271.26", "51.2", "51.15", "51.14", ".5", "100.",
          "front", "middle", "rear", "Rear", " rear ", "back", "", " ", "-20", "+20", "1e2",
          "1_0", "0x10", "inf", "NaN", "12mm", "1,5", "100", "99.96", "99.94", "20.04", None]


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    arg = json.dumps({"adjustments": ADJUSTMENTS, "values": VALUES})
    p = subprocess.run(["node", str(SCRIPT), arg], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


# --- accept and refuse ------------------------------------------------------------------

def test_the_kit_and_the_build_give_one_answer_to_every_value(out):
    for name, decl in ADJUSTMENTS.items():
        got = out["accepts"][name]
        assert len(got) == len(VALUES)
        for value, kit in zip(VALUES, got):
            ok, answer = adj.accepts(decl, value, "panel-setback", "SLIDER")
            assert kit == ({"ok": True, "value": answer} if ok else
                           {"ok": False, "reason": answer}), (name, value)


def _answer(out, name, value):
    return out["accepts"][name][VALUES.index(value)]


def test_the_list_is_not_vacuous(out):
    """Each of the three adjustments accepts some of the list and refuses some."""
    for name in ADJUSTMENTS:
        oks = [a["ok"] for a in out["accepts"][name]]
        assert any(oks) and not all(oks), name


def test_what_is_kept_has_one_spelling(out):
    """A string: rounded to 0.1, in decimal, no exponent, no sign, no `.0`."""
    assert _answer(out, "ranged", "120.0") == {"ok": True, "value": "120"}
    assert _answer(out, "ranged", "120.04") == {"ok": True, "value": "120"}
    assert _answer(out, "ranged", "120.05") == {"ok": True, "value": "120.1"}
    assert _answer(out, "bare", " 271.20 ") == {"ok": True, "value": "271.2"}
    assert _answer(out, "bare", "271.24") == {"ok": True, "value": "271.2"}
    assert out["oneString"] == ["p~k~271.2"] * 3
    for name in ADJUSTMENTS:
        for a in out["accepts"][name]:
            if a["ok"]:
                assert isinstance(a["value"], str)
                assert not a["value"].endswith(".0") and "e" not in a["value"].lower()
                assert float(a["value"]) >= 0


def test_a_stop_name_is_input_and_the_number_is_kept(out):
    assert _answer(out, "ranged", "rear") == {"ok": True, "value": "180"}
    assert _answer(out, "ranged", " rear ") == {"ok": True, "value": "180"}
    assert _answer(out, "holes", "middle") == {"ok": True, "value": "100"}
    assert _answer(out, "holes", "100") == {"ok": True, "value": "100"}


def test_both_ends_of_a_range_are_positions(out):
    assert _answer(out, "bare", "51.2")["ok"] and _answer(out, "bare", "271.2")["ok"]
    assert _answer(out, "bare", "51.15")["ok"]          # rounds to the end
    assert not _answer(out, "bare", "51.14")["ok"]
    assert not _answer(out, "bare", "271.26")["ok"]


def test_the_sentence_for_a_number_outside_the_range(out):
    assert _answer(out, "ranged", "300") == {
        "ok": False, "reason": "panel-setback on SLIDER takes 20 to 180 mm. 300 is outside it."}
    assert _answer(out, "bare", "271.26")["reason"] == \
        "panel-setback on SLIDER takes 51.2 to 271.2 mm. 271.3 is outside it."


def test_the_sentence_for_stops_alone(out):
    want = "panel-setback on SLIDER takes one of: front (20), middle (100), rear (180)."
    for value in ("120", "back", "", "19.9"):
        assert _answer(out, "holes", value) == {"ok": False, "reason": want}, value


def test_the_sentence_for_what_is_neither_a_number_nor_a_stop(out):
    want = "panel-setback on SLIDER takes a number in mm, or one of: front, middle, rear."
    for value in ("back", "Rear", "", "12mm", "NaN", "1_0", "0x10", "inf", "1,5", None):
        assert _answer(out, "ranged", value) == {"ok": False, "reason": want}, value
    # with no stop to offer, the sentence offers none
    assert _answer(out, "bare", "back")["reason"] == "panel-setback on SLIDER takes a number in mm."


def test_the_sentence_for_a_number_with_a_sign_or_an_exponent(out):
    """`-20` is a number, and no position is written so. Told that the
    adjustment takes a number, a reader who typed one learns nothing: the
    sentence says what is wrong with the value."""
    for value in ("-20", "+20", "1e2"):
        assert _answer(out, "ranged", value) == {"ok": False, "reason": (
            "panel-setback on SLIDER takes a number in mm written with digits and a point "
            f"only. {value} is not.")}, value
        assert _answer(out, "bare", value)["reason"].endswith(f"only. {value} is not.")
        # with stops alone there is no number to type at all: the stops are named
        assert _answer(out, "holes", value)["reason"].startswith(
            "panel-setback on SLIDER takes one of: front (20)")


def test_the_sentence_names_the_device_when_the_adjustment_knows_it(out):
    assert out["sentenceFromFace"]["reason"] == \
        "panel-setback on SLIDER takes 20 to 180 mm. 300 is outside it."
    assert out["sentenceBare"]["reason"] == "the position takes 20 to 180 mm. 300 is outside it."


# --- the rows of a control -----------------------------------------------------------------

def test_a_face_says_what_it_declares(out):
    a = out["of"]["panel-setback"]
    assert (a["id"], a["on"], a["carrier"], a["at"]) == ("panel-setback", "SLIDER", "panel", 60)
    assert out["ofNone"] == {} and out["ofBad"] == {}


def test_a_row_carries_what_the_control_needs(out):
    (row,) = out["rows"]
    assert row == {
        "id": "panel-setback", "value": "60", "built": "60", "default": "60",
        "label": "Panel setback", "carrier": "panel", "axis": "z",
        "datum": "the front face of the panel", "unit": "mm", "type": "range",
        "min": "20", "max": "180", "stop": "",
        "stops": [{"name": "front", "value": "20"}, {"name": "middle", "value": "100"},
                  {"name": "rear", "value": "180"}]}


def test_a_row_shows_the_position_held_else_where_the_drawing_was_built(out):
    assert (out["rowsSet"][0]["value"], out["rowsSet"][0]["stop"]) == ("180", "rear")
    assert (out["rowsBetween"][0]["value"], out["rowsBetween"][0]["stop"]) == ("120", "")
    # a value that is not a position is not shown as one
    assert out["rowsRefused"][0]["value"] == "60"
    # a face a configuration built at the front stop
    moved = out["rowsBuiltMoved"][0]
    assert (moved["value"], moved["built"], moved["default"], moved["stop"]) == \
        ("20", "20", "60", "front")


def test_rows_from_configs_json_need_no_face(out):
    first, second = out["rowsFromConfigs"]
    assert [first["id"], second["id"]] == ["a-first", "panel-setback"]      # in id order
    assert first["type"] == "stops" and (first["min"], first["max"]) == ("", "")
    assert first["label"] == "a-first"
    assert [s["name"] for s in first["stops"]] == ["near", "far"]           # in order of position
    assert (first["value"], first["stop"]) == ("100", "far")
    assert second["value"] == second["built"] == "60"                       # no `at`: the default


# --- move and reset -------------------------------------------------------------------------

def test_a_member_moves_in_the_plane_of_its_face(out):
    """On the plan `data-moves-by` is `0 -1 0`: 40 mm forward of the default
    is 40 down the page, 120 back is 120 up it."""
    s = out["plan"]
    assert s["built"]["panel"] == {} and s["built"]["tab"]["transform"] == "translate(5,130) rotate(90 1 1)"
    assert s["drew20"] == {"panel-setback": 20}
    assert s["at20"]["panel"] == s["at20"]["rail"] == {"transform": "translate(0 40)"}
    assert s["at180"]["panel"] == {"transform": "translate(0 -120)"}
    # in front of the transform the member was built with
    assert s["at20"]["tab"] == {"transform": "translate(0 40) translate(5,130) rotate(90 1 1)"}
    assert s["at180"]["tab"] == {"transform": "translate(0 -120) translate(5,130) rotate(90 1 1)"}
    # and what is not a member stays
    assert s["at20"]["side-left"] == s["at180"]["side-left"] == {}
    assert s["atRear"] == s["at180"]
    assert s["fromMap"] == {"transform": "translate(0 -40)"}


def test_a_refused_value_and_a_reset_leave_the_drawing_as_built(out):
    s = out["plan"]
    assert s["refused"] == s["built"] and s["refusedStash"] is False
    assert s["reset"] == s["built"] and s["resetStash"] is False


def test_a_face_built_moved_is_moved_from_where_it_was_built(out):
    """The kit moves a node by (value - at): a face built at 20 and set to 60
    goes 40 back, and a face built at 60 and set to 60 does not move."""
    assert out["fromBuilt20"] == {"transform": "translate(0 -40)"}


def test_a_well_changes_its_depth_and_what_stands_in_it_goes_with_the_floor(out):
    f = out["front"]
    assert f["built"]["panel"]["data-depth"] == "60"
    for name, s in (("at20", 20), ("at180", 180)):
        got = f[name]
        assert got["panel"] == {"transform": "translate(10.0,0.0)", "data-depth": str(s)}, name
        assert got["rail"] == {"transform": "translate(20.0,15.0)", "data-z-lift": str(-s)}, name
        assert got["rail--rail"] == {"data-z-out": str(7.5 - s)}, name
        assert got["rail--web"] == {"data-z-profile": f"0:{-s},10:{7.5 - s}",
                                    "data-z-profile-y": f"0:{5 - s}"}, name
        # not a member, and a projection, which is flat
        assert got["plain"] == f["built"]["plain"] and got["seen"] == f["built"]["seen"], name


def test_the_default_set_and_a_reset_are_the_drawing_as_built(out):
    f = out["front"]
    assert f["at60"] == f["built"] and f["at60Stash"] is False
    assert f["reset"] == f["built"] and f["resetStash"] is False


def test_unpainting_fields_does_not_undo_a_position(out):
    assert out["afterUnpaint"] == {"depth": "180", "value": "180"}


# --- the location ------------------------------------------------------------------------------

def test_a_position_goes_into_a_link_and_back(out):
    assert out["encoded"] == "panel~panel-setback~180"
    assert out["decoded"] == {"panel": {"panel-setback": "180"}}
