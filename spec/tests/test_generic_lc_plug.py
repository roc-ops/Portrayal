"""generic/lc-plug: the four-tier LC plug silhouette, front view, standing for
every LC plug - a body holding the ferrule, then a shoulder, a neck and a
latch tip stepping narrower toward the tab (docs/superpowers/plans/
2026-09-19-pluggables-b2-connector-parts.md, Task 4).

It occupies an `lc` receptacle at its own `mate` point (behaviour: occupies,
mates: lc) and presents `lc-plug` so common/lc-boot@1 can seat on its `boot`
point - or a bare cable can land on its `cable` point when there is no boot.
Both rear points share the front `mate` point's (x, y): the fibre runs
straight through the plug on one axis, front to back.

NO DEPTH. The SENKO drawing gives an LC plug's overall length only as a
REFERENCE figure in parentheses, and three SENKO products disagree - (42),
(38.6), (43) - while the front profile and the latch length repeat with
tolerances. spec/tests/test_plug_envelopes.py already pins this on the
registry entry; the tests below pin it on the contract that reads the
registry.
"""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/lc-plug/v1/contract.yaml"

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
    assert d["mates"] == "lc"
    assert d["interface"] == "lc-plug"
    assert d["conforms"] == "lc-plug"
    assert d["kind"] == "component"
    assert d["optical"]["positions"] == 1


def test_no_behaviour_despite_the_plan_table():
    """The plan's Task 4 table says `behaviour: occupies`, but this class is
    shared with std/lc-bore@3 (the aperture the plug enters), and
    test_behaviour.py::test_a_receptacle_does_not_move asserts every
    `class: port` contract carries no `behaviour` at all. std/lc-bore@3 itself
    seats a mate-to occupant with no `behaviour` set - the field only drives
    the 3D viewer's eject affordance, not the mate-to math - so omitting it
    keeps this part working and keeps that invariant intact. See
    provenance.behaviour for the full account."""
    d = contract()
    assert "behaviour" not in d
    assert "behaviour" in d["provenance"]


def test_size_has_no_depth():
    d = contract()
    assert d["size"] == {"w": 5.58, "h": 10.43}
    assert "d" not in d["size"], (
        "an LC plug has no class-wide overall length - see the contract's "
        "provenance.size and spec/tests/test_plug_envelopes.py")


def test_size_says_why_there_is_no_depth():
    """provenance.size must be actionable for a future reader, not just an
    absence - it should name the REF dimension and say it is not a class
    figure."""
    prov = contract()["provenance"]["size"]
    assert "REF" in prov or "reference" in prov.lower()
    assert "42" in prov, "should name at least one of the disagreeing REF figures"


def test_the_four_tiers_are_the_part():
    d = contract()
    elems = d["elements"]
    assert set(elems) == {"tip", "neck", "shoulder", "body"}
    widths = {k: v["size"][0] for k, v in elems.items()}
    assert widths == {"tip": 2.3, "neck": 3.3, "shoulder": 4.3, "body": 5.58}
    # narrower toward the tip, which is the latch end
    assert widths["tip"] < widths["neck"] < widths["shoulder"] < widths["body"]
    heights = sum(v["size"][1] for v in elems.values())
    assert abs(heights - 10.43) < 0.01, "the four tiers must sum to the drawn 10.43"


def test_connection_points_share_the_optical_axis():
    cps = contract()["connection-points"]
    assert set(cps) == {"mate", "boot", "cable"}
    assert cps["mate"]["direction"] == "front"
    assert cps["boot"]["direction"] == "rear"
    assert cps["cable"]["direction"] == "rear"
    # front and rear are the same physical axis, seen from two directions
    assert cps["mate"]["at"] == cps["boot"]["at"] == cps["cable"]["at"]


def test_it_lints_clean_alone():
    """L9 (size against the registry), L11 (mating - both `mates` and
    `interface` need a usable 'mate' point) and L99 (a generic under
    class: transceiver stays generic - not applicable here since class is
    `port`, but run it anyway so a future reclass is still checked)."""
    assert rule_errors(P, "L9", "L11", "L99") == []


def test_skin_matches_the_four_elements():
    svg = (P.parent / "skins/default.svg").read_text()
    for el in ("tip", "neck", "shoulder", "body"):
        assert f'id="{el}"' in svg, el
