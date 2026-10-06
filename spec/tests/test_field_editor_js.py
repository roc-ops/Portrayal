"""The explorer's field editor, the half that needs no page (#811).

A component declares `fields:` - a breaker's rating, a supply's wattage, a
latch's colour - and the kit has had `setFields` to write them. The explorer
never called it, so a part seated there always showed its defaults. The form
now lives in the inspector (kit/shell.js); what it draws, what it refuses and
what it writes into the location are pure functions in kit/fields.js, held
here through the real module.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/field-editor.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_row_per_declared_field_in_declared_order(out):
    rows = out["rows"]
    assert [r["key"] for r in rows] == ["rating", "colour", "count"]
    assert out["none"] == []


def test_a_row_shows_what_the_drawing_holds_else_the_default(out):
    rating, colour, count = out["rows"]
    assert (rating["value"], rating["default"]) == ("5", "60")
    # an empty held value is "nothing set", so the default shows
    assert colour["value"] == "#c22f2f"
    assert count["value"] == "4"


def test_a_row_carries_what_the_control_needs(out):
    rating, colour, count = out["rows"]
    assert rating["type"] == "choice" and rating["options"] == ["2", "3", "5", "60"]
    assert (rating["label"], rating["unit"]) == ("Rating", "A")
    assert colour["type"] == "text" and colour["pattern"] == "#[0-9a-f]{6}"
    # no label declared: the key stands in for it
    assert count["type"] == "number" and count["label"] == "count"


def test_a_value_the_field_does_not_take_is_refused(out):
    a = out["accepts"]
    assert a["option"] and not a["notOption"]
    assert a["number"] and not a["notNumber"] and not a["emptyNumber"]
    # the pattern is the whole value, not a prefix of it
    assert a["pattern"] and not a["notPattern"]
    # an unreadable pattern refuses nothing; an undeclared field takes nothing
    assert a["badPattern"] and not a["undeclared"]
    # `decl["constructor"]` is a function on any object; it is not a declaration
    assert not a["inherited"]


def test_the_location_string_round_trips_every_separator(out):
    assert out["dec"] == {"breaker-a1/module": {"rating": "30"},
                          "a,b~c/x": {"k": "v ~,1"}}
    # sorted, and a null value is not written
    assert out["enc"].split(",")[1] == "breaker-a1%2Fmodule~rating~30"
    assert "gone" not in out["enc"]
    assert out["empty"] == ["", "", "{}", "{}"]


def test_a_bad_entry_is_dropped_and_the_rest_kept(out):
    assert out["junk"] == {"ok": {"k": "v"}}



def test_a_name_every_object_inherits_is_an_ordinary_key(out):
    """`fields=` is whatever a link carries. Gathered in a plain object,
    `constructor~keys~x` replaced Object.keys with a string and
    `constructor~prototype~x` threw, before any device had loaded."""
    got = out["inherited"]
    assert got["got"] == {"constructor": {"keys": "x", "prototype": "y"},
                          "hasOwnProperty": {"call": "z"}, "toString": {"zz": "w"},
                          "ok": {"k": "v"}}
    assert got["own"] and got["untouched"]


def test_a_location_is_not_a_place_to_hold_a_document(out):
    """A contract's pattern is run over every value kept, so a value has a
    length and a string has a number of entries."""
    assert list(out["long"]) == ["b"] and len(out["long"]["b"]["k"]) == 256
    assert out["many"] == 256
