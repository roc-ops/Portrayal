"""`faces:` - a part naming its own drawings seen from other directions.

The legacy spelling is a top-level `plan: {ref}`. The new one is
`faces: {plan: {ref}, rear: {ref}}`. Both must mean the same thing for `plan`,
and the library must never carry both on one contract, because then a reader has
to guess which the author meant.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import faces as F  # noqa: E402
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]


def run82(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_faces_once(path, doc)
    return [e for e in L.ERRORS if "[L82]" in e]


def test_the_legacy_spelling_still_answers():
    assert F.face_ref({"plan": {"ref": "dell/riser-card-14g@1"}}, "plan") == \
        "dell/riser-card-14g@1"


def test_the_new_spelling_answers_the_same_way():
    assert F.face_ref({"faces": {"plan": {"ref": "dell/riser-card-14g@1"}}},
                      "plan") == "dell/riser-card-14g@1"


def test_a_rear_face_has_no_legacy_spelling_to_fall_back_to():
    """`rear` is new, so it reads `faces` only - there is no top-level `rear:`."""
    assert F.face_ref({"faces": {"rear": {"ref": "fs/x-rear@1"}}}, "rear") == \
        "fs/x-rear@1"
    assert F.face_ref({"rear": {"ref": "fs/x-rear@1"}}, "rear") is None


def test_a_part_with_no_faces_at_all_answers_none():
    assert F.face_ref({}, "plan") is None
    assert F.face_ref({}, "rear") is None


def test_saying_it_both_ways_is_an_error():
    got = run82({"plan": {"ref": "a/b@1"},
                 "faces": {"plan": {"ref": "a/c@1"}}})
    assert len(got) == 1, got
    assert "faces.plan" in got[0]


def test_saying_it_both_ways_is_an_error_even_when_they_agree():
    """Agreeing today is not the point - one of them gets edited tomorrow."""
    got = run82({"plan": {"ref": "a/b@1"},
                 "faces": {"plan": {"ref": "a/b@1"}}})
    assert len(got) == 1, got


def test_one_spelling_or_the_other_is_quiet():
    assert run82({"plan": {"ref": "a/b@1"}}) == []
    assert run82({"faces": {"plan": {"ref": "a/b@1"}}}) == []
    assert run82({"faces": {"rear": {"ref": "a/b@1"}}}) == []
    assert run82({}) == []
