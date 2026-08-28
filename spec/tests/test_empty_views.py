"""L60 and the schema guard behind `empty` (see capability._has_content).

`empty` is the only field in a device that can turn a failing capability check
green without anything being drawn, so it carries two guards: the schema stops
it being a bare flag, and L60 stops the sentence outliving the search.
"""
import json
import pathlib
import sys

import jsonschema
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))

SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
REAL = yaml.safe_load((ROOT / "library/devices/cisco/asr-9910/device.yaml").read_text())


def validate(doc):
    jsonschema.validate(doc, SCHEMA)


# ---- the schema will not take a flag ----------------------------------------

def test_the_real_device_validates():
    validate(REAL)


@pytest.mark.parametrize("bad", [True, "yes", "n/a", "nothing here"])
def test_a_bare_flag_or_a_shrug_is_rejected(bad):
    """The claim is about a SEARCH, not about the drawing, so it has to be long
    enough to say where you looked. `empty: yes` is the failure mode this field
    would otherwise invite."""
    doc = json.loads(json.dumps(REAL))
    doc["views"]["bottom"]["empty"] = bad
    with pytest.raises(jsonschema.ValidationError):
        validate(doc)


def test_the_declaration_says_where_it_looked():
    note = REAL["views"]["bottom"]["empty"]
    assert "78-document" in note and "11.3 percent" in note, \
        "the sentence should carry the search, not just assert emptiness"


# ---- L60: the sentence must not outlive the search --------------------------

def lint_one(doc, tmp_path):
    import lint
    lint.FINDINGS.clear() if hasattr(lint, "FINDINGS") else None
    p = tmp_path / "device.yaml"
    p.write_text(yaml.safe_dump(doc))
    out = []
    real_warn = lint.warn
    lint.warn = lambda path, rule, msg: out.append((rule, msg))
    try:
        lint.lint_device_empty_declaration(str(p), doc)
    finally:
        lint.warn = real_warn
    return out


def test_a_bare_declared_empty_view_is_silent(tmp_path):
    assert lint_one(REAL, tmp_path) == []


def test_drawing_on_a_face_that_says_it_is_empty_warns(tmp_path):
    """THE WAY THIS ROTS. Not fraud - time. A source turns up, the feature gets
    drawn, and the sentence saying nobody could find one stays behind."""
    doc = json.loads(json.dumps(REAL))
    doc["views"]["bottom"]["regions"] = [{"id": "feet", "label": "four rubber feet"}]
    found = lint_one(doc, tmp_path)
    assert found and found[0][0] == "L60"
    assert "1 regions" in found[0][1]


def test_a_view_with_no_declaration_is_not_examined(tmp_path):
    doc = json.loads(json.dumps(REAL))
    doc["views"]["bottom"].pop("empty")
    doc["views"]["bottom"]["regions"] = [{"id": "feet", "label": "four rubber feet"}]
    assert lint_one(doc, tmp_path) == []
