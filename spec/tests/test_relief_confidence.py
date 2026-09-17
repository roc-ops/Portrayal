"""L35 and L36 - where a relief magnitude came from, and whether `borrowed` is true.

Every part here is planted in a `tmp_path` library rather than pointed at a real
one. The obvious way to test L36 is to aim it at the origins that failed in
practice - edgecore/agr-panel-screw, which says "estimated - it stands proud but
was not measured", and common/led-dot, which carries no depth provenance at all -
but a test that asserts somebody's real debt is still outstanding breaks the day
they pay it, and paying it is the point of the rule. So the fixtures own their own
defect.

L36 is an ERROR and L35 is a WARNING, and the tests below assert that split
directly: `borrowed` ASSERTS a measurement and the assertion is checkable from
files in this repository, where `unstated` merely fails to say anything and would
fail 126 features nobody has had the chance to mark.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]

from portrayal import lint


def plant(root, ref, features, **extra):
    """Write one contract, with a skin carrying every node its relief names."""
    nsname, major = ref.rsplit("@", 1)
    d = root / "components" / nsname / f"v{major}"
    (d / "skins").mkdir(parents=True, exist_ok=True)
    data = {"format": 1, "kind": "component", "name": nsname.split("/")[-1],
            "version": f"{major}.0.0", "class": "mechanical",
            "size": {"w": 10.0, "h": 10.0},
            "relief": {"wall": "#4a4f55", "features": features}}
    data.update(extra)
    (d / "contract.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    rects = "".join(
        f'<rect id="{f["node"]}" x="0" y="0" width="2" height="2"/>' for f in features)
    (d / "skins" / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" '
        f'viewBox="0 0 10 10">{rects}</svg>')
    return d / "contract.yaml"


def found(path, root, code, stream=None):
    """Messages of one code raised by one contract, and nothing else.

    `stream` picks one side - "warnings" or "errors" - because whether a rule
    raises a warning or an error is part of what these tests check, and the two
    assertions that checked it used to read `lint.ERRORS` AFTER this returned.
    That worked only because the old helper cleared the globals and never put
    them back: the test was reading the leak that `collecting()` exists to stop.
    """
    with lint.collecting() as got:
        lint.lint_component_relief_confidence(
            path, yaml.safe_load(path.read_text()), [str(root)])
    msgs = (got.warnings if stream == "warnings" else
            got.errors if stream == "errors" else got.warnings + got.errors)
    return [m for m in msgs if f"[{code}]" in m]


def measured_origin(root, ref="acme/anvil@1", value=4.2, token="measured"):
    return plant(root, ref, [{"node": "body", "out": value, "confidence": token,
                              "source": "a tape measure lying beside it"}])


# ----------------------------------------------------------------- L35

def test_l35_counts_the_unmarked_and_does_not_name_them_all(tmp_path):
    p = plant(tmp_path, "acme/plain@1",
              [{"node": f"n{i}", "out": 1.0 + i} for i in range(6)])
    msgs = found(p, tmp_path, "L35")
    assert len(msgs) == 1, "one line per file, not one per feature"
    assert "6 of 6" in msgs[0]
    assert "..." in msgs[0], "a long list is truncated rather than printed in full"
    assert msgs == found(p, tmp_path, "L35", "warnings"), \
        "L35 is a warning - the key is optional"


def test_l35_is_silent_once_every_feature_is_marked(tmp_path):
    p = plant(tmp_path, "acme/marked@1",
              [{"node": "a", "out": 1.0, "confidence": "estimated",
                "source": "no source, and it says so"}])
    assert found(p, tmp_path, "L35") == []


def test_l35_says_nothing_about_a_part_with_no_relief(tmp_path):
    p = plant(tmp_path, "acme/bare@1", [])
    assert found(p, tmp_path, "L35") == []


# ----------------------------------------------------------------- L36

def test_l36_accepts_a_borrow_whose_origin_measured_it(tmp_path):
    measured_origin(tmp_path)
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "out": 4.2, "confidence": "borrowed",
                "source": "acme/anvil@1 - measured there"}])
    assert found(p, tmp_path, "L36") == []


def test_l36_accepts_a_photo_measured_origin(tmp_path):
    measured_origin(tmp_path, token="photo-measured")
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "out": 4.2, "confidence": "borrowed",
                "source": "acme/anvil@1 - photo-measured there"}])
    assert found(p, tmp_path, "L36") == []


def test_l36_rejects_a_borrow_from_an_origin_that_only_estimated(tmp_path):
    """The 213-feature case: the origin carries the number and never measured it."""
    measured_origin(tmp_path, token="estimated")
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "out": 4.2, "confidence": "borrowed",
                "source": "acme/anvil@1 - asserts a measurement it never took"}])
    msgs = found(p, tmp_path, "L36")
    assert len(msgs) == 1 and "estimated" in msgs[0]
    assert msgs == found(p, tmp_path, "L36", "errors"), \
        "borrowed asserts a fact, so a failed check is an error"


def test_l36_rejects_a_borrow_from_an_origin_that_says_nothing(tmp_path):
    plant(tmp_path, "acme/anvil@1", [{"node": "body", "out": 4.2}])
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "out": 4.2, "confidence": "borrowed",
                "source": "acme/anvil@1 - unstated there"}])
    assert "unstated" in found(p, tmp_path, "L36")[0]


def test_l36_refuses_a_chain_of_borrows(tmp_path):
    """A citation chain has to terminate in somebody holding an instrument."""
    measured_origin(tmp_path, ref="acme/first@1", token="measured")
    plant(tmp_path, "acme/middle@1",
          [{"node": "body", "out": 4.2, "confidence": "borrowed",
            "source": "acme/first@1 - measured there"}])
    p = plant(tmp_path, "acme/last@1",
              [{"node": "a", "out": 4.2, "confidence": "borrowed",
                "source": "acme/middle@1 - which borrowed it too"}])
    assert "borrowed" in found(p, tmp_path, "L36")[0]


def test_l36_requires_the_ref_at_the_front_of_source(tmp_path):
    measured_origin(tmp_path)
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "out": 4.2, "confidence": "borrowed",
                "source": "measured on acme/anvil@1, but the ref is not first"}])
    assert "does not begin with the origin ref" in found(p, tmp_path, "L36")[0]


def test_l36_rejects_an_origin_that_does_not_carry_the_number(tmp_path):
    measured_origin(tmp_path, value=4.2)
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "out": 9.9, "confidence": "borrowed",
                "source": "acme/anvil@1 - which has no 9.9"}])
    assert "carries no relief magnitude of 9.9" in found(p, tmp_path, "L36")[0]


def test_l36_rejects_an_origin_that_does_not_resolve(tmp_path):
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "out": 4.2, "confidence": "borrowed",
                "source": "acme/ghost@1 - no such part"}])
    assert "does not resolve" in found(p, tmp_path, "L36")[0]


def test_l36_matches_across_primitives(tmp_path):
    """A hex standoff is a `cyl` where the drawn polygon it came from was an `out`.

    The number travelled; the primitive did not have to. Matching on the magnitude
    rather than on the key is what lets casa/ups-32x4 cite casa/io-6p12 honestly.
    """
    measured_origin(tmp_path, value=9.5, token="photo-measured")
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "cyl": 9.5, "confidence": "borrowed",
                "source": "acme/anvil@1 - same number, different primitive"}])
    assert found(p, tmp_path, "L36") == []


def test_l36_ignores_lift_and_thread_when_reading_the_magnitude(tmp_path):
    """A stacked cyl carries one number plus modifiers, not two numbers."""
    measured_origin(tmp_path, value=2.2, token="measured")
    p = plant(tmp_path, "acme/user@1",
              [{"node": "a", "cyl": 2.2, "lift": 6.0, "thread": 1.0,
                "confidence": "borrowed", "source": "acme/anvil@1 - measured there"}])
    assert found(p, tmp_path, "L36") == []
