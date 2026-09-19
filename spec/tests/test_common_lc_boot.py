"""common/lc-boot: a strain-relief boot for an LC plug, sized to the plug BODY
it wraps rather than the plug's own front-view silhouette
(docs/superpowers/plans/2026-09-19-pluggables-b2-connector-parts.md, Task 5).

`class: boot` did not exist before this part; it is added to the `passive`
role in spec/schemas/power-roles.yaml in the same commit, because L51 refuses
a class that sits in no power role. The class-existence test below is the
part of this file that would fail loudest if that commit were ever split.

WHY common/ AND NOT generic/. No standard governs a boot - its size follows
the cable OD and the vendor's own tooling, and SENKO alone lists six boot
options for the LC 2PC family and four more for the LC-HD. A `generic/` boot
would present one vendor's accessory as the class shape, which is what L99
refuses for a transceiver a level up. `common/` is the shape-for-a-class
namespace with no standards claim; common/qsfp-pull-tab@1 is the model this
follows.
"""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/common/lc-boot/v1/contract.yaml"
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


def test_boot_is_a_power_role_passive():
    roles = yaml.safe_load(POWER_ROLES.read_text())["roles"]
    assert "boot" in roles["passive"], (
        "L51 refuses a class in no power role - add 'boot' to the passive "
        "role in spec/schemas/power-roles.yaml")
    for role, classes in roles.items():
        if role != "passive":
            assert "boot" not in classes, f"boot must sit in exactly one role, found in {role} too"


def test_shape():
    d = contract()
    assert d["kind"] == "component"
    assert d["class"] == "boot"
    assert d["mates"] == "lc-plug"


def test_size_is_the_plug_body_not_the_silhouette():
    """5.58 x 5.65 is the plug BODY (side-view body height, front-view body
    width) - not the plug's own 5.58 x 10.43 front-view silhouette, which
    includes the latch a boot does not wrap."""
    d = contract()
    assert d["size"] == {"w": 5.58, "h": 5.65}
    plug = yaml.safe_load(
        (LIB / "components/generic/lc-plug/v1/contract.yaml").read_text())
    assert d["size"]["w"] == plug["size"]["w"], "w is borrowed from the plug body width"
    assert d["size"]["h"] != plug["size"]["h"], (
        "h must NOT equal the plug's front-view silhouette height (10.43) - "
        "that figure includes the latch, which the boot does not wrap")


def test_boot_length_attr():
    d = contract()
    assert d["attrs"]["boot-length"] == 15.1


def test_connection_points():
    cps = contract()["connection-points"]
    assert set(cps) == {"mate", "cable"}
    assert cps["mate"]["direction"] == "front"
    assert cps["cable"]["direction"] == "rear"
    assert cps["mate"]["at"] == cps["cable"]["at"], (
        "front and rear share the optical axis, same reasoning as the plug")


def test_provenance_says_why_this_is_common_not_generic():
    prov = contract()["provenance"]["standard"]
    assert "no standard" in prov.lower() or "no published standard" in prov.lower()
    assert "generic" in prov


def test_it_lints_clean_alone():
    """L9 does not apply (no `conforms`); L11 checks `mates` has a usable
    'mate' connection point."""
    assert rule_errors(P, "L9", "L11") == []
