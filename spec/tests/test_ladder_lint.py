"""The pluggable ladder registry (spec/schemas/pluggables.yaml) answers to the
corpus, in both directions - and the two directions are two different rule
numbers because they disagree about severity.

L102 asks whether something IN THE TREE resolves against the registry: a
device's pluggable `media` (a port group fact) and a part's `rate` attr (a
component fact) are the same underlying question - "does spec/schemas/
pluggables.yaml have a rung for this value" - asked at the two places the
value can appear, the way L100 asks "no attrs key is null" at both scopes
under one code. Both are ERROR: a value the registry cannot place is a
contradiction between two files this repository owns, not a datasheet
problem, and silence here is exactly what would let Task 3's accept list
quietly produce nothing for a real port.

L103 asks the question the other way: does a family's `interface` name a cage
anything in the library actually IS. This is WARNING, not error, because
`sfp-dd` genuinely has no cage in the library today and the media vocabulary
needs the family anyway - failing the whole corpus over a registry entry that
is correct would be worse than the gap it reports.

Component-scope L102 (`rate` vs `mates`) is exercised entirely with synthetic
contracts, per the brief: nothing in the library declares `rate` yet, so a
"does this fire on the real corpus" test for that half would only ever prove
a vacuous truth. Device-scope L102 (`media` vs the rate union) and L103
(`interface` vs the component corpus) are each run against the real library
too, because those DO have a real corpus to disagree with, and the whole
point of this file is that the registry answers to it.
"""
import pathlib
import re

import yaml

import libdata
from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _l102(warnings_or_errors, code="L102"):
    return [e for e in warnings_or_errors if f"[{code}]" in e]


# --- component scope: a part's `rate`, against the family its `mates` names -

def run_component(doc, path="t/contract.yaml"):
    with L.collecting() as found:
        L.lint_component_pluggable_rate(path, doc)
    return _l102(found.errors)


def test_no_rate_is_not_asked():
    assert run_component({"class": "transceiver"}) == []


def test_a_rate_matching_its_mates_family_is_clean():
    # sfp28 is a rung of the `sfp` family (SFF-8432: sfp/sfp-plus/sfp28/sfp56)
    got = run_component({"class": "transceiver", "mates": "sfp",
                          "attrs": {"rate": "sfp28"}})
    assert got == [], got


def test_a_rate_outside_its_mates_family_is_an_error():
    # qsfp28 is a QSFP rung, not an SFP one - mates: sfp and rate: qsfp28
    # disagree about what kind of module this is.
    got = run_component({"class": "transceiver", "mates": "sfp",
                          "attrs": {"rate": "qsfp28"}})
    assert len(got) == 1, got
    assert "qsfp28" in got[0] and "sfp" in got[0]


def test_a_rate_with_no_mates_names_no_family():
    """`rate` presupposes a family to check it against. No `mates` at all is
    the same defect as a `mates` that names nothing in the registry - there
    is nothing on the other end of the claim."""
    got = run_component({"class": "transceiver", "attrs": {"rate": "sfp28"}})
    assert len(got) == 1, got
    assert "no family" in got[0]


def test_a_rate_whose_mates_is_not_a_pluggable_interface_names_no_family():
    got = run_component({"class": "transceiver", "mates": "rj45",
                          "attrs": {"rate": "sfp28"}})
    assert len(got) == 1, got
    assert "no family" in got[0]


def test_sectioned_attrs_are_flattened_the_same_way():
    """Component attrs can be sectioned like a device's; the rule must not
    only recognise a flat bag."""
    got = run_component({"class": "transceiver", "mates": "qsfp",
                          "attrs": {"performance": {"rate": "qsfp112"}}})
    assert got == [], got
    got = run_component({"class": "transceiver", "mates": "qsfp",
                          "attrs": {"performance": {"rate": "sfp28"}}})
    assert len(got) == 1, got


def test_no_component_in_the_library_declares_rate_yet():
    """The brief's own premise: this check fires on nothing today because
    nothing has been built to fire on. Confirms the rule is exercised only by
    synthetic data above, and that the corpus run below finding zero L102
    component errors is not a coincidence of an untested code path."""
    with_rate = [ref for ref, _path, doc in libdata.components()
                 if "rate" in (doc.get("attrs") or {})]
    assert with_rate == [], with_rate


def test_every_real_component_is_clean():
    with L.collecting() as found:
        for _ref, path, doc in libdata.components():
            L.lint_component_pluggable_rate(path, doc)
    assert _l102(found.errors) == []


# --- device scope: a port group's `media`, against the rate union ----------

def run_device(doc, path="t/device.yaml"):
    with L.collecting() as found:
        L.lint_device_pluggable_media(path, doc)
    return _l102(found.errors)


def test_a_group_with_no_media_is_not_asked():
    assert run_device({"groups": {"g0": {"term": "Port"}}}) == []


def test_a_non_port_group_is_not_asked():
    assert run_device({"groups": {"g0": {"term": "Power",
                                          "attrs": {"media": "iec-c14"}}}}) == []


def test_a_non_pluggable_media_is_not_asked():
    """rj45/fiber/usb-c/coax-smb are real `media` values on real devices and
    none of them are cages - PLUGGABLE_CAGES is the same filter L40 uses to
    leave them alone, and this rule reuses it rather than reinventing it."""
    assert run_device({"groups": {"g0": {"term": "Port",
                                          "attrs": {"media": "rj45"}}}}) == []


def test_a_pluggable_media_that_resolves_is_clean():
    got = run_device({"groups": {"g0": {"term": "Port",
                                         "attrs": {"media": "qsfp28"}}}})
    assert got == [], got


def test_a_pluggable_media_the_registry_cannot_place_is_an_error(monkeypatch):
    """Built by taking a rate OUT of the real registry rather than inventing a
    fake media value - this is the shape the rule exists to catch: a value
    PLUGGABLE_CAGES still recognises as a cage (L40's vocabulary has not
    moved) that spec/schemas/pluggables.yaml no longer carries as a rate
    (the registry's own ladder has)."""
    assert "sfp56" in L.PLUGGABLE_CAGES
    stripped = {name: dict(fam, rates=[r for r in fam["rates"] if r != "sfp56"])
                for name, fam in L.PLUGGABLE_FAMILIES.items()}
    monkeypatch.setattr(L, "PLUGGABLE_FAMILIES", stripped)
    got = run_device({"groups": {"g0": {"term": "Port",
                                         "attrs": {"media": "sfp56"}}}})
    assert len(got) == 1, got
    assert "sfp56" in got[0]


def test_every_real_device_port_group_resolves():
    """The corpus run the brief asks for: zero L102 findings against every
    device in the library today. #243/#244's own T0/T1 work already proved
    PLUGGABLE_CAGES and the registry's rate union agree exactly
    (test_pluggable_ladder.py); this is that same fact, asked from a real
    device rather than from the vocabulary the registry was built from."""
    with L.collecting() as found:
        for _slug, path, doc in libdata.library():
            L.lint_device_pluggable_media(path, doc)
    assert _l102(found.errors) == []


# --- library scope: a family's `interface`, against the component corpus ---

FAMILY_IN_WARNING = re.compile(r"family '([^']+)'")


def run_library(root):
    with L.collecting() as found:
        L.lint_pluggable_family_interfaces(root)
    return [w for w in found.warnings if "[L103]" in w]


def _families_named(warnings):
    return {FAMILY_IN_WARNING.search(w).group(1) for w in warnings}


def test_the_real_library_warns_for_sfp_dd_and_nothing_else():
    """sfp-dd is the one family with no cage in the library today, and the
    brief is explicit that a warning here for any OTHER family is a genuine
    registry/corpus disagreement to report, not to silence."""
    got = run_library(LIB)
    assert _families_named(got) == {"sfp-dd"}, got


def test_a_family_with_no_cage_anywhere_warns(monkeypatch):
    """Built by adding an extra family the real corpus cannot possibly
    satisfy, so the warning is not incidentally the sfp-dd one above."""
    extra = dict(L.PLUGGABLE_FAMILIES)
    extra["make-believe"] = {"interface": "make-believe-cage",
                              "rates": ["make-believe-cage"],
                              "source": "synthetic, for the test only"}
    monkeypatch.setattr(L, "PLUGGABLE_FAMILIES", extra)
    got = run_library(LIB)
    families = _families_named(got)
    assert "make-believe" in families, got
    assert "sfp-dd" in families, got


def test_a_family_whose_interface_is_modelled_does_not_warn(monkeypatch):
    """The clean half of the same check, built the same way - add a family
    whose interface a real component in the library does declare, and
    confirm it earns no warning."""
    extra = dict(L.PLUGGABLE_FAMILIES)
    extra["already-modelled"] = {"interface": "sfp", "rates": ["sfp"],
                                  "source": "synthetic, for the test only"}
    monkeypatch.setattr(L, "PLUGGABLE_FAMILIES", extra)
    got = run_library(LIB)
    assert "already-modelled" not in _families_named(got), got


def test_a_missing_components_dir_warns_for_nothing():
    """A root with no `components/` at all (a bad path, a library that is
    only devices) is treated as nothing to check against, the same as
    `lint_vendor_registry` and `lint_unplaced_majors` treat a missing
    directory - it returns rather than raising or warning about every family."""
    got = run_library(pathlib.Path("/nonexistent-portrayal-library-root"))
    assert got == []


def test_an_empty_components_dir_warns_for_every_family(tmp_path):
    (tmp_path / "components").mkdir()
    got = run_library(tmp_path)
    assert _families_named(got) == set(L.PLUGGABLE_FAMILIES), got


# --- device scope: a group's `media` vs its cage's presented `interface` ----
#
# render.py's cages[] derivation (spec C1 task 3) found this, not a person:
# giving the accept list a real audience turned "does the group's media agree
# with the cage's drawn aperture" into a question that had an answer for the
# first time. 78 ports across 6 real devices disagree - group media qsfp-dd
# on a placement modelled with std/qsfp-ganged@1, a QSFP aperture - and
# render.py's precedence rule (the group's media governs) already serves the
# right optic there; L104 is what keeps the disagreement itself visible.

def run_cage_media(doc, path="t/device.yaml"):
    with L.collecting() as found:
        L.lint_device_cage_media_disagreement(path, doc, [LIB])
    return [w for w in found.warnings if "[L104]" in w]


def _one_placement_device(media, ref, group="g0"):
    return {"groups": {group: {"term": "Port", "attrs": {"media": media}}},
            "views": {"front": {"components": {"placements": [
                {"id": "p0", "ref": ref, "group": group, "at": [0, 0]}]}}}}


def test_agreeing_media_and_interface_is_clean():
    # std/sfp-ganged@1 presents `sfp`; `sfp-plus` is a rung of the SAME `sfp`
    # family (SFF-8432), so the two name one family and nothing fires.
    got = run_cage_media(_one_placement_device("sfp-plus", "std/sfp-ganged@1"))
    assert got == [], got


def test_disagreeing_media_and_interface_warns():
    # The exact shape the real corpus has: group media qsfp-dd, aperture
    # std/qsfp-ganged@1 (interface qsfp) - QSFP-DD and QSFP are different
    # families.
    got = run_cage_media(_one_placement_device("qsfp-dd", "std/qsfp-ganged@1"))
    assert len(got) == 1, got
    assert "front/p0" in got[0]
    assert "qsfp-dd" in got[0] and "'qsfp'" in got[0]


def test_a_placement_with_no_group_is_not_asked():
    doc = {"views": {"front": {"components": {"placements": [
        {"id": "p0", "ref": "std/qsfp-ganged@1", "at": [0, 0]}]}}}}
    assert run_cage_media(doc) == []


def test_a_group_with_no_media_is_not_asked_by_l104():
    doc = {"groups": {"g0": {"term": "Port"}},
            "views": {"front": {"components": {"placements": [
                {"id": "p0", "ref": "std/qsfp-ganged@1", "group": "g0", "at": [0, 0]}]}}}}
    assert run_cage_media(doc) == []


def test_an_interface_outside_the_registry_is_not_asked():
    """`common/lc-boot@1` mates `lc-plug`, which names no family - and a
    placement whose OWN ref presents no registry interface either should not
    be compared against a media value it has nothing to disagree with."""
    doc = _one_placement_device("qsfp-dd", "common/lc-boot@1")
    assert run_cage_media(doc) == []


def test_a_media_the_registry_cannot_place_is_not_asked_by_l104():
    """A media value with no family at all (L102's question) has nothing for
    this rule to compare either - L102 already reports it, and L104 doubling
    up on the same gap would be the same defect reported twice."""
    doc = _one_placement_device("not-a-real-media", "std/qsfp-ganged@1")
    assert run_cage_media(doc) == []


def test_every_real_device_cage_media_disagreement_is_this_exact_set():
    """The corpus count and the seven devices it falls on, pinned exactly - a
    wrong count, high or low, fails loudly rather than needing a second manual
    recount. 78 across six devices when L104 read only the port group; the
    79th, `smartoptics/dcp-sc-28p`, declares its media on the placement."""
    per_device = {}
    for slug, path, doc in libdata.library():
        n = len(run_cage_media(doc, path))
        if n:
            per_device[slug] = n
    assert per_device == {
        "edgecore/as7946-30xb": 8,
        "edgecore/as7946-74xksb": 2,
        "edgecore/csr440": 2,
        "edgecore/dcs240": 32,
        "edgecore/dcs511": 32,
        "smartoptics/dcp-sc-28p": 1,
        "ufispace/s9510-28dc": 2,
    }, per_device
    assert sum(per_device.values()) == 79


def test_a_placement_declared_media_is_read_before_its_group():
    """The placement's own `attrs.media` is L18's first source and L104's, so
    a port that declares its media there - with no group media at all - is
    compared, not skipped. Without this the corpus's 79th disagreement, and
    the wrong accept list it produced, were both invisible."""
    doc = {"groups": {"g0": {"term": "Port"}},
           "views": {"front": {"components": {"placements": [
               {"id": "p0", "ref": "std/qsfp-ganged@1", "group": "g0",
                "at": [0, 0], "attrs": {"media": "qsfp-dd"}}]}}}}
    got = run_cage_media(doc)
    assert len(got) == 1, got
    assert "the placement declares media" in got[0], got[0]


# --- registration ------------------------------------------------------------

def test_l102_is_registered_for_both_scopes():
    assert L.RULES["L102"][0] == "component, device"


def test_l103_is_registered_as_a_library_rule():
    assert L.RULES["L103"][0] == "library"


def test_l104_is_registered_as_a_device_rule():
    assert L.RULES["L104"][0] == "device"


# --- the registry itself, loaded by lint.py exactly as pluggables.yaml holds it

def test_lint_loads_the_same_registry_the_file_holds():
    doc = yaml.safe_load((ROOT / "spec/schemas/pluggables.yaml").read_text())
    assert L.PLUGGABLE_FAMILIES == doc["families"]
