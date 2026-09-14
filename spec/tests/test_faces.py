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


def test_render_reads_a_plan_through_the_accessor():
    """render.py must not spell out `.get("plan")` for a COMPONENT any more.

    The bay-side `plan:` - where a projection LANDS - is a different key and
    keeps its literal reads; this only checks the two component-side ones.
    """
    src = (ROOT / "spec/tools/portrayal/render.py").read_text()
    assert 'oc or {}).get("plan")' not in src, \
        "render.py:~1199 still reads a component's plan directly"
    assert 'sc or {}).get("plan")' not in src, \
        "render.py:~1218 still reads a component's plan directly"
    assert "face_ref(" in src, "render.py does not use the accessor at all"


def test_lint_reads_a_plan_through_the_accessor():
    src = (ROOT / "spec/tools/portrayal/lint.py").read_text()
    assert 'c.get("plan") or {}).get("ref")' not in src, \
        "lint.py:~5844 still reads a component's plan directly"


def test_the_accessor_answers_for_every_part_that_names_a_plan():
    """Thirteen parts name a plan drawing; the accessor must find all of them.

    Reads the real library rather than a fixture. Spelling-agnostic on purpose -
    it passes before Task 5's migration and after it, because what it watches is
    that no part LOSES its plan drawing, not which way the part spells it.
    """
    lib = ROOT / "library/components"
    named = [p for p in lib.glob("*/*/v*/contract.yaml")
             if F.face_ref(yaml.safe_load(p.read_text()) or {}, "plan")]
    assert len(named) == 13, \
        f"expected 13 parts naming a plan drawing, found {len(named)}"


def run83(doc, path="t/contract.yaml", name="t/thing@1"):
    L.ERRORS.clear()
    L.lint_component_rear_face(path, doc, LIB, name)
    return [e for e in L.ERRORS if "[L83]" in e]


def test_a_rear_face_must_name_a_component_that_exists():
    got = run83({"faces": {"rear": {"ref": "fs/not-a-real-part@1"}}})
    assert len(got) == 1, got
    assert "not in the library" in got[0]


def test_a_part_may_not_be_its_own_rear():
    got = run83({"faces": {"rear": {"ref": "common/mpo-adapter@1"}}},
                name="common/mpo-adapter@1")
    assert len(got) == 1, got
    assert "its own rear" in got[0]


def test_a_rear_face_may_not_itself_have_a_rear(tmp_path):
    """A part has one back. `a`'s rear being `b` whose rear is `c` means nothing.

    Builds its own two-component library rather than leaning on the real one
    staying arranged as it is - and the real library has no chain to point at,
    which is exactly why this rule exists before one appears.
    """
    d = tmp_path / "components" / "t" / "middle" / "v1"
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: middle\nversion: 1.0.0\n"
        "class: port\nsize: {w: 1, h: 1}\n"
        "faces: {rear: {ref: t/deepest@1}}\n")
    e = tmp_path / "components" / "t" / "deepest" / "v1"
    e.mkdir(parents=True)
    (e / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: deepest\nversion: 1.0.0\n"
        "class: port\nsize: {w: 1, h: 1}\n")

    L.ERRORS.clear()
    L.lint_component_rear_face("t/contract.yaml",
                               {"faces": {"rear": {"ref": "t/middle@1"}}},
                               [str(tmp_path)], "t/outer@1")
    got = [e for e in L.ERRORS if "[L83]" in e]
    assert len(got) == 1, got
    assert "rear of its own" in got[0]


def test_a_real_rear_reference_is_quiet():
    got = run83({"faces": {"rear": {"ref": "common/mpo-adapter@1"}}})
    assert got == [], got


def test_no_rear_at_all_is_quiet():
    assert run83({}) == []
    assert run83({"faces": {"plan": {"ref": "common/mpo-adapter@1"}}}) == []


def test_the_index_carries_a_parts_other_faces():
    """The viewer offers a rear drawing only if the index says there is one."""
    src = (ROOT / "spec/tools/portrayal/components_index.py").read_text()
    assert "face_ref(" in src, \
        "components_index.py never asks a contract for its faces, so the " \
        "viewer cannot know a part has a rear drawing"


def test_the_index_entry_omits_faces_when_there_are_none():
    """An empty dict on 700-odd entries is bytes on every page load.

    Reads the BUILT index, not the source that writes it - a source-text
    assertion passes against code that was rearranged and still emits `{}`.
    Skips when dist is absent so a bare checkout does not fail on it.
    """
    import json
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    entries = json.loads(f.read_text())["components"]
    empty = [e["name"] for e in entries if e.get("faces") == {}]
    assert not empty, f"these carry an empty faces object: {empty}"
