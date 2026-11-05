"""The model-device skill's Submit stage names every check preflight runs.

An assistant that follows the skill runs preflight at the end, and reads what
each check asks of it from the skill. A check preflight gains without a line
in the skill is a check the assistant meets for the first time as a FAIL. The
check names are read from `preflight.CHECKS`, not copied here, so a new check
fails this test until step 6 of the Submit stage names it.

One direction only: the skill may name more than preflight runs.
"""
import re
from pathlib import Path

import pytest

from portrayal import preflight

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude/skills/portrayal-model-device/SKILL.md"


def submit_stage():
    text = SKILL.read_text(encoding="utf-8")
    m = re.search(r"^## Submit.*?(?=^## |\Z)", text, re.S | re.M)
    assert m, "the skill has no '## Submit' heading"
    return m.group(0)


def missing_checks(checks):
    stage = submit_stage()
    return [c for c in checks if f"`{c}`" not in stage]


def check_named(checks):
    missing = missing_checks(checks)
    assert not missing, (
        f"the skill's Submit stage does not name {', '.join(missing)} "
        "in backticks: name each check preflight runs in the skill's Submit stage "
        "(step 6, Preflight)")


def test_the_submit_stage_names_every_preflight_check():
    check_named(preflight.CHECKS)


def test_a_check_preflight_gains_must_be_named(monkeypatch):
    monkeypatch.setattr(preflight, "CHECKS", preflight.CHECKS + ("a-check-nobody-named",))
    with pytest.raises(AssertionError, match="a-check-nobody-named"):
        check_named(preflight.CHECKS)
