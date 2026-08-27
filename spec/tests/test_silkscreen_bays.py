"""A bay paints over a legend, and L21 had never looked at one.

L21 gathered its opaque boxes from placements alone, so a mark printed where a
card goes was reported as fine. The C40G is the worked example: all six of its
slot numbers sit inside `fan-left` and do not appear in the compiled drawing at
all - declared, invisible, and linting clean.

A bay is the most opaque thing on a faceplate. Filled it is a card front, empty
it is a dark cavity, and either way nothing under it can be read.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402


class _NoSchema:
    """Schema validation is not what this is testing."""

    def iter_errors(self, _data):
        return iter(())


def l21_for(path):
    """L21 lives inline in lint_device, so the whole device pass runs and the
    result is filtered - the same way capability.py borrows these rules."""
    saved_w, saved_e = lint.WARNINGS[:], lint.ERRORS[:]
    lint.WARNINGS.clear()
    lint.ERRORS.clear()
    try:
        lint.lint_device(path, _NoSchema(), [str(LIB)])
        return [w for w in lint.WARNINGS if "[L21]" in w]
    finally:
        lint.WARNINGS[:] = saved_w
        lint.ERRORS[:] = saved_e


def device(tmp_path, mark_x):
    d = {
        "format": 1, "kind": "device", "name": "t", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "T", "model": "T",
        "chassis": {"width": 100, "height": 50, "depth": 100},
        "views": {"front": {
            "size": {"w": 100, "h": 50},
            "silkscreen": [{"at": [mark_x, 25], "text": "0", "font-size": 11}],
            "components": {"bays": [
                {"id": "slot-0", "at": [10, 10], "size": {"w": 40, "h": 30},
                 "accepts": ["casa/blank-faceplate@1"]}]},
        }},
    }
    p = tmp_path / "device.yaml"
    p.write_text(yaml.safe_dump(d))
    return p


def test_a_mark_under_a_bay_is_reported(tmp_path):
    """Synthetic, so it keeps testing the rule after the C40G is fixed."""
    ws = l21_for(device(tmp_path, 20))
    assert any("slot-0" in w and "paints over it" in w for w in ws), ws


def test_a_mark_clear_of_the_bay_is_not(tmp_path):
    assert not l21_for(device(tmp_path, 70))


def test_the_c40g_slot_numbers_are_the_live_case():
    """Asserts the RULE sees them, not that the device stays broken: every L21
    warning on this device must be a burial report, whatever the count."""
    man = LIB / "devices/casa/c40g/device.yaml"
    for w in l21_for(man):
        assert "paints over it" in w
