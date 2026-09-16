"""The workflow is a gate too, and nothing checked it.

roc-ops/Portrayal#183. `gates.yml` was one ~20-minute job: a README typo triggered apt, pip,
89 renders, 993 exports and the whole suite. It linted the library THREE times
per run - its own step, again inside `build.sh`, and a third time in
`test_lint_green`, which shells out and is the critical path inside the suite at
around 76 seconds. It installed no node although fourteen test modules shell out
to it, relying on the runner image happening to ship it. And it guarded skips
with a global integer.

WHAT IS TESTED HERE IS THE SHAPE OF THE WORKFLOW, not that CI passes - that is
what CI is for. The parts below are the ones that go quietly wrong: a job that
stops depending on lint, a `node` install that gets dropped, an allow-list that
drifts from what the suite actually skips.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
GATES = ROOT / ".github/workflows/gates.yml"
ALLOW = ROOT / "spec/allowed-skips.txt"
CHECK = ROOT / "spec/tools/portrayal/check_skips.py"


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(GATES.read_text())


def steps(job):
    return job.get("steps") or []


def test_lint_is_its_own_job_and_the_build_waits_on_it(workflow):
    jobs = workflow["jobs"]
    assert "lint" in jobs and "build" in jobs, list(jobs)
    assert jobs["build"].get("needs") == "lint", jobs["build"].get("needs")
    names = [s.get("name") or s.get("uses", "") for s in steps(jobs["lint"])]
    assert any("lint" == n for n in names), names
    # and it is the FAST job: no build, no suite, no apt
    body = yaml.safe_dump(jobs["lint"])
    for heavy in ("publish.sh", "pytest", "apt-get"):
        assert heavy not in body, f"the lint job should not run {heavy}"


def test_the_build_job_does_not_lint_again(workflow):
    """The second of the three lints. `NO_LINT=1` is honoured by build.sh and is
    safe here only because the `lint` job gates this one."""
    build = yaml.safe_dump(workflow["jobs"]["build"])
    assert "NO_LINT=1 ./publish.sh" in build, build[:400]


def test_build_sh_still_lints_by_default():
    """NON-VACUITY, and the thing that matters locally: skipping the check is how
    the partial dist that looked like a successful build came back."""
    t = (ROOT / "build.sh").read_text()
    assert 'if [ "${NO_LINT:-0}" != 1 ]; then' in t
    assert "lint.py" in t


def test_the_third_lint_is_skipped_only_when_ci_says_so():
    t = (ROOT / "spec/tests/test_skeleton.py").read_text()
    assert 'PORTRAYAL_LINT_ALREADY_RAN' in t
    assert "def test_lint_green" in t


def test_node_is_installed_rather_than_inherited(workflow):
    """Fourteen test modules carry `skipif(shutil.which("node") is None)`. Before
    this the suite depended on the runner image, and the day it changed those
    files would have gone quiet, not red."""
    build = yaml.safe_dump(workflow["jobs"]["build"])
    assert "actions/setup-node" in build
    users = [p for p in (ROOT / "spec/tests").glob("test_*.py")
             if 'which("node")' in p.read_text()]
    assert len(users) >= 10, f"only {len(users)} modules shell out to node"


def test_the_build_job_caches_pip_against_a_real_file(workflow):
    body = yaml.safe_dump(workflow["jobs"]["build"])
    assert "cache: pip" in body
    assert "spec/requirements-ci.txt" in body
    assert (ROOT / "spec/requirements-ci.txt").exists()


def test_the_lint_job_installs_only_what_lint_imports(workflow):
    """The suite's list pulls numpy and pillow. On a cold cache that is most of
    the "fast" gone, for a job that reads YAML and checks it against a schema."""
    body = yaml.safe_dump(workflow["jobs"]["lint"])
    assert "pip install pyyaml jsonschema" in body, body[:400]
    for heavy in ("numpy", "pillow", "requirements-ci"):
        assert heavy not in body, f"the lint job should not install {heavy}"


def test_the_requirements_cover_what_the_suite_imports_at_collection():
    """A module-scope import in a collected test file is a COLLECTION ERROR - it
    takes the whole suite down rather than skipping one file, which is how the
    second run of this workflow died on numpy."""
    req = (ROOT / "spec/requirements-ci.txt").read_text()
    for pkg in ("pytest", "pytest-xdist", "pyyaml", "jsonschema", "pillow", "numpy"):
        assert re.search(rf"^{re.escape(pkg)}$", req, re.M), pkg


def test_the_kit_has_a_test_script_covering_every_module():
    pkg = json.loads((ROOT / "kit/package.json").read_text())
    script = (pkg.get("scripts") or {}).get("test")
    assert script, "kit/package.json has no test script"
    for mod in sorted(p.name for p in (ROOT / "kit").glob("*.js")):
        assert mod in script, f"{mod} is not checked by `npm test`"


def test_the_workflow_runs_the_kit(workflow):
    assert "npm test" in yaml.safe_dump(workflow["jobs"]["build"])


# --- the skip allow-list ------------------------------------------------------

def run_check(tmp_path, report):
    f = tmp_path / "pytest.txt"
    f.write_text(report)
    return subprocess.run([sys.executable, str(CHECK), str(f), str(ALLOW)],
                          capture_output=True, text=True)


def test_a_listed_reason_passes(tmp_path):
    reason = [l for l in ALLOW.read_text().splitlines()
              if l.strip() and not l.startswith("#")][0]
    r = run_check(tmp_path, f"SKIPPED [1] spec/tests/t.py:1: {reason}\n1 passed, 1 skipped\n")
    assert r.returncode == 0, r.stdout


def test_a_tool_going_missing_is_caught(tmp_path):
    """THE FAILURE THE COUNT COULD NOT SEE. `node` vanishing skips fourteen
    files, and a budget of five catches that only because fourteen is bigger
    than five - a budget of twenty would not, and nobody would notice."""
    r = run_check(tmp_path, "SKIPPED [14] spec/tests/t.py:24: node not installed\n"
                            "1800 passed, 14 skipped\n")
    assert r.returncode == 1
    assert "node not installed" in r.stdout
    assert "does not list" in r.stdout


def test_the_allow_list_matches_what_the_suite_skips_today():
    """A list that has drifted from the suite is the same silence one level up:
    it passes because nothing matches it rather than because nothing is wrong."""
    r = subprocess.run([sys.executable, "-m", "pytest", str(ROOT / "spec/tests"),
                        "-q", "-rs", "-n", "auto", "--co", "-q"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-500:]
    allowed = [l for l in ALLOW.read_text().splitlines()
               if l.strip() and not l.startswith("#")]
    assert allowed, "the allow-list is empty"
    assert len(allowed) <= 6, f"{len(allowed)} allowed skip reasons - this list is growing"
