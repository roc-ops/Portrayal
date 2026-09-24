"""Facets in the schema and L117 (docs/superpowers/specs/2026-09-24-tilted-facets-design.md).

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


from portrayal import lint


def plant(root, data):
    p = root / "components/acme/card/v1/contract.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data))
    return p


LIB = SPEC.parent / "library"


def run(tmp_path, data):
    p = plant(tmp_path, data)
    with lint.collecting() as found:
        lint.lint_component_facets(p, data, [str(tmp_path), str(LIB)])
        lint.lint_component_collisions(p, data, [str(tmp_path), str(LIB)])
    return found


def test_a_good_facet_is_clean(tmp_path):
    f = run(tmp_path, card())
    assert not [e for e in f.errors if "[L117]" in e]


def test_on_must_name_a_facet(tmp_path):
    c = card()
    c["parts"][0]["on"] = "nowhere"
    assert any("[L117]" in e for e in run(tmp_path, c).errors)


def test_the_projected_part_must_lie_within_its_facet(tmp_path):
    c = card()
    c["parts"][0]["at"] = [2.5, 65.0]        # 10.15 x cos30 = 8.79 tall, ends at 73.8 > 70.5
    assert any("[L117]" in e for e in run(tmp_path, c).errors)


def test_a_facet_does_not_also_declare_its_slope(tmp_path):
    c = card()
    c["relief"]["features"][0]["profile-y"] = [[0, 0], [30, 5]]
    assert any("[L117]" in e for e in run(tmp_path, c).errors)


def test_the_facet_node_must_be_an_element(tmp_path):
    c = card(elements={})
    assert any("[L117]" in e for e in run(tmp_path, c).errors)


def test_l46_measures_the_projected_box(tmp_path):
    # two QSFP28s 7 mm apart. At true height (10.15) they overlap 3.15 mm = 31% of the
    # smaller, over L46's 25% threshold; on a 30-degree facet each is 8.79 tall and the
    # overlap is 1.79 mm = 20%, under it. Unprojected boxes would warn; projected must not.
    c = card()
    c["parts"].append({"ref": "std/qsfp28@1", "id": "p2", "at": [2.5, 52.0], "on": "housing"})
    assert not [w for w in run(tmp_path, c).warnings if "[L46]" in w]
