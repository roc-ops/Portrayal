"""The optical rules fire on their defect and stay quiet on the real thing.

Each rule gets both halves. A rule that only ever fires is as useless as one
that never does, and the quiet half is the one that breaks silently when a
predicate is tightened - which is how a fixture that could not tell `!seen` from
`!seen && named` shipped in this repo before.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint as L

LIB = [str(ROOT / "library")]


def run(rule, doc, code=None, path="t/contract.yaml"):
    """Call ONE rule and return ONLY its errors.

    Every optical rule takes `(path, data, lib_roots)` - the ones that do not
    need the roots accept and ignore them - so one call shape serves all three.

    Filtering on a substring like "L8" would also catch L80 while testing L81,
    and would quietly pass if a rule started raising under the wrong code, so
    `code` narrows to one rule when a test cares which fired.
    """
    with L.collecting() as _found:
        rule(path, doc, LIB)
    return [e for e in _found.errors
            if code is None or f"[{code}]" in e]


def module(paths, parts=None, unused=None):
    """A module composing two LC duplex adapters, which hold 2 positions each."""
    doc = {"kind": "module", "size": {"w": 55.4, "h": 19.5},
           "parts": parts if parts is not None else [
               {"ref": "common/lc-duplex-adapter@3", "id": "common"},
               {"ref": "common/lc-duplex-adapter@3", "id": "split"}],
           "optical": {"media": "os2", "paths": paths}}
    if unused:
        doc["optical"]["unused"] = unused
    return doc


def test_a_position_past_the_connectors_capacity_is_caught():
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "common.3", "to": "split.1"}]))
    assert len(hits) == 1, hits
    assert "common.3" in hits[0] and "2" in hits[0]


def test_an_endpoint_naming_no_composed_part_is_caught():
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "mtp-1.1", "to": "split.1"}]))
    assert len(hits) == 1 and "mtp-1" in hits[0], hits


def test_a_path_within_capacity_is_silent():
    assert run(L.lint_component_optical_endpoints,
               module([{"from": "common.1", "to": "split.2"}])) == []


def test_a_split_destination_is_checked_like_any_other_endpoint():
    """The ratio form must not be a hole the checker walks past."""
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 50},
                               {"at": "split.9", "ratio": 50}]}]))
    assert len(hits) == 1 and "split.9" in hits[0], hits


def test_a_malformed_endpoint_gets_its_own_message_not_the_unknown_part_one():
    """Pins the `except ValueError` branch, which the other tests never reach.

    `lint_component()` reports only the FIRST schema error and still returns
    the data, so a contract that fails schema validation somewhere else still
    flows into this rule carrying an endpoint string `optical.ENDPOINT` would
    have rejected. Without a test that exercises `split_endpoint` raising,
    that branch and its distinct "is not an optical endpoint" message could be
    deleted and this suite would stay green - the other tests only ever reach
    the "names {part!r}" and "asks for position" messages, both of which
    require `split_endpoint` to have already succeeded.
    """
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "bad", "to": "split.1"}]))
    assert len(hits) == 1, hits
    assert "is not an optical endpoint" in hits[0], hits


def test_two_paths_landing_on_one_position_are_caught():
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.1"}]))
    assert len(hits) == 1 and "split.1" in hits[0], hits


def test_one_source_feeding_two_destinations_is_NOT_a_conflict():
    """That is a split, which is the whole point of the graph form - as long as
    it is written as ONE path with a ratio list, which is the form the ratio
    check can actually see."""
    assert run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 50},
                               {"at": "split.2", "ratio": 50}]}])) == []


def test_the_same_source_in_two_plain_paths_is_caught():
    """A split written the long way hides its ratios from the check above.

    `{from: common.1, to: split.1}` and `{from: common.1, to: split.2}` each
    yield zero ratios via `endpoints()`, so the sum-to-100 check never runs -
    a 70/30 tap written this way carries no ratios anywhere the linter can see.
    A source is allowed to be a `from` in at most one path; a genuine split
    must use the ratio list, which is the one form L79 can verify.
    """
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.1", "to": "split.2"}]))
    assert len(hits) == 1 and "common.1" in hits[0], hits


def test_ratios_that_do_not_sum_to_100_are_caught():
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 70},
                               {"at": "split.2", "ratio": 40}]}]))
    assert len(hits) == 1 and "110" in hits[0], hits


def test_a_97_3_split_sums_and_is_silent():
    assert run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}])) == []


def test_a_position_no_path_reaches_and_no_entry_declares_is_caught():
    """ppm-ocu-97-3's dead bore, which is currently a sentence in provenance."""
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}]))
    assert len(hits) == 1 and "common.2" in hits[0], hits


def test_declaring_it_unused_silences_it():
    assert run(L.lint_component_optical_coverage,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}],
                      unused={"common.2": "three-port coupler in a four-bore "
                                          "faceplate"})) == []


def test_declaring_a_position_unused_that_a_path_DOES_reach_is_caught():
    """The rule has to bite both ways or `unused` becomes a way to silence it."""
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.2"}],
                      unused={"common.2": "this claim contradicts path 1 above"}))
    assert len(hits) == 1 and "common.2" in hits[0], hits


def test_an_unused_key_naming_no_real_position_is_caught():
    """`unused: {ghost.7: "..."}` or `common.9` on a two-bore adapter validates
    against the schema - `propertyNames` only checks the string shape - and
    the per-position loop above only ever walks real positions, so a bogus key
    was previously checked by nothing at all. An uncheckable claim is a defect
    here the same as a missing one.
    """
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.2"}],
                      unused={"ghost.7": "does not exist"}))
    assert len(hits) == 1 and "ghost.7" in hits[0], hits


def test_a_component_with_no_paths_at_all_is_not_checked_by_L80():
    """This is the rule's deliberate blind spot, not a bug.

    L80 only asks its question of a part that has opted in by declaring
    `optical.paths`. A component that composes connectors (here, two LC
    duplex adapters worth four positions) but declares zero paths returns
    before the coverage walk ever runs - every position of every composed
    connector escapes "reached or declared unused" unchecked. Running the
    rule on every component that merely composes a connector would error on
    every part in the library with an LC adapter and no optical model, which
    today is all of them, so it stays a guard rather than a check. Nothing
    else in this file catches this gap either.
    """
    assert run(L.lint_component_optical_coverage, module([])) == []
