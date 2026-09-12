"""The optical rules fire on their defect and stay quiet on the real thing.

Each rule gets both halves. A rule that only ever fires is as useless as one
that never does, and the quiet half is the one that breaks silently when a
predicate is tightened - which is how a fixture that could not tell `!seen` from
`!seen && named` shipped in this repo before.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]


def run(rule, doc, code=None, path="t/contract.yaml"):
    """Call ONE rule and return ONLY its errors.

    Every optical rule takes `(path, data, lib_roots)` - the ones that do not
    need the roots accept and ignore them - so one call shape serves all three.

    Filtering on a substring like "L8" would also catch L80 while testing L81,
    and would quietly pass if a rule started raising under the wrong code, so
    `code` narrows to one rule when a test cares which fired.
    """
    L.ERRORS.clear()
    rule(path, doc, LIB)
    return [e for e in L.ERRORS
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
