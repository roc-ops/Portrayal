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


def test_lint_is_its_own_job_and_the_build_does_not_queue_behind_it(workflow):
    """`needs: lint` made a run queue twice on a busy pool. The gate it gave is
    kept by the merge: see test_the_merge_refuses_a_failed_lint."""
    jobs = workflow["jobs"]
    assert "lint" in jobs and "build" in jobs, list(jobs)
    assert "needs" not in jobs["build"], jobs["build"].get("needs")
    names = [s.get("name") or s.get("uses", "") for s in steps(jobs["lint"])]
    assert any("lint" == n for n in names), names
    # and it is the FAST job: no build, no suite, no apt
    body = yaml.safe_dump(jobs["lint"])
    for heavy in ("publish.sh", "pytest", "apt-get"):
        assert heavy not in body, f"the lint job should not run {heavy}"


def test_the_build_job_does_not_lint_again(workflow):
    """The second of the three lints. `NO_LINT=1` is honoured by build.sh and is
    safe here only because no head merges without the `lint` job passing."""
    build = yaml.safe_dump(workflow["jobs"]["build"])
    assert "NO_LINT=1 ./publish.sh" in build, build[:400]


def test_the_merge_refuses_a_failed_lint():
    """THE GATE `needs: lint` USED TO BE. With the jobs side by side, the only
    thing standing between a manifest that does not lint and main is that
    merge-if-green reads every check-run on the head and refuses on any that did
    not succeed - and on any still running."""
    t = (ROOT / ".github/merge-if-green.sh").read_text()
    assert "check-runs" in t
    assert '$3!="success"' in t, "a failed check must refuse the merge"
    assert '$2!="completed"' in t, "a running check must refuse the merge"


def test_a_push_to_main_lints_but_does_not_rebuild(workflow):
    """merge-if-green merges only a green, up-to-date head, so main's tree after
    the merge is the tree that was tested. The build on the push repeated it and
    held a self-hosted runner through every merge burst. `workflow_dispatch`
    keeps a full run on main one click away."""
    on = workflow.get("on", workflow.get(True))
    assert "workflow_dispatch" in on, on
    assert workflow["jobs"]["build"].get("if") == "github.event_name != 'push'"
    assert "if" not in workflow["jobs"]["lint"]


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


def test_a_fork_never_reaches_the_self_hosted_pool(workflow):
    """The runner is chosen by a repository variable so that going public is a
    settings change - and a settings change is the kind that gets forgotten. A
    self-hosted machine runs whatever a pull request's tree says and is not
    thrown away afterwards, so the fork test has to come FIRST in every
    `runs-on`, before the variable is consulted, and fall back to hosted."""
    for name, job in workflow["jobs"].items():
        runs_on = str(job.get("runs-on", ""))
        assert runs_on.startswith(
            "${{ (github.event.pull_request.head.repo.fork && 'ubuntu-latest')"
        ), f"{name}: {runs_on}"
        assert runs_on.rstrip(" }").endswith("'ubuntu-latest'"), f"{name}: {runs_on}"


def test_the_suite_log_is_not_in_a_shared_tmp(workflow):
    """Several runners on one machine share /tmp. A fixed /tmp path lets one
    job's skip check read another job's log - green for the wrong tree."""
    build = yaml.safe_dump(workflow["jobs"]["build"])
    assert "/tmp/pytest.txt" not in build
    assert "$RUNNER_TEMP/pytest.txt" in build


def _pyproject():
    import tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_the_build_job_caches_pip_against_a_real_file(workflow):
    """The cache key has to be a file pip actually reads, or it never invalidates
    - and since #178 the dependency list lives in pyproject rather than in
    spec/requirements-ci.txt."""
    body = yaml.safe_dump(workflow["jobs"]["build"])
    assert "cache: pip" in body
    assert "pyproject.toml" in body
    assert (ROOT / "pyproject.toml").exists()


def test_the_lint_job_installs_only_what_lint_imports(workflow):
    """The suite's extra pulls numpy and pillow. On a cold cache that is most of
    the "fast" gone, for a job that reads YAML and checks it against a schema.

    `pip install -e .` keeps that true only while pyproject's `dependencies`
    stay the two the tools import, so both halves are asserted - the step and
    the list it resolves to."""
    body = yaml.safe_dump(workflow["jobs"]["lint"])
    assert "pip install -e ." in body, body[:400]
    for heavy in ("numpy", "pillow", "[test]"):
        assert heavy not in body, f"the lint job should not install {heavy}"
    core = {d.split(">")[0].split("=")[0].strip()
            for d in _pyproject()["project"]["dependencies"]}
    assert core == {"pyyaml", "jsonschema"}, (
        f"the lint job installs pyproject's core dependencies; they are now {core}")


def test_the_test_extra_covers_what_the_suite_imports_at_collection():
    """A module-scope import in a collected test file is a COLLECTION ERROR - it
    takes the whole suite down rather than skipping one file, which is how the
    second run of this workflow died on numpy."""
    extra = _pyproject()["project"]["optional-dependencies"]
    names = {d.split(">")[0].split("=")[0].strip() for d in extra["test"]}
    assert {"pytest", "pytest-xdist", "pillow", "numpy"} <= names, names
    # pyyaml and jsonschema arrive as core dependencies, not as test extras
    core = {d.split(">")[0].split("=")[0].strip()
            for d in _pyproject()["project"]["dependencies"]}
    assert {"pyyaml", "jsonschema"} <= names | core


def test_the_tools_are_a_package_and_nothing_inserts_a_path():
    """#178. Fifty modules imported each other by bare name and 94 files put this
    directory onto `sys.path` in fourteen spellings - a hack a test could get
    subtly wrong, and that no editor or import linter could follow.

    Asserted over the tree rather than over a list, because the next file to do
    it will not be on any list.
    """
    import ast

    def inserts_a_path(src):
        """A real CALL, parsed - not the string in a comment. Grepping for the
        text flagged this file's own docstring and a note left where the hack
        used to be, which is a sweep measuring the searcher rather than the tree.
        """
        for node in ast.walk(ast.parse(src)):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "insert"
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "path"
                    and getattr(node.func.value.value, "id", None) == "sys"):
                return True
        return False

    offenders = [str(f.relative_to(ROOT)) for f in sorted((ROOT / "spec").rglob("*.py"))
                 if inserts_a_path(f.read_text())]
    assert not offenders, offenders
    hyphened = [str(f.relative_to(ROOT)) for f in (ROOT / "spec/tools").rglob("*-*.py")]
    assert not hyphened, f"a hyphen is not an identifier: {hyphened}"

    setup = _pyproject()["tool"]["setuptools"]
    # THE COMPILER AND THE INTAKE TOOLS, which is what #178 was about. The exact
    # set grew to five in #179 and is asserted there, by test_tools_layout.py -
    # two tests owning one list is how a list goes stale.
    assert {"portrayal", "portrayal_intake"} <= set(setup["packages"])
    for pkg, where in setup["package-dir"].items():
        assert (ROOT / where / "__init__.py").exists(), f"{pkg} has no __init__.py"


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


def test_the_intake_extra_and_its_requirements_file_agree():
    """Two lists of the same dependencies drift. The file carries the ARGUMENT -
    why docling, why opencv, why the GPU is optional - and pyproject carries the
    install; neither is redundant, and nothing was holding them together."""
    import tomllib
    req = (ROOT / "spec/tools/intake/requirements.txt").read_text()
    named = {l.split(">")[0].split("=")[0].strip().lower()
             for l in req.splitlines() if l.strip() and not l.startswith("#")}
    extra = tomllib.loads((ROOT / "pyproject.toml").read_text())
    intake = {d.split(">")[0].split("=")[0].strip().lower()
              for d in extra["project"]["optional-dependencies"]["intake"]}
    assert named == intake, f"file-only: {named - intake}, extra-only: {intake - named}"
