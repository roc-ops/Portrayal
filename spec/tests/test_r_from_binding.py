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

from portrayal.render import fill_from_attrs

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/r-from.mjs"


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
                  {"cable-od": "-4"}):
        root, c = circle()
        fill_from_attrs(root, attrs)
        assert c.get("r") == "2.4", attrs


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
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
