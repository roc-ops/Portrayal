"""generic/rj45-plug: the unshielded RJ45 (8P8C) copper plug body, standing
for every unshielded RJ45 plug of this shape (docs/superpowers/plans/
2026-09-19-pluggables-b2-connector-parts.md, Task 6).

It occupies an `rj45` receptacle at its own `mate` point (mates: rj45) and
presents `rj45-plug` so common/rj45-boot@1 can seat on its `boot` point - or a
bare cable can land on its `cable` point when there is no boot. Both rear
points share the front `mate` point's (x, y), the same connection-point
convention generic/lc-plug@1 and common/lc-boot@1 introduced.

UNLIKE generic/lc-plug@1, this plug HAS a depth. CommScope customer drawing
2843005 rev K, sheet 1 (UNSHIELDED MOD PLUG 8 POSITION) gives the overall
length .885 [22.48] as a PLAIN dimension, not parenthesised, so it is a real,
class-wide figure and belongs in `size.d` - unlike the LC plug's reference-only
overall length, which disagreed across three SENKO drawings and so was left
out. Sheet 2 of the same drawing dimensions the SHIELDED variant, a genuinely
different shape (8.26 high x 22.73 long); this part is sheet 1 only.
"""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/rj45-plug/v1/contract.yaml"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())

lint.STANDARDS.update(
    lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def component_errors(path):
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
    assert d["class"] == "port"
    assert d["mates"] == "rj45"
    assert d["interface"] == "rj45-plug"
    assert d["conforms"] == "rj45-plug"
    assert d["kind"] == "component"


def test_no_behaviour():
    """Ruling carried from generic/lc-plug@1 (Task 4) and restated for Task 6:
    test_behaviour.py::test_a_receptacle_does_not_move forbids a `behaviour`
    on `class: port`. Seating does not need it - render.py's mate-to
    resolution never reads it - and `class: port` is how this library defines
    a connector. See provenance.behaviour for the full account."""
    d = contract()
    assert "behaviour" not in d
    assert "behaviour" in d["provenance"]


def test_size_has_a_real_depth():
    d = contract()
    assert d["size"] == {"w": 11.68, "h": 7.93, "d": 22.48}, (
        "this plug DOES have a class-wide depth - the LC plug's no-depth "
        "reasoning does not carry over, see provenance.size")


def test_size_names_the_unshielded_sheet():
    """provenance must say why this is sheet 1 and not sheet 2, so a later
    reader does not quietly average the two real shapes together."""
    prov = contract()["provenance"]
    text = " ".join(str(v) for v in prov.values())
    assert "8.26" in text or "sheet 2" in text.lower() or "shielded" in text.lower()


def test_size_is_registered_and_lints_clean():
    """L9 holds a `conforms:`-declared size to spec/schemas/standards.yaml's
    `rj45-plug` entry, which spec/tests/test_plug_envelopes.py also pins."""
    assert rule_errors(P, "L9") == []
    reg = yaml.safe_load(
        (ROOT / "spec/schemas/standards.yaml").read_text())["standards"]["rj45-plug"]
    d = contract()
    assert d["size"]["w"] == reg["w"]
    assert d["size"]["h"] == reg["h"]
    assert d["size"]["d"] == reg["depth"]


def test_latch_is_a_relief_feature_not_folded_into_size():
    d = contract()
    feats = (d.get("relief") or {}).get("features") or []
    latch = [f for f in feats if f["node"] == "latch"]
    assert len(latch) == 1, "the latch belongs in relief.features, see provenance.latch"
    assert latch[0]["out"] == 2.77
    assert latch[0].get("confidence")
    assert latch[0].get("source")


def test_connection_points_share_the_axis():
    cps = contract()["connection-points"]
    assert set(cps) == {"mate", "boot", "cable"}
    assert cps["mate"]["direction"] == "front"
    assert cps["boot"]["direction"] == "rear"
    assert cps["cable"]["direction"] == "rear"
    # front and rear are the same physical axis, seen from two directions -
    # the convention generic/lc-plug@1 introduced, followed here rather than
    # re-invented
    assert cps["mate"]["at"] == cps["boot"]["at"] == cps["cable"]["at"]


def test_not_a_fibre_connector():
    """spec/tests/test_connector_sweep.py's sweep keys on
    `attrs.media == "fiber"`; this part's media is `rj45`, so it must not
    enter that sweep's FIBRE_CONNECTORS census - checked, not assumed."""
    d = contract()
    assert d["attrs"]["media"] != "fiber"


def test_it_lints_clean_alone():
    assert rule_errors(P, "L9", "L11", "L99") == []


def test_skin_has_the_body_and_latch_nodes():
    svg = (P.parent / "skins/default.svg").read_text()
    assert 'id="body"' in svg
    assert 'id="latch"' in svg
