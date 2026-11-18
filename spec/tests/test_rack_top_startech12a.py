"""The StarTech 12U open frame states its top opening and no longer says the base key is missing.

The product states the `top` entry with no `box`, and its source quotes the product's own form
note. No held document states the caster count, so `base` is not written and a gap asks for it.
"""
import json
import pathlib

from jsonschema import Draft202012Validator

from portrayal import lint
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/rack-product.schema.json").read_text())
KEY = "startech/4postrack12a"
PATH = LIB / "racks" / KEY / "rack.yaml"


def rack():
    return load_yaml(PATH)


def test_the_product_states_the_top_entry_with_no_box():
    doc = rack()
    assert list(Draft202012Validator(SCHEMA).iter_errors(doc)) == []
    assert list(doc["enclosure"]) == ["entries"]
    [top] = doc["enclosure"]["entries"]
    assert (top["id"], top["where"], top["kind"]) == ("top", "roof", "open")
    assert "box" not in top
    assert doc["version"] == "1.1.0"


def test_the_top_entry_lints_clean():
    got = []
    real = lint.err
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    try:
        lint.lint_rack(PATH, rack(), [str(LIB)])
    finally:
        lint.err = real
    assert [m for r, m in got if r == "L193"] == []


def test_the_source_quotes_the_form_note_of_the_product():
    doc = rack()
    quote = "the Frame Type row (Open Frame) on page 3"
    assert quote in doc["provenance"]["form"]["note"].replace("\n", " ")
    assert quote in doc["enclosure"]["entries"][0]["source"]


def test_the_description_no_longer_says_the_key_does_not_exist():
    text = rack()["description"].replace("\n", " ").lower()
    assert "no key for a base" not in text
    assert "not data yet" not in text
    assert "caster" in text


def test_the_caster_count_is_a_gap_because_no_held_document_states_it():
    doc = rack()
    assert "base" not in doc
    gap = {g["what"]: g for g in doc["gaps"]}["casters"]
    assert "base" in gap["note"].lower() and "base" in gap["wanted"].lower()
    assert "no key" not in gap["note"].lower()
