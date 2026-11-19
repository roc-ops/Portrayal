"""The open frames whose own notes say they are open frames state the `top` entry.

A product states one `top` entry (roof, open, no box) only on two conditions.
Its own notes say it is an open frame, and none says it has a roof.
It also states an `outer`. A product that fails that test states no entry.
"""
import pathlib

import pytest
from jsonschema import Draft202012Validator

import json

from portrayal import lint
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/rack-product.schema.json").read_text())

# product -> the words of its own form note that its entry quotes
STATED = {
    "fs/fs-or4p-45u": "an open frame with two left and two right vertical rails, "
                      "top and base brackets and side sections",
    "startech/4postrack42": "joined by corner and center beams, with top and base brackets",
}
# products whose notes give no such sentence, or that fail the form or the outer test
LEFT_OUT = [
    "chatsworth/13853-x03",
    "chatsworth/55053-x03",
    "fs/fs-or4p-xxu",
    "fs/fs-dr-8u",
    "generic/2-post-frame",
    "generic/4-post-frame",
    "generic/4-post-cabinet",
    "startech/rk1219walloh",
]


def rack(key):
    return load_yaml(LIB / "racks" / key / "rack.yaml")


def flat(text):
    return " ".join(text.split())


def l193(key, doc):
    got = []
    real = lint.err
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    try:
        lint.lint_rack(LIB / "racks" / key / "rack.yaml", doc, [str(LIB)])
    finally:
        lint.err = real
    return [m for r, m in got if r == "L193"]


@pytest.mark.parametrize("key", STATED)
def test_the_frame_states_exactly_the_top_entry(key):
    doc = rack(key)
    assert [e.message for e in Draft202012Validator(SCHEMA).iter_errors(doc)] == []
    assert l193(key, doc) == []
    assert list(doc["enclosure"]) == ["entries"]
    [top] = doc["enclosure"]["entries"]
    assert {k: top[k] for k in ("id", "where", "kind")} == {"id": "top", "where": "roof", "kind": "open"}
    assert "box" not in top
    assert "outer" in doc


@pytest.mark.parametrize("key", STATED)
def test_the_source_quotes_the_products_own_form_note(key):
    doc = rack(key)
    quote = STATED[key]
    assert quote in flat(doc["provenance"]["form"]["note"])
    [top] = doc["enclosure"]["entries"]
    assert quote in flat(top["source"])
    assert "roof" not in flat(doc["description"]).lower()


@pytest.mark.parametrize("key", LEFT_OUT)
def test_a_product_the_screen_left_out_states_no_entry(key):
    assert "entries" not in (rack(key).get("enclosure") or {})
