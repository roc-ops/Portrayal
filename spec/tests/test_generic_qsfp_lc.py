"""generic/qsfp-lc: one QSFP with an LC duplex face, standing for every QSFP+,
QSFP28 and QSFP56 with one (docs/pluggables-generics-design.md section 3)."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/qsfp-lc/v2/contract.yaml"

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


def contract():
    return yaml.safe_load(P.read_text())


def test_shape():
    d = contract()
    assert d["class"] == "transceiver" and d["behaviour"] == "occupies"
    assert d["mates"] == "qsfp" and d["conforms"] == "qsfp-module"
    assert d["attrs"]["power-absent"] == "not-applicable"
    assert set(d["fields"]) == {"latch-color", "label"}
    assert {p["ref"] for p in d["parts"]} == {"std/lc-bore@3", "common/qsfp-pull-tab@2"}
    assert {p["id"] for p in d["parts"]} == {"tx", "rx", "tab"}
    for k in ("mate", "optical-tx", "optical-rx"):
        assert d["connection-points"][k]["direction"] == "front"


def test_no_rate_anywhere():
    d = contract()
    for k in ("speed", "reach", "wavelength", "mode", "power-draw-max-w"):
        assert k not in d["attrs"], k


def test_it_protrudes_from_day_one():
    feats = {f["node"]: f for f in contract()["relief"]["features"]}
    assert feats["body"]["out"] > 0
    assert feats["body"]["confidence"] in ("drawing", "verified", "measured")
    assert "SFF-8661" in feats["body"]["source"]


def test_the_skin_takes_the_label_as_a_field():
    """The colour is no longer painted in this skin: the composed tab takes it
    (see test_the_seated_tab_wears_the_placements_colour)."""
    svg = (P.parent / "skins/default.svg").read_text()
    assert 'data-from="label"' in svg


def test_it_lints_clean_alone():
    """L9 (size against the registry), L11 (mating) and L99 (stays generic)."""
    assert rule_errors(P, "L9", "L11", "L99") == []


def test_the_bores_are_lifted_to_the_module_face():
    """The bores recess from the transceiver face, which stands proud of the
    panel by the body's `out`; a bore at lift 0 would be a hole in the panel."""
    d = contract()
    out = next(f for f in d["relief"]["features"] if f["node"] == "body")["out"]
    for p in d["parts"]:
        assert abs(p["lift"] - out) < 0.01, p


def test_the_pull_tab_is_the_composed_loop_and_takes_the_colour():
    d = yaml.safe_load(P.read_text())
    tab = next(p for p in d["parts"] if p["id"] == "tab")
    assert tab["ref"] == "common/qsfp-pull-tab@2"
    assert tab["lift"] == 20.0 and tab["at"][1] < 0, "the grip rises above the face's top edge"
    assert tab["at"][1] >= -3.4, "inside the MSA's 3.4 MAX above the module"
    feats = {f["node"] for f in d["relief"]["features"]}
    assert "tab" not in feats, "the brick is gone"
    svg = (P.parent / "skins/default.svg").read_text()
    assert 'id="tab"' not in svg
    assert "latch-color" in d["fields"]


def test_it_declares_its_head_inside_the_msa_envelope():
    d = yaml.safe_load(P.read_text())
    assert d["head"]["size"] == {"w": 18.35, "h": 8.5, "d": 20.0}
    assert not d["head"].get("exceeds")
    with lint.collecting() as got:
        lint.lint_component_head(P, d)
    assert not [e for e in got.errors if "[L121]" in e]


def test_v1_is_superseded_by_v2():
    v1 = yaml.safe_load((P.parents[1] / "v1/contract.yaml").read_text())
    assert v1["superseded-by"] == f"generic/{P.parents[1].name}@2"


def test_the_seated_tab_wears_the_placements_colour():
    from portrayal import render as render_mod
    lib = render_mod.Library([str(LIB)])
    ref = f"generic/{P.parents[1].name}@2"
    g, _ = render_mod.instance_group(lib, ref, "m", [0, 0], None,
                                     {"latch-color": "#1f5fbf"}, None, None)
    fills = {e.get("fill") for e in g.iter() if e.get("data-fill-from") == "latch-color"}
    assert fills == {"#1f5fbf"}
