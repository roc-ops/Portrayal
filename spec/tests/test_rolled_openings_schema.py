"""The rolled bracket's `strip` and `ear-slots` keys validate what a sheet can state and no more."""
import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

SCHEMA = json.loads((pathlib.Path(__file__).resolve().parents[2] / "spec/schemas/device.schema.json").read_text())
EARS = SCHEMA["properties"]["chassis"]["properties"]["ears"]["oneOf"]
ITEM = next(o for o in EARS if o.get("type") == "object")["properties"]["rolled"]["items"]
BASE = {"id": "below", "side": "below", "bar-h": 25.4, "length": 486.41, "ear-h": 92.44, "ear-w": 28.0}


def errors(extra):
    return list(Draft202012Validator({**ITEM, "$defs": SCHEMA["$defs"]}).iter_errors({**BASE, **extra}))


def test_a_bracket_without_them_still_validates():
    assert errors({}) == []


def test_the_shelf_bracket_figures_validate():
    assert errors({"strip": {"count": 17, "pitch": 25.4, "size": [5, 5]},
                   "ear-slots": {"count": 2, "pitch": 60, "size": [6, 14]}}) == []


def test_the_cross_bracket_slots_validate():
    assert errors({"strip": {"shape": "slot", "count": 11, "pitch": 35, "size": [30, 4]}}) == []


@pytest.mark.parametrize("bad", [
    {"strip": {"count": 0, "pitch": 25.4, "size": [5, 5]}},
    {"strip": {"count": 2.5, "pitch": 25.4, "size": [5, 5]}},
    {"strip": {"count": 17, "pitch": 0, "size": [5, 5]}},
    {"strip": {"count": 17, "pitch": 25.4}},
    {"strip": {"count": 17, "pitch": 25.4, "size": [5]}},
    {"strip": {"shape": "square", "count": 17, "pitch": 25.4, "size": [5, 5]}},
    {"strip": {"count": 17, "pitch": 25.4, "size": [5, 5], "first": 40}},
    {"ear-slots": {"count": 2, "size": [6, 14]}},
    {"ear-slots": {"count": 2, "pitch": 60, "size": [6, 14], "first": 5}},
    {"strip": {"count": 17, "pitch": 25.4, "size": [0, 5]}},
    {"strip": {"count": 17, "pitch": 25.4, "size": [5, -5]}},
    {"ear-slots": {"count": 2, "pitch": 60, "size": [6, 0]}},
    {"ear-slots": {"count": 0, "pitch": 60, "size": [6, 14]}},
    {"ear-slots": {"count": 2.5, "pitch": 60, "size": [6, 14]}},
    {"ear-slots": {"count": 2, "pitch": 60, "size": [6]}},
    {"strip": {"pitch": 25.4, "size": [5, 5]}},
    {"strip": {"count": 17, "pitch": -1, "size": [5, 5]}},
])
def test_a_wrong_figure_is_refused(bad):
    assert errors(bad), bad


def test_the_published_form_keeps_each_key_and_floats_each_length():
    from portrayal.render import published_ears
    out = published_ears({"rolled": [{**BASE, "strip": {"count": 17, "pitch": 25, "size": [5, 5]},
                                      "ear-slots": {"count": 2, "pitch": 60, "size": [6, 14]}}]})
    b = out["rolled"][0]
    assert b["strip"] == {"count": 17, "pitch": 25.0, "size": [5.0, 5.0]}
    assert isinstance(b["strip"]["count"], int) and isinstance(b["strip"]["pitch"], float)
    assert b["ear-slots"] == {"count": 2, "pitch": 60.0, "size": [6.0, 14.0]}
    assert "strip" not in published_ears({"rolled": [BASE]})["rolled"][0]


def test_the_published_form_keeps_the_shape():
    from portrayal.render import published_ears
    out = published_ears({"rolled": [{**BASE, "strip": {"shape": "slot", "count": 11, "pitch": 35, "size": [30, 4]}}]})
    assert out["rolled"][0]["strip"] == {"shape": "slot", "count": 11, "pitch": 35.0, "size": [30.0, 4.0]}
