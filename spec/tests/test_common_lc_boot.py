"""common/lc-boot: a strain-relief boot for an LC plug, sized to the BOOT's own
6.2 square block rather than to the plug it wraps
(docs/pluggables-connectors-design.md).

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


def test_size_is_the_boots_own_block():
    """6.2 x 6.2 is the BOOT's own outer block, off the boot's own drawing.

    It was 5.58 x 5.65, which is the plug body EXACTLY - w borrowed from the
    plug's front view, h read off the plug's side view. A boot the size of
    what it wraps has ZERO WALL, which is the very thing
    common/rj45-boot@1's own provenance calls wrong.
    """
    d = contract()
    assert d["size"] == {"w": 6.2, "h": 6.2}
    assert d["size-confidence"] == {"w": "drawing", "h": "drawing"}, (
        "both figures now come off the BOOT's own sub-assembly - the old h "
        "was labelled `drawing` while citing a PLUG figure")


def test_the_boot_goes_round_the_outside_of_the_plug():
    """The invariant the old size broke, stated against the plug it wraps.

    A boot is not the plug body and it is not the plug's front-view
    silhouette: it goes AROUND the body, so it must be strictly larger than
    the body in both axes, and it must not reach the silhouette height, which
    includes a latch the boot does not cover.
    """
    d = contract()
    plug = yaml.safe_load(
        (LIB / "components/generic/lc-plug/v2/contract.yaml").read_text())
    body_w = plug["size"]["w"]
    body_h = plug["elements"]["body"]["size"][1]
    assert d["size"]["w"] > body_w, (
        f"the boot is {d['size']['w']} wide around a {body_w} plug body - a "
        f"boot that is exactly what it wraps has no wall")
    assert d["size"]["h"] > body_h, (
        f"the boot is {d['size']['h']} tall around a {body_h} plug body")
    assert d["size"]["h"] < plug["size"]["h"], (
        "the boot must not reach the plug's front-view silhouette height "
        "(10.43), which includes the latch it does not wrap")


def test_boot_length_attr():
    d = contract()
    assert d["attrs"]["boot-length"] == 15.1


def test_the_skin_is_the_contract():
    import re
    svg = (P.parent / "skins/default.svg").read_text()
    d = contract()
    body = d["elements"]["body"]
    # the body is a group since pluggables D (its bore paints on the rear
    # face the `body` feature extrudes); its outline is the group's rect
    m = re.search(r'<g id="body"[^>]*>\s*<rect [^>]*>', svg)
    assert m
    got = {k: float(re.search(rf'\b{k}="([-\d.]+)"', m.group(0)).group(1))
           for k in ("x", "y", "width", "height")}
    assert (got["width"], got["height"]) == (body["size"][0], body["size"][1])
    assert f'viewBox="0 0 {body["size"][0]} {body["size"][1]}"' in svg
    axis = d["connection-points"]["mate"]["at"]
    b = re.search(r'<circle id="bore"[^>]*>', svg)
    assert b
    assert [float(re.search(r'cx="([-\d.]+)"', b.group(0)).group(1)),
            float(re.search(r'cy="([-\d.]+)"', b.group(0)).group(1))] == axis


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
