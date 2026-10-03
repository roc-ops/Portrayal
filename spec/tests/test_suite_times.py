"""The suite reports what it cost, and what a change added to it.

The suite grew one reasonable test at a time and nothing said so. `suite_times`
reads pytest's junit record, and against an earlier run it names the new slow
test, the file that slowed and the total that grew - with the runner's load
divided out, because the same tree measures up to twice as slow on a busy
machine and a raw difference is mostly a reading of that.

Every expected figure below is a literal worked out by hand from the times in
the fixture, never recomputed the way the tool computes it.
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

from portrayal import suite_times as T

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "spec/tools/portrayal/suite_times.py"
GATES = ROOT / ".github/workflows/gates.yml"


def junit(tmp_path, cases, name="junit.xml"):
    """A junit file holding (classname, test name, seconds) cases."""
    body = "".join(f'<testcase classname="{c}" name="{n}" time="{s}"/>' for c, n, s in cases)
    f = tmp_path / name
    f.write_text(f'<testsuites><testsuite name="pytest">{body}</testsuite></testsuites>')
    return f


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                          capture_output=True, text=True)


def spread(files=24, seconds=2.0):
    """Enough one-test files for the load to be estimated."""
    return {f"test_f{i:02d}::test_it": seconds for i in range(files)}


# --- reading a run ------------------------------------------------------------

def test_a_test_is_named_by_its_file_and_its_own_name(tmp_path):
    f = junit(tmp_path, [("spec.tests.test_viewbox", "test_one[agr110]", "1.5"),
                         ("spec.tests.test_viewbox.TestRear", "test_two", "0.25")])
    assert T.read_junit(f) == {"test_viewbox::test_one[agr110]": 1.5,
                               "test_viewbox::TestRear.test_two": 0.25}


def test_the_report_gives_the_summed_seconds_and_the_slowest_file_first(tmp_path):
    f = junit(tmp_path, [("spec.tests.test_a", "test_x", "2"), ("spec.tests.test_a", "test_y", "3"),
                         ("spec.tests.test_b", "test_z", "40")])
    r = run(f)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "3 tests in 2 files took 45s of summed test time." in r.stdout
    rows = [l for l in r.stdout.splitlines() if l.startswith("| ") and "test_" in l]
    assert rows == ["| 40.0 | test_b |", "| 5.0 | test_a |"]


def test_a_run_with_nothing_to_compare_against_flags_nothing(tmp_path):
    r = run(junit(tmp_path, [("spec.tests.test_a", "test_slow", "90")]))
    assert r.returncode == 0
    assert "::warning" not in r.stdout
    assert "No earlier run to compare against" in r.stdout


def test_a_record_with_no_test_in_it_is_an_error_not_a_clean_report(tmp_path):
    """NON-VACUITY. A report over nothing reads the same as a suite that got no
    slower, so an empty record and a missing one both fail."""
    empty = run(junit(tmp_path, []))
    assert empty.returncode == 1 and "holds no test" in empty.stdout
    missing = run(tmp_path / "never-written.xml")
    assert missing.returncode == 1 and "does not exist" in missing.stdout


# --- comparing two runs -------------------------------------------------------

def test_a_busy_runner_is_not_reported_as_a_slower_suite():
    """Every file took exactly twice as long. That is the machine."""
    base = spread()
    cmp = T.compare({k: v * 2 for k, v in base.items()}, base)
    assert cmp["load"] == 2.0
    assert T.flags(cmp) == []
    assert cmp["total"] == 48.0 and cmp["base_total"] == 48.0


def test_a_new_slow_test_is_named_with_the_load_divided_out():
    base = spread()
    now = {k: v * 2 for k, v in base.items()}
    now["test_f00::test_added"] = 14.0      # 7s on the base run's machine
    now["test_f00::test_added_small"] = 1.0
    cmp = T.compare(now, base)
    assert cmp["slow_new"] == {"test_f00::test_added": 7.0}
    assert cmp["new_seconds"] == 7.5
    assert "new test test_f00::test_added takes 7.0s" in T.flags(cmp)


def test_a_file_that_slowed_more_than_the_rest_is_named():
    base = {**spread(), "test_heavy::test_a": 10.0, "test_heavy::test_b": 10.0}
    now = {**base, "test_heavy::test_a": 30.0}
    cmp = T.compare(now, base)
    assert cmp["load"] == 1.0
    assert cmp["grew"] == {"test_heavy": (20.0, 40.0)}
    assert "test_heavy went from 20.0s to 40.0s" in T.flags(cmp)


def test_a_small_drift_in_one_file_is_not_named():
    """Under the threshold on seconds (4s) and, separately, on ratio (10%)."""
    base = {**spread(), "test_small::test_a": 2.0, "test_big::test_a": 100.0}
    now = {**base, "test_small::test_a": 6.0, "test_big::test_a": 110.0}
    assert T.compare(now, base)["grew"] == {}


def test_the_total_is_named_when_the_suite_grew_by_three_per_cent():
    base = spread(files=25, seconds=4.0)                    # 100s
    grown = {**base, **{f"test_new{i}::test_it": 1.0 for i in range(3)}}   # 103s
    assert T.compare(grown, base)["total_grew"] is True
    assert any("the suite went from 100s to 103s" in f for f in T.flags(T.compare(grown, base)))
    barely = {**base, "test_new::test_it": 2.0}             # 102s
    assert T.compare(barely, base)["total_grew"] is False


def test_too_few_shared_files_and_no_load_is_claimed():
    """A median over three files is a guess, and dividing by a guess would
    hide a real regression or invent one."""
    base = spread(files=3)
    cmp = T.compare({k: v * 2 for k, v in base.items()}, base)
    assert cmp["load"] == 1.0 and cmp["shared_files"] == 3


def test_the_command_compares_against_a_base_file_and_still_exits_zero(tmp_path):
    """FLAGS, NEVER FAILS: a timing is a question for a reviewer."""
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"tests": spread()}))
    cases = [("spec.tests." + k.split("::")[0], "test_it", "2.0") for k in spread()]
    cases.append(("spec.tests.test_f00", "test_added", "9"))
    summary = tmp_path / "summary.md"
    out = tmp_path / "times.json"
    r = run(junit(tmp_path, cases), "--base", base, "--summary", summary, "--out", out)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "::warning title=test time::new test test_f00::test_added takes 9.0s" in r.stdout
    assert "- new test test_f00::test_added takes 9.0s" in summary.read_text()
    assert json.loads(out.read_text())["tests"]["test_f00::test_added"] == 9.0


# --- which run is the base ----------------------------------------------------

def art(sha, created, name="test-times", expired=False):
    return {"name": name, "created_at": created, "expired": expired,
            "workflow_run": {"head_sha": sha}}


def test_the_base_is_the_newest_merged_heads_run():
    """An open branch's run would report main's newer tests as this change's."""
    arts = [art("open", "2026-10-03T09:00:00Z"), art("old", "2026-10-01T09:00:00Z"),
            art("new", "2026-10-02T09:00:00Z")]
    chosen, number = T.choose_base(arts, {"old": 700, "new": 742})
    assert chosen["workflow_run"]["head_sha"] == "new" and number == 742


def test_an_expired_or_differently_named_artifact_is_not_a_base():
    arts = [art("a", "2026-10-02T09:00:00Z", expired=True),
            art("b", "2026-10-02T08:00:00Z", name="coverage")]
    assert T.choose_base(arts, {"a": 1, "b": 2}) == (None, None)


# --- the workflow -------------------------------------------------------------

@pytest.fixture(scope="module")
def build():
    return yaml.safe_load(GATES.read_text())["jobs"]["build"]


def step(build, name):
    return next(s for s in build["steps"] if s.get("name") == name)


def test_the_suite_writes_the_record_the_report_reads(build):
    assert '--junitxml "$RUNNER_TEMP/junit.xml"' in step(build, "tests")["run"]
    assert '"$RUNNER_TEMP/junit.xml"' in step(build, "test time")["run"]


def test_the_report_cannot_turn_a_green_run_red(build):
    """Fetching the base talks to an API, and the comparison is a convenience."""
    s = step(build, "test time")
    assert s.get("continue-on-error") is True
    assert "--fetch-base" in s["run"] and "$GITHUB_STEP_SUMMARY" in s["run"]


def test_the_times_are_published_for_the_next_run_to_compare_against(build):
    s = step(build, "publish test times")
    assert s["with"]["name"] == T.ARTIFACT
    uses = s["uses"]
    assert uses.startswith("actions/upload-artifact@") and len(uses.split("@")[1]) == 40, uses


def test_the_job_may_read_artifacts_and_pull_requests_and_write_nothing(build):
    perms = build["permissions"]
    assert perms == {"contents": "read", "actions": "read", "pull-requests": "read"}
