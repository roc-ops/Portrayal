"""common/rj45-boot: a strain-relief boot for an RJ45 (8P8C) copper plug,
sized to the boot's OWN body (docs/superpowers/plans/2026-09-19-pluggables-
b2-connector-parts.md, Task 7).

UNLIKE common/lc-boot@1, this boot's own outer dimensions ARE given on its
drawing - EASE Electronics J0072 rev A dimensions the mouth cross-section
directly, 14.5 x 10.0 - so this contract uses those figures rather than
borrowing anything from generic/rj45-plug@1. The two boots are sized by
different rules because they had different source material, not because the
corpus disagrees with itself; provenance.size makes the argument in full so a
later "make them consistent" pass does not undo it.

`class: boot` already exists - added to the `passive` role in
spec/schemas/power-roles.yaml by Task 5 (common/lc-boot@1). This task must
NOT re-add it; the test below only asserts it is still there exactly once.
"""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/common/rj45-boot/v1/contract.yaml"
POWER_ROLES = ROOT / "spec/schemas/power-roles.yaml"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())

lint.STANDARDS.update(
    lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def component_errors(path):
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


def contract():
    return yaml.safe_load(P.read_text())


def test_boot_class_already_exists_exactly_once():
    roles = yaml.safe_load(POWER_ROLES.read_text())["roles"]
    assert "boot" in roles["passive"], (
        "Task 5 (common/lc-boot@1) already added boot to the passive role - "
        "this task must not re-add it")
    for role, classes in roles.items():
        if role != "passive":
            assert "boot" not in classes, f"boot must sit in exactly one role, found in {role} too"


def test_shape():
    d = contract()
    assert d["kind"] == "component"
    assert d["class"] == "boot"
    assert d["mates"] == "rj45-plug"
    assert d["behaviour"] == "occupies"


def test_size_is_the_boots_own_body_not_borrowed():
    """14.5 x 10.0 is the boot's OWN mouth cross-section, dimensioned directly
    on EASE J0072 - not borrowed from generic/rj45-plug@1 the way
    common/lc-boot@1 borrows its width from generic/lc-plug@1."""
    d = contract()
    assert d["size"] == {"w": 14.5, "h": 10.0}
    plug = yaml.safe_load(
        (LIB / "components/generic/rj45-plug/v1/contract.yaml").read_text())
    # larger than the plug body it wraps in both dimensions - a boot goes
    # around the outside
    assert d["size"]["w"] > plug["size"]["w"]
    assert d["size"]["h"] > plug["size"]["h"]


def test_boot_length_attr():
    d = contract()
    assert d["attrs"]["boot-length"] == 26.4


def test_connection_points():
    cps = contract()["connection-points"]
    assert set(cps) == {"mate", "cable"}
    assert cps["mate"]["direction"] == "front"
    assert cps["cable"]["direction"] == "rear"
    assert cps["mate"]["at"] == cps["cable"]["at"], (
        "front and rear share one axis, the same reasoning as the plug and "
        "as common/lc-boot@1 before it")


def test_provenance_says_why_this_is_common_not_generic():
    prov = contract()["provenance"]["standard"]
    assert "no standard" in prov.lower() or "no published standard" in prov.lower()
    assert "generic" in prov


def test_provenance_says_why_the_size_rule_differs_from_lc_boot():
    """The brief's own warning: someone will 'make them consistent' later
    unless provenance explains why the two boots are sized by different
    rules. Guard the explanation, not just the numbers."""
    prov = contract()["provenance"]["size"]
    assert "lc-boot" in prov
    assert "borrow" in prov.lower()


def test_it_lints_clean_alone():
    """L9 does not apply (no `conforms`); L11 checks `mates` has a usable
    'mate' connection point and that behaviour: occupies has one too."""
    assert rule_errors(P, "L9", "L11") == []


def test_skin_has_the_body_node():
    svg = (P.parent / "skins/default.svg").read_text()
    assert 'id="body"' in svg
