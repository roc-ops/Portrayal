"""generic/rj45-plug: the unshielded RJ45 (8P8C) copper plug body, standing
for every unshielded RJ45 plug of this shape
(docs/pluggables-connectors-design.md).

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


def test_latch_2_77_is_not_a_relief_figure():
    """Fix round 1: the latch's 2.77 is an in-plane Y displacement (the latch
    hangs BELOW the body datum in the drawing's side view, the same plane as
    size.w/size.h) - not a Z protrusion out of the panel face. An earlier
    draft of this contract carried it as `relief.features[].out`, which
    render.js's `data-z-out` treats as an ABSOLUTE distance perpendicular to
    the face - std/sma@1's barrel is genuinely a Z protrusion (coaxial with
    the mate axis) and that precedent does not carry to a latch on a
    different axis. The 2.77/5.89 figures are recorded in provenance and
    drawn (inset, schematically) in the skin instead.

    Pluggables D gives the part a `relief:` block after all - the body's
    standoff out of the jack and the latch's reach ALONG the plug axis, both
    genuinely Z - so what this pins now is that neither in-plane figure is
    written as a Z magnitude."""
    d = contract()
    for f in d["relief"]["features"]:
        for k in ("out", "lift"):
            assert f.get(k) not in (2.77, 5.89), (f["node"], k, f.get(k))
    prov = d["provenance"]["latch"]
    assert "2.77" in prov
    assert "5.89" in prov


def test_latch_has_no_angle_in_provenance():
    """Fix round 1: '88 degrees REF' does not describe the latch - it labels
    the cable-entry core-out taper on two SKU-specific plan views elsewhere on
    the sheet (bubbles 8/9, 'APPROXIMATE ... ONLY APPLIES TO PARTS
    X-557972-X / X-554720-X'), not the dimensioned side view the 2.77/5.89
    latch figures come from. The drawing gives no angle for the latch and
    this contract must not invent or substitute one."""
    prov = contract()["provenance"]["latch"]
    assert "88" not in prov or "core-out" in prov.lower()
    assert "no angle" in prov.lower() or "no angle is given" in prov.lower()


def test_size_says_h_excludes_the_latch_unlike_lc_plug():
    """Fix round 1, finding 3: generic/lc-plug@1's h (10.43) is a silhouette
    INCLUDING its latch; this part's h (7.93) is the body EXCLUDING its latch.
    Neither number is wrong, but they measure different quantities and a
    reader comparing them needs to be told so - in both contracts and in both
    spec/schemas/standards.yaml entries."""
    prov = contract()["provenance"]
    text = " ".join(str(v) for v in prov.values()).lower()
    assert "lc-plug" in text
    assert "exclud" in text  # "excluding"/"excludes"
    reg = yaml.safe_load(
        (ROOT / "spec/schemas/standards.yaml").read_text())["standards"]
    assert "exclud" in reg["rj45-plug"]["notes"].lower()
    assert "includ" in reg["lc-plug"]["notes"].lower()


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
