"""data-r-from: a numeric field sets a circle's radius (docs/pluggables-cables-design.md section 4).

The value is a DIAMETER - `cable-od`, a cable's outside diameter in mm - so the
circle takes half of it. Empty, absent or not a number leaves the radius the
skin was drawn with, the rule colour follows, and kit/fields.js applies the same
rule at runtime: the parity test below holds the two to one answer.
"""
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from portrayal import lint
from portrayal.render import fill_from_attrs

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/r-from.mjs"

# One list, fed to the build, the kit and L122. The last group is the parity
# gap the final review probed: '1e1' and '1_0' float() takes and the pattern
# does not; Arabic-Indic digits Python's \d took and JS's did not; a leading
# \x1c separator Python's \s took and JS's did not; a no-break space JS's \s
# took and Python's pattern now refuses alike.
CASES = [9.0, 7, "3.0", "", "thick", None, "0", "1.2.3", "inf", "-4", " 6.9 ",
         "\t6.9\n", "1e1", "1_0", "\u0661\u0660", "\u06f1\u06f0", "\x1c6.9",
         "\u00a06.9", "6.9\u2003", "."]


def circle(r="2.4"):
    root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg">'
                         f'<circle id="stub" cx="5" cy="5" r="{r}" data-r-from="cable-od"/></svg>')
    return root, next(e for e in root.iter() if e.get("id") == "stub")


def test_a_numeric_value_sets_half_the_diameter():
    root, c = circle()
    fill_from_attrs(root, {"cable-od": 9.0})
    assert float(c.get("r")) == 4.5


def test_a_string_number_counts():
    root, c = circle()
    fill_from_attrs(root, {"cable-od": "3.0"})
    assert float(c.get("r")) == 1.5


def test_absent_empty_or_junk_leaves_the_drawn_default():
    for attrs in ({}, {"cable-od": ""}, {"cable-od": "thick"}, {"cable-od": None},
                  {"cable-od": "0"}, {"cable-od": "1.2.3"}, {"cable-od": "inf"},
                  {"cable-od": "-4"}, {"cable-od": "1e1"}, {"cable-od": "1_0"},
                  {"cable-od": "\u0661\u0660"}, {"cable-od": "\x1c6.9"}):
        root, c = circle()
        fill_from_attrs(root, attrs)
        assert c.get("r") == "2.4", attrs


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), json.dumps(CASES)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_kit_agrees(out):
    """Empty restores the drawn radius, and junk restores it too."""
    assert out["seq"] == ["4.5", "2.4", "2.4"]


def test_the_kit_agrees_on_every_build_case(out):
    """Each value the build test feeds, through the kit, lands on the same radius."""
    for val, r in out["cases"]:
        root, c = circle()
        fill_from_attrs(root, {"cable-od": val})
        assert r == c.get("r"), (val, r, c.get("r"))


def test_the_kit_reaches_a_composed_childs_stub(out):
    """paintFields searches the whole part group, so a stub drawn by a composed
    part - a nested group, as the build emits it - is sized too."""
    assert out["nested"] == "3.45"


def test_unpaint_puts_the_radius_back(out):
    assert out["unpainted"] == "2.4"
    assert out["stashLeft"] is False


def l122_accepts(v):
    """Whether L122 passes `v` as a field default (range aside: the cases in
    range are the ones it would draw)."""
    data = {"name": "t", "fields": {"cable-od": {"type": "number", "default": v}}}
    with lint.collecting() as got:
        lint.lint_component_cable_od(Path("t.yaml"), data)
    return not any("not a number" in e for e in got.errors)


def test_lint_build_and_kit_accept_one_set(out):
    """L122, render and the kit agree on what is a number. The kit draws
    exactly what the build draws, and L122 reads as a number exactly what the
    build draws plus a zero (a number, which the build leaves undrawn and L122
    then refuses on range). '1e1' and '1_0' used to pass lint and draw nothing;
    Arabic-Indic digits drew in Python and not in JS."""
    assert len(out["cases"]) == len(CASES)
    for v, (_, kit_r) in zip(CASES, out["cases"]):
        root, c = circle()
        fill_from_attrs(root, {"cable-od": v})
        assert kit_r == c.get("r"), (v, kit_r, c.get("r"))
        if v is None or v == "":
            continue  # absent or empty: L122 errors on "", by design
        drawn = c.get("r") != "2.4"
        assert l122_accepts(v) == (drawn or str(v).strip() == "0"), v


def test_the_non_ascii_and_exponent_cases_are_junk_everywhere(out):
    junk = ("1e1", "1_0", "\u0661\u0660", "\x1c6.9", "\u00a06.9")
    kit = dict(zip(map(repr, CASES), (r for _, r in out["cases"])))
    for v in junk:
        root, c = circle()
        fill_from_attrs(root, {"cable-od": v})
        assert c.get("r") == "2.4", v
        assert kit[repr(v)] == "2.4", v
        assert not l122_accepts(v), v
