"""L81: a composed pitch matches the standard the composed part conforms to.

The library held `lc-duplex-receptacle.pitch: 6.25` at verified confidence and
an adapter composing its bores 6.60 apart, and nothing compared them. This is
the rule that would have caught it, written after the fact so the next connector
cannot repeat it.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]

# STANDARDS IS EMPTY ON A PLAIN IMPORT, and that would make every test here pass
# for the wrong reason. `lint.py` fills it inside `main()`, so a unit test that
# calls a rule directly sees `{}`, the rule finds no standard for any `conforms`
# key, returns early, and raises nothing - a green suite against a rule that did
# nothing. Load it here, once, the same way main does.
L.STANDARDS.update(
    L.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def run(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_composed_pitch(path, doc, LIB)
    return [e for e in L.ERRORS if "[L81]" in e]


def test_the_standards_registry_is_loaded_for_these_tests():
    """Guard the guard: without this the rest of the file passes vacuously."""
    assert L.STANDARDS.get("lc-duplex-receptacle", {}).get("pitch") == 6.25


def adapter(xs):
    """A part composing `std/lc-bore@3` (4.7 wide, pitch 6.25) at these x."""
    return {"kind": "component", "size": {"w": 13.2, "h": 11.0},
            "parts": [{"ref": "std/lc-bore@3", "id": i, "at": [x, 1.55]}
                      for i, x in zip(("tx", "rx"), xs)]}


def test_a_composed_pitch_off_the_standard_is_caught():
    hits = run(adapter([0.95, 7.55]))          # 6.60 apart
    assert len(hits) == 1, hits
    assert "6.6" in hits[0] and "6.25" in hits[0]


def test_the_standard_pitch_is_silent():
    assert run(adapter([0.825, 7.075])) == []   # 6.25 apart


def test_one_instance_has_no_pitch_to_check():
    doc = {"kind": "component", "size": {"w": 6.0, "h": 11.0},
           "parts": [{"ref": "std/lc-bore@3", "id": "tx", "at": [0.65, 1.55]}]}
    assert run(doc) == []


def test_a_part_whose_standard_states_no_pitch_is_silent():
    """`conforms` alone is not enough - the standard must carry a `pitch`."""
    doc = {"kind": "component", "size": {"w": 40.0, "h": 20.0},
           "parts": [{"ref": "std/sfp@1", "id": "a", "at": [0.0, 0.0]},
                     {"ref": "std/sfp@1", "id": "b", "at": [20.0, 0.0]}]}
    assert run(doc) == []
