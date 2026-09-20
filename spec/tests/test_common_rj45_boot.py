"""common/rj45-boot: a strain-relief boot for an RJ45 (8P8C) copper plug,
sized to the boot's OWN body (docs/superpowers/plans/2026-09-19-pluggables-
b2-connector-parts.md, Task 7).

EASE Electronics J0072 rev A dimensions the mouth cross-section directly,
14.5 x 10.0, so this contract uses those figures rather than borrowing
anything from generic/rj45-plug@1. common/lc-boot@1 is now sourced from its
own drawing too; the two boots no longer follow different rules, and the
paragraph of provenance.size that used to defend the difference now records
that it is gone.

`h` IS THE BODY, NOT THE SILHOUETTE. The same view dimensions an overall 15.5
- the 10 body plus a 5.5 latch-slot tab - and `size.h` is the 10. That
matches generic/rj45-plug@1, whose `h` excludes its latch too, which is what
keeps a boot-against-plug comparison like-for-like.

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
    on EASE J0072 - not borrowed from generic/rj45-plug@1."""
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


def test_provenance_names_the_view_each_tolerance_comes_from():
    """BOTH tolerances are on this sheet, and the contract used to deny it.

    It asserted "THE DRAWING READS 10 +/-0.5, NOT 10 +/-0.4 - zoomed to
    1200dpi to be sure" while citing the mouth end view, which is the view
    that reads +/-0.4. The lower end view - the cable exit, R3 corners, 6.0
    bore - is the one that reads +/-0.5. The nominal is the same either way,
    so `size` never moved; the certainty claim was the defect, and a
    provenance that names a view has to name it correctly.
    """
    prov = contract()["provenance"]["size"]
    assert "10 +/-0.4" in prov and "10 +/-0.5" in prov, (
        "both tolerances are on the sheet and provenance must say so")
    lower = prov.lower()
    assert "both are on the sheet" in lower, (
        "the old claim denied one of two figures that are both on the sheet; "
        "provenance must say outright that both exist")
    assert "upper end view" in lower and "lower end view" in lower, (
        "each figure must be attributed to the view it is on")


def test_provenance_accounts_for_the_15_5_overall():
    """The same view dimensions an overall 15.5 that `size.h` is not.

    10 is the body; 15.5 is the body plus the 5.5 latch-slot tab below it. A
    contract that states one and never mentions the other leaves a reader no
    way to tell a deliberate choice from an oversight - and this one IS
    deliberate: generic/rj45-plug@1's `h` excludes its latch too, so boot
    against plug is a like-for-like comparison.
    """
    prov = contract()["provenance"]["size"]
    assert "15.5" in prov
    assert "rj45-plug" in prov, (
        "the choice is only defensible against the plug's own body-not-"
        "silhouette `h`; provenance must make that link")
    d = contract()
    assert d["size"]["h"] == 10.0, (
        "size.h is the body; if it ever becomes 15.5 the elements, the axis "
        "and both connection points move with it")


def test_the_skin_bore_is_sourced_in_both_axes():
    """The 11.9 is a callout; the height used to be invented and cite it anyway.

    The skin drew an 11.9 x 8.5 bore and its comment cited "the EASE J0072
    11.9 inner opening" for the whole rectangle. The drawing gives no height
    for that opening. It is now measured off the same view, and provenance
    carries the measurement rather than the skin implying a callout.
    """
    import re
    d = contract()
    assert "bore" in d["provenance"], (
        "a figure the skin draws and the drawing does not state needs its own "
        "provenance entry")
    bore_prov = d["provenance"]["bore"]
    assert "measured" in bore_prov.lower()
    assert "8.5" in bore_prov, "say what the invented figure was"

    svg = (P.parent / "skins/default.svg").read_text()
    m = re.search(r'<rect id="bore"[^>]*>', svg)
    assert m, "the skin must still draw the opening"
    got = {k: float(re.search(rf'\b{k}="([-\d.]+)"', m.group(0)).group(1))
           for k in ("x", "y", "width", "height")}
    assert got["width"] == 11.9, "the width is the drawing's callout"
    assert got["height"] != 8.5, "the invented height must be gone"
    assert str(got["height"]) in bore_prov, (
        f"the skin draws a bore {got['height']} high; provenance must state "
        f"that same figure and where it came from")
    # centred in the 10 body, as the measured walls are
    assert abs(got["y"] + got["height"] / 2 - contract()["size"]["h"] / 2) < 0.01
    assert abs(got["x"] + got["width"] / 2 - contract()["size"]["w"] / 2) < 0.01


def test_it_lints_clean_alone():
    """L9 does not apply (no `conforms`); L11 checks `mates` has a usable
    'mate' connection point and that behaviour: occupies has one too."""
    assert rule_errors(P, "L9", "L11") == []


def test_skin_has_the_body_node():
    svg = (P.parent / "skins/default.svg").read_text()
    assert 'id="body"' in svg
