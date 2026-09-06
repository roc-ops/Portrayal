"""L22 and L23 - a port group is one family, and its attrs are true of its members.

A group is where a block of ports says its facts once, and the renderer merges
them down into every member. That only pays off if the block really is one
family, and it is only safe if the block's promise matches what it holds.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402


def check(dev):
    """Run L22/L23 over an in-memory manifest and return (errors, warnings)."""
    lint.ERRORS, lint.WARNINGS = [], []
    lint.lint_device_groups(Path("test.yaml"), dev, [str(LIB)])
    return lint.ERRORS, lint.WARNINGS


def device(groups, placements):
    return {"groups": groups,
            "views": {"front": {"components": {"placements": placements}}}}


SFP28 = {"term": "Port", "attrs": {"media": "sfp28", "speed": "25g"}}


def test_a_family_cage_may_be_narrowed_by_its_group():
    """std/sfp-ganged can only ever say `sfp` - one cage serves SFP, SFP+ and
    SFP28 - so a group declaring sfp28 over it is the intended use, not a clash."""
    errs, warns = check(device({"sfp28": SFP28}, [
        {"id": "port-1", "ref": "std/sfp-ganged@1", "group": "sfp28"},
        {"id": "port-2", "ref": "std/sfp-ganged@1", "group": "sfp28"},
    ]))
    assert errs == [] and warns == []


def test_a_group_may_not_relabel_a_port_of_another_family():
    """The whole reason L22 is an error: group attrs are merged into every
    member, so without this an RJ45 draws as SFP28 and the drawing says so."""
    errs, _ = check(device({"sfp28": SFP28}, [
        {"id": "port-1", "ref": "std/sfp-ganged@1", "group": "sfp28"},
        {"id": "port-2", "ref": "common/rj45-eth@1", "group": "sfp28"},
    ]))
    assert len(errs) == 1 and "[L22]" in errs[0] and "port-2" in errs[0]


def test_a_port_may_not_declare_a_different_media_from_its_group():
    errs, _ = check(device({"sfp28": SFP28}, [
        {"id": "port-1", "ref": "std/sfp-ganged@1", "group": "sfp28",
         "attrs": {"media": "sfp-plus"}},
    ]))
    assert len(errs) == 1 and "[L22]" in errs[0]


def test_a_port_may_not_declare_a_different_speed_from_its_group():
    errs, _ = check(device({"sfp28": SFP28}, [
        {"id": "port-1", "ref": "std/sfp-ganged@1", "group": "sfp28",
         "attrs": {"speed": "10g"}},
    ]))
    assert len(errs) == 1 and "[L22]" in errs[0] and "speed" in errs[0]


def test_a_bucket_of_three_families_is_a_warning_that_names_them():
    """The S9510-28DC as it was: `ports` holding QSFP-DD/400G, QSFP28/100G and
    SFP28/25G, which is why it could carry no attrs at all."""
    _, warns = check(device({"ports": {"term": "Port"}}, [
        {"id": "port-0", "ref": "common/qsfp-cage@2", "group": "ports",
         "attrs": {"media": "qsfp-dd", "speed": "400g"}},
        {"id": "port-2", "ref": "common/qsfp-cage@2", "group": "ports",
         "attrs": {"media": "qsfp28", "speed": "100g"}},
        {"id": "port-4", "ref": "std/sfp-ganged@1", "group": "ports",
         "attrs": {"media": "sfp28", "speed": "25g"}},
    ]))
    assert len(warns) == 1 and "[L23]" in warns[0]
    for m in ("qsfp-dd", "qsfp28", "sfp28", "400g"):
        assert m in warns[0]


def test_a_declared_mixture_is_an_answer_not_an_exemption():
    """as7326-56x/mgmt is SFP+, USB-A, RJ45, serial and USB-C because the
    vendor's faceplate calls it one cluster. Splitting it by media would be a
    worse drawing, so the author says so and L23 accepts it."""
    _, warns = check(device({"mgmt": {"term": "Port", "mixed": "management cluster"}}, [
        {"id": "port-57", "ref": "std/sfp-ganged@1", "group": "mgmt",
         "attrs": {"media": "sfp-plus", "speed": "10g"}},
        {"id": "usb-a", "ref": "std/usb-a@1", "group": "mgmt"},
        {"id": "console", "ref": "std/rj45@2", "group": "mgmt",
         "attrs": {"media": "rj45-serial"}},
    ]))
    assert warns == []


def test_mixed_on_a_group_that_is_not_mixed_is_also_wrong():
    """`mixed:` states a fact about the hardware. A block that is one family
    does not get to claim it, or the field decays into a silencer."""
    _, warns = check(device({"sfp28": dict(SFP28, mixed="management cluster")}, [
        {"id": "port-1", "ref": "std/sfp-ganged@1", "group": "sfp28"},
    ]))
    assert len(warns) == 1 and "[L23]" in warns[0] and "drop it" in warns[0]


def test_the_portfolio_is_clean():
    """Every device in the library passes both rules. L23 is a warning so that
    it can land without going red everywhere - but there is nothing left for it
    to say, and this is what keeps that true."""
    for man in sorted(LIB.glob("devices/*/*/device.yaml")):
        errs, warns = check(yaml.safe_load(man.read_text()))
        assert errs == [], (man, errs)
        assert warns == [], (man, warns)
