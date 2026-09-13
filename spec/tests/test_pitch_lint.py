"""L81: a composed pitch respects the standard the composed part conforms to.

The library held `lc-duplex-receptacle.pitch: 6.25` at verified confidence and
an adapter composing its bores 6.60 apart, and nothing compared them. This is
the rule that would have caught it, written after the fact so the next connector
cannot repeat it.

`lc-duplex-receptacle` is a fixed TARGET pitch (a keyed mating interface), but
five of the six `pitch` entries in standards.yaml (`xfp`, `cfp`, `cfp2`, `cxp`,
`qsfp-ganged`) are documented FLOORS - a minimum a device may sit wider than.
The first version of this rule treated every pitch as a target and 18 library
contracts got a `provenance.pitch-note` annotation to work around the false
positives that produced. `pitch-kind` on the standard now tells the rule which
check applies; these tests pin both halves of that distinction, plus the
default (absent `pitch-kind` reads as the stricter `target`).
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


def test_xfp_is_a_floor_in_the_registry():
    """Guard the guard, floor half: without this the floor tests below pass
    vacuously if standards.yaml ever loses its `pitch-kind`."""
    assert L.STANDARDS.get("xfp", {}).get("pitch-kind") == "floor"
    assert L.STANDARDS.get("xfp", {}).get("pitch") == 23.5


def xfp_pair(xs):
    """A part composing `std/xfp@1` (19.5 wide, floor pitch 23.5) at these x."""
    return {"kind": "component", "size": {"w": 70.0, "h": 20.0},
            "parts": [{"ref": "std/xfp@1", "id": i, "at": [x, 5.0]}
                      for i, x in zip(("a", "b"), xs)]}


def test_a_composed_pitch_wider_than_a_floor_is_silent():
    """Wider than a floor is compliance, not a violation - the registry's own
    words for xfp say a device may sit its ports wider than 23.5."""
    assert run(xfp_pair([0.0, 30.0])) == []           # 30.0 apart, > 23.5 floor


def test_a_composed_pitch_narrower_than_a_floor_is_caught_and_says_floor():
    hits = run(xfp_pair([0.0, 20.0]))                 # 20.0 apart, < 23.5 floor
    assert len(hits) == 1, hits
    assert "20" in hits[0] and "23.5" in hits[0]
    assert "floor" in hits[0]


def test_a_composed_pitch_off_a_target_is_caught_either_direction():
    """A target has no 'wider is fine' reading - narrower AND wider both miss
    the fixed interface pitch lc-duplex-receptacle documents."""
    assert "6.25" in run(adapter([0.95, 7.55]))[0]     # 6.60, wider - already caught above
    hits = run(adapter([1.0, 6.9]))                    # 5.90, narrower
    assert len(hits) == 1, hits
    assert "5.9" in hits[0] and "6.25" in hits[0]


def test_an_entry_with_no_pitch_kind_is_treated_as_a_target():
    """Absent `pitch-kind` reads as the stricter `target`, so a future standard
    entry that forgets the key fails loudly on a wider composed pitch rather
    than silently passing it as if it were a floor. Proven against the real
    xfp entry with its `pitch-kind` removed for the duration of this test -
    if that key were merely optional-and-ignored, this composed pitch (wider
    than xfp's floor, and so silent in the two floor tests above) would stay
    silent here too. It must not.
    """
    saved = L.STANDARDS["xfp"].pop("pitch-kind")
    try:
        hits = run(xfp_pair([0.0, 30.0]))              # 30.0 apart, > 23.5
    finally:
        L.STANDARDS["xfp"]["pitch-kind"] = saved
    assert len(hits) == 1, hits
    assert "target" in hits[0]
