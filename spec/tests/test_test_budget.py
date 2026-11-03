"""The test budget: each tier's summed seconds, held to spec/test-budget.json.

The suite's cost grew one reasonable test at a time, and the report that named
the growth (suite_times.py) could never fail a run, so nothing stopped it. The
budget can: a tier over its seconds, or a new light-tier function over its
ceiling, fails the run. Raising a number is a one-way door, so the growth is a
decision somebody makes rather than a drift nobody sees.
"""
import json
import pathlib
import re

import pytest

from portrayal import suite_budget as B

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUDGET = {"light": {"seconds": 400, "new_function_seconds": 5.0, "why": "x"},
          "full": {"seconds": 400, "why": "x"}}
# Thirty files of ten seconds: enough shared files for the load to be estimated.
BASE = {f"test_a{i}::f": 10.0 for i in range(30)}


def test_within_budget_says_so_and_returns_nothing():
    assert B.check(dict(BASE), BASE, BUDGET, "light") == ([], [])


def test_a_tier_over_its_seconds_names_the_files_that_grew():
    tests = {**BASE, "test_new::g[1]": 60.0, "test_new::g[2]": 60.0, "test_a0::h": 3.0}
    failures, _ = B.check(tests, BASE, BUDGET, "full")
    assert len(failures) == 1, failures
    line = failures[0]
    assert "full" in line and "400" in line and "423" in line, line
    assert "test_new" in line, line


def test_load_is_divided_out_before_the_budget_is_read():
    """Every file twice as slow is a busy runner, not a bigger suite."""
    tests = {k: v * 2 for k, v in BASE.items()}
    assert sum(tests.values()) == 600
    assert B.check(tests, BASE, BUDGET, "full") == ([], [])


def test_a_new_light_function_at_five_seconds_is_named():
    """Two cheap parameters of one new function are one six-second cost."""
    tests = {**BASE, "test_x::f[1]": 3.0, "test_x::f[2]": 3.0}
    failures, _ = B.check(tests, BASE, {**BUDGET, "light": {**BUDGET["light"], "seconds": 1700}},
                          "light")
    assert len(failures) == 1, failures
    assert "test_x::f" in failures[0] and "6.0" in failures[0], failures[0]
    assert "@pytest.mark.heavy" in failures[0], failures[0]


def test_the_ceiling_does_not_apply_to_the_full_tier():
    tests = {**BASE, "test_x::f[1]": 3.0, "test_x::f[2]": 3.0}
    assert B.check(tests, BASE, BUDGET, "full") == ([], [])


def test_a_new_heavy_function_counts_against_the_full_budget():
    """Marking a test heavy moves its cost to the full tier; it does not remove it."""
    tests = {**BASE, "test_slow::f": 150.0}
    failures, _ = B.check(tests, BASE, BUDGET, "full")
    assert len(failures) == 1 and "test_slow" in failures[0], failures


def test_no_base_measures_raw_and_warns_without_failing():
    """With no earlier run there is no load to divide out, so an overrun cannot
    be told from a busy runner: it is said, and the run is not failed on it."""
    tests = {f"test_a{i}::f": 20.0 for i in range(30)}
    failures, warnings = B.check(tests, None, BUDGET, "full")
    assert failures == []
    assert len(warnings) == 1 and "no base" in warnings[0] and "600" in warnings[0], warnings


def _junit(path, tests):
    cases = "".join(
        f'<testcase classname="spec.tests.{k.split("::")[0]}" name="{k.split("::")[1]}" time="{v}"/>'
        for k, v in tests.items())
    path.write_text(f'<?xml version="1.0"?><testsuites><testsuite>{cases}</testsuite></testsuites>')
    return str(path)


@pytest.mark.parametrize("extra,code", [({}, 0), ({"test_new::g": 200.0}, 1)])
def test_the_command_exits_one_only_over_budget(tmp_path, capsys, extra, code):
    junit = _junit(tmp_path / "j.xml", {**BASE, **extra})
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"tests": BASE}))
    budget = tmp_path / "budget.json"
    budget.write_text(json.dumps(BUDGET))
    assert B.main([junit, "--tier", "full", "--budget", str(budget), "--base", str(base)]) == code
    assert "full tier" in capsys.readouterr().out


def test_the_command_with_no_base_says_so_and_passes(tmp_path, capsys):
    junit = _junit(tmp_path / "j.xml", {f"test_a{i}::f": 20.0 for i in range(30)})
    budget = tmp_path / "budget.json"
    budget.write_text(json.dumps(BUDGET))
    assert B.main([junit, "--tier", "full", "--budget", str(budget)]) == 0
    assert "no base" in capsys.readouterr().out


def test_the_budget_file_gives_a_reason_for_every_number():
    doc = json.loads((ROOT / "spec/test-budget.json").read_text())
    assert set(doc) == {"light", "full"}, doc
    for tier, entry in doc.items():
        assert isinstance(entry["seconds"], int) and entry["seconds"] > 0, (tier, entry)
        assert len(entry.get("why", "")) >= 40, (tier, "says why in a sentence")
    assert doc["light"]["new_function_seconds"] == 5.0


def test_raising_the_budget_is_a_one_way_door():
    """The budget only stops growth if raising it is a decision: the
    contributing guide's merge-danger list and the pull request skill's both
    name the file, so a pull request that edits it is held for the maintainer."""
    contributing = (ROOT / "CONTRIBUTING.md").read_text()
    danger = contributing[contributing.index("#### Merge danger"):]
    danger = danger[:re.search(r"\n#{1,4} ", danger[1:]).start() + 1]
    assert "spec/test-budget.json" in danger
    skill = (ROOT / ".claude/skills/portrayal-pr/SKILL.md").read_text()
    assert "spec/test-budget.json" in skill
