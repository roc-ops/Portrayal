"""Facets in the schema and L114 (docs/superpowers/specs/2026-09-24-tilted-facets-design.md).

Fixtures are planted in a tmp library; no live part is borrowed."""
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((SPEC / "schemas/component.schema.json").read_text())


def card(**over):
    c = {"format": 1, "kind": "component", "name": "card", "version": "1.0.0",
         "class": "line-card", "size": {"w": 25.0, "h": 100.0},
         "elements": {"housing": {"at": [0.0, 40.0], "size": [25.0, 30.0], "class": "display"}},
         "relief": {"features": [{"node": "housing", "facet": {"deg": 30, "facing": "up"},
                                  "confidence": "drawing", "source": "fixture"}]},
         "parts": [{"ref": "std/qsfp28@1", "id": "p1", "at": [2.5, 45.0], "on": "housing"}]}
    c.update(over)
    return c


def test_schema_accepts_facet_and_on():
    jsonschema.Draft202012Validator(SCHEMA).validate(card())


@pytest.mark.parametrize("bad", [{"deg": 0, "facing": "up"}, {"deg": 90, "facing": "up"},
                                 {"deg": 30, "facing": "sideways"}, {"deg": 30}])
def test_schema_refuses_bad_facets(bad):
    c = card()
    c["relief"]["features"][0]["facet"] = bad
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(c)
