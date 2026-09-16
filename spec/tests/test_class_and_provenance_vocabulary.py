"""One list of classes, and a provenance key a rule can ask about.

roc-ops/Portrayal#173. Two vocabularies had grown without anything holding them
to a shape, and each had drifted in its own direction.

`class` had 40 values for 584 contracts, four of them synonyms of another four:
`cooling` against `fan` (nine fan trays and modules, split by who modelled
them - `comparable.py` already had to paper over it with
`FAN_WORDS = ("fan", "cooling")`), `fastener` against `screw`, `panel` against
`display` (the four MX craft interfaces, two under each), and `connector`
against `inlet`, whose own entry in power-roles.yaml said it was "the same
argument as `inlet` at the other polarity". A note saying a class is the same
argument as another class is a note saying it is that class.

`provenance` had gone the other way: 579 distinct keys across 584 contracts, 495
of them used fewer than five times, some of them whole sentences -
`adjacent-brackets-overlap-by-1.27-on-purpose`,
`where-the-electrical-facts-come-from`. The key had become a headline for the
note rather than a name for the figure, and the cost is that a rule cannot ask
whether a figure is sourced. L52 had to be loosened to accept "any power-named
key" after convicting eighteen contracts that had done the work; nothing could
ask about `size` at all, and 41 contracts had no note named for theirs.

THE CLASS LIST IS NOT IN THE SCHEMA ON PURPOSE. It lives in power-roles.yaml,
which is the file lint reads, because the same list in two places drifts and
only one of them would be enforced.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
from portrayal import lint

MERGED = {"cooling": "fan", "fastener": "screw", "panel": "display",
          "connector": "inlet"}


@pytest.fixture(scope="module")
def contracts():
    return {f"{c.parts[-4]}/{c.parts[-3]}@{c.parts[-2][1:]}": yaml.safe_load(c.read_text()) or {}
            for c in sorted(LIB.glob("components/*/*/v*/contract.yaml"))}


@pytest.fixture(scope="module")
def roles():
    return yaml.safe_load((ROOT / "spec/schemas/power-roles.yaml").read_text())["roles"]


# --- the class vocabulary -----------------------------------------------------

def test_there_are_contracts_to_check(contracts):
    """NON-VACUITY for every sweep below."""
    assert len(contracts) > 500


def test_every_class_the_library_uses_is_in_the_list(contracts, roles):
    """What L51 enforces at lint time, asserted over the corpus so a refactor of
    the rule cannot quietly stop enforcing it."""
    listed = {c for r in roles.values() for c in r}
    used = {d.get("class") for d in contracts.values()}
    assert not (used - listed), f"class(es) in no power role: {sorted(used - listed)}"


def test_the_list_has_no_class_the_library_does_not_use(contracts, roles):
    """THE OTHER DIRECTION, which nothing checked. `panel-blank` sat in the
    passive set and no contract carried it - dead vocabulary reads as a
    supported choice, and the next person to want that shape uses it instead of
    asking whether the library already has one."""
    listed = {c for r in roles.values() for c in r}
    used = {d.get("class") for d in contracts.values()}
    assert not (listed - used), f"listed and unused: {sorted(listed - used)}"


def test_a_class_sits_in_exactly_one_role(roles):
    flat = [c for r in roles.values() for c in r]
    dupes = {c for c in flat if flat.count(c) > 1}
    assert not dupes, f"class(es) in more than one role: {sorted(dupes)}"


@pytest.mark.parametrize("gone,kept", sorted(MERGED.items()))
def test_a_merged_class_does_not_come_back(contracts, roles, gone, kept):
    """Named one by one: each merge is its own argument about its own parts, and
    a regression on any of them is a separate mistake."""
    listed = {c for r in roles.values() for c in r}
    assert gone not in listed, f"{gone!r} is back in power-roles.yaml"
    assert kept in listed
    using = sorted(r for r, d in contracts.items() if d.get("class") == gone)
    assert not using, f"{gone!r} is back on {using}"


def test_the_fan_classes_really_did_come_together(contracts):
    """The merge that mattered - nine parts moved. Checks the parts arrived
    rather than that the name went away, which a deletion would also satisfy."""
    fans = {r for r, d in contracts.items() if d.get("class") == "fan"}
    for ref in ("casa/c40g-fan@1", "cisco/asr-9006-fan@1", "dell/fan-14g@1",
                "common/fan-module@1", "ufispace/fan-803816@1"):
        assert ref in fans, f"{ref} should be class fan"


def test_the_four_mx_craft_interfaces_share_a_class(contracts):
    """They were two and two, which is what a class split by nothing looks
    like."""
    got = {r: contracts[r].get("class") for r in
           ("juniper/mx240-craft@1", "juniper/mx480-craft@1",
            "juniper/mx2000-craft@1", "juniper/mx960-craft@1")}
    assert set(got.values()) == {"display"}, got


# --- the provenance key vocabulary -------------------------------------------

def run_l92(path, doc):
    lint.WARNINGS.clear()
    lint.lint_component_size_sourced(path, doc)
    return [w for w in lint.WARNINGS if "[L92]" in w]


def test_a_size_with_no_note_named_for_it_is_reported():
    doc = {"size": {"w": 1.0, "h": 1.0},
           "provenance": {"layout": "x", "depth": "y"}}
    found = run_l92("t.yaml", doc)
    assert len(found) == 1 and "no provenance key names it" in found[0]


def test_the_message_names_the_keys_the_contract_does_carry():
    """A rule that says a key is missing should say what is there, or the reader
    opens the file to find out."""
    doc = {"size": {"w": 1.0}, "provenance": {"layout": "x"}}
    assert "layout" in run_l92("t.yaml", doc)[0]


def test_a_size_key_satisfies_it():
    assert run_l92("t.yaml", {"size": {"w": 1.0}, "provenance": {"size": "datasheet"}}) == []


def test_an_axis_specific_key_still_answers():
    """`size-width` is a note about the size, so it counts. Splitting a figure
    across axes is a real need - common/qsfp-drawing gives its two axes
    different sources - and it must not cost the contract its answer."""
    assert run_l92("t.yaml", {"size": {"w": 1.0},
                              "provenance": {"size-width": "drawing"}}) == []


def test_a_part_with_no_size_is_not_asked():
    assert run_l92("t.yaml", {"provenance": {}}) == []


def test_the_thirteen_renamed_contracts_kept_their_note(contracts):
    """The rename moved a key, not a sentence. Each of these explained its size
    under `extent`, `face`, `geometry` or `overall`; the note is the same words
    under the name a rule can ask for."""
    for ref, must in (("edgecore/agr-filter-top@1", "353.5"),
                      ("edgecore/agr-psu-ac@1", "60.1"),
                      ("juniper/mx204-fan@1", "42.0"),
                      ("casa/brand-swoop@1", "48.66")):
        prov = contracts[ref].get("provenance") or {}
        assert "size" in prov, f"{ref} lost its size key"
        assert must in " ".join(str(prov["size"]).split()), f"{ref}: {prov['size'][:80]}"


def test_the_unsourced_sizes_are_counted_and_not_growing(contracts):
    """A CENSUS, like L27. 41 contracts stated a size no note named; 13 had the
    note under another name and were renamed, and 28 genuinely do not say -
    fourteen Dell risers, six Casa parts, four ground plates. The number is
    allowed to fall and not to rise."""
    unsourced = [r for r, d in contracts.items()
                 if d.get("size") and not any(
                     k == "size" or k.startswith("size")
                     for k in (d.get("provenance") or {}))]
    assert len(unsourced) <= 28, (
        f"{len(unsourced)} contracts state an unsourced size, up from 28:\n  "
        + "\n  ".join(sorted(unsourced)[:10]))
