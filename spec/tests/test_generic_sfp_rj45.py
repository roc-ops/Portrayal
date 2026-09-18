"""A copper SFP: the SFP envelope with an RJ45 jack for a face."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/sfp-rj45/v1/contract.yaml"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())

# STANDARDS IS EMPTY ON A PLAIN IMPORT: lint.py fills it inside main(), so a
# rule called directly finds no entry for any `conforms` key and L9 reports an
# unknown key - or, worse, passes vacuously. Load it once, the way main does
# (the pattern spec/tests/test_pitch_lint.py established).
lint.STANDARDS.update(
    lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def component_errors(path):
    """The rules a part test cares about, run the way the CLI runs them. L9 is a
    branch of `lint.lint_component`, not a function of its own; L11 and L99 are
    separate functions the CLI's component loop calls after it, so they are
    called here too - `lint_component` alone would never raise them."""
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        lint.lint_component_generic(path, d)
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


def test_it_is_an_sfp_with_a_jack_for_a_face():
    d = yaml.safe_load(P.read_text())
    assert d["mates"] == "sfp" and d["conforms"] == "sfp-module"
    assert d["attrs"]["face"] == "rj45" and d["attrs"]["media"] == "copper"
    assert [p["ref"] for p in d["parts"]] == ["std/rj45-ganged@2"]
    assert "optical-tx" not in d["connection-points"]
    assert d["connection-points"]["net"]["direction"] == "front"


def test_it_lints_clean():
    assert rule_errors(P, "L9", "L11", "L99") == []
