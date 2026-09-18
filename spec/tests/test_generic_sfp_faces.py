"""The SFP faces that are not LC duplex: one LC (bidi). Same
envelope, same latch, a different face - and the face is in the name
(docs/pluggables-design.md decision 4).

generic/sfp-sc is GATED (no free document dimensions the SC opening - see the
ruling in spec A section 4). Only generic/sfp-lc-simplex is built here."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

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


def contract(name):
    return yaml.safe_load((LIB / f"components/generic/{name}/v1/contract.yaml").read_text())


def test_bidi_has_one_lc_bore_and_one_optical_point():
    d = contract("sfp-lc-simplex")
    assert d["mates"] == "sfp" and d["conforms"] == "sfp-module"
    assert [p["ref"] for p in d["parts"]] == ["std/lc-bore@3"]
    assert "optical" in d["connection-points"]
    assert "optical-tx" not in d["connection-points"]


def test_both_share_the_sfp_envelope_and_protrude():
    lc = contract("sfp-lc")
    for name in ("sfp-lc-simplex",):
        d = contract(name)
        assert d["size"] == lc["size"], name
        body = next(f for f in d["relief"]["features"] if f["node"] == "body")
        assert body["out"] == next(f for f in lc["relief"]["features"] if f["node"] == "body")["out"]


def test_both_lint_clean():
    for name in ("sfp-lc-simplex",):
        p = LIB / f"components/generic/{name}/v1/contract.yaml"
        assert rule_errors(p, "L9", "L11", "L99") == [], name
