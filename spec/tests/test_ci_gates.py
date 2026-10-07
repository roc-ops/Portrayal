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


def needs(job):
    n = job.get("needs") or []
    return [n] if isinstance(n, str) else list(n)


def test_lint_is_its_own_job_and_the_build_does_not_queue_behind_it(workflow):
    """`needs: lint` made a run queue twice on a busy pool. The gate it gave is
    kept by the merge: see test_the_merge_refuses_a_failed_lint. The build
    starts at once (`dist` needs nothing), and no job waits on lint."""
    jobs = workflow["jobs"]
    assert "lint" in jobs and "build" in jobs, list(jobs)
    assert not needs(jobs["dist"]), jobs["dist"].get("needs")
    for name, job in jobs.items():
        assert "lint" not in needs(job), f"{name} queues behind lint"
    names = [s.get("name") or s.get("uses", "") for s in steps(jobs["lint"])]
    assert any("lint" == n for n in names), names
    # and it is the FAST job: no build, no suite, no apt
    body = yaml.safe_dump(jobs["lint"])
    for heavy in ("publish.sh", "pytest", "apt-get"):
        assert heavy not in body, f"the lint job should not run {heavy}"


def test_the_build_job_does_not_lint_again(workflow):
    """The second of the three lints. `NO_LINT=1` is honoured by build.sh and is
    safe here only because no head merges without the `lint` job passing."""
    build = yaml.safe_dump(workflow["jobs"]["dist"])
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
    jobs = workflow["jobs"]
    assert jobs["dist"].get("if") == "github.event_name != 'push' && !github.event.pull_request.draft"
    assert jobs["tests"].get("if") == "github.event_name != 'push' && !github.event.pull_request.draft"
    assert jobs["build"].get("if") == (
        "${{ !cancelled() && github.event_name != 'push' && !github.event.pull_request.draft }}")
    assert "if" not in jobs["lint"]
    assert set(jobs) == {"lint", "dist", "tests", "build"}, "a new job needs the push rule too"


def test_a_draft_lints_and_its_suite_waits_for_ready(workflow):
    """A DRAFT GETS LINT, NOT THE SUITE. Every push to a draft ran the full build
    and four shards for a branch nobody could merge. The guard is only safe with
    `ready_for_review` among the types: it is not a default type, and without it
    marking a draft ready would start no run at all, so the suite would wait for
    the next push. The three default types must stay listed, or listing any type
    would silently drop them."""
    on = workflow.get("on", workflow.get(True))
    types = set(on["pull_request"]["types"])
    assert {"opened", "synchronize", "reopened", "ready_for_review"} <= types, types
    jobs = workflow["jobs"]
    guarded = [n for n in jobs if "!github.event.pull_request.draft" in str(jobs[n].get("if", ""))]
    assert sorted(guarded) == ["build", "dist", "tests"], guarded
    assert "if" not in jobs["lint"], "lint is the feedback a draft keeps"


def test_a_draft_run_cannot_cancel_a_ready_run(workflow):
    """A push and "ready for review" a second apart start two runs on one head.
    If they share a concurrency group, the push's run - its payload still says
    draft - cancels the ready one and runs lint alone, and the skipped `build`
    it leaves reads as passing to branch protection (#867). Draft status in the
    group keeps the two apart, so the ready run always lands a real `build`."""
    group = workflow["concurrency"]["group"]
    assert "github.event.pull_request.draft" in group, group
    assert "github.ref" in group, "pushes to one ref must still supersede each other"
    assert workflow["concurrency"]["cancel-in-progress"] is True


def test_a_skipped_build_cannot_merge():
    """A skipped required check reads as passing to branch protection, and a
    draft's `build` is skipped. What stops that head merging is the merge script,
    which takes nothing but `success`."""
    t = (ROOT / ".github/merge-if-green.sh").read_text()
    assert '$3!="success"' in t


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
    build = yaml.safe_dump(workflow["jobs"]["tests"])
    assert "actions/setup-node" in build
    users = [p for p in (ROOT / "spec/tests").glob("test_*.py")
             if 'which("node")' in p.read_text()]
    assert len(users) >= 10, f"only {len(users)} modules shell out to node"


def test_a_fork_never_reaches_the_self_hosted_pool(workflow):
    """The runner is chosen by a repository variable, and the cross-repository
    test comes FIRST in every `runs-on`, before the variable is consulted, and
    falls back to hosted. It compares repository names rather than reading
    `head.repo.fork`, which is null for a pull request whose fork was deleted.

    THIS IS NOT THE PROTECTION, AND THE WORKFLOW SAYS SO (#656). A pull request
    runs its own copy of this file, so a fork can rewrite `runs-on`. What keeps
    a stranger off a self-hosted machine is that none is registered while the
    repository is public."""
    for name, job in workflow["jobs"].items():
        runs_on = str(job.get("runs-on", ""))
        assert runs_on.startswith(
            "${{ (github.event_name == 'pull_request' && "
            "github.event.pull_request.head.repo.full_name != github.repository && 'ubuntu-latest')"
        ), f"{name}: {runs_on}"
        assert runs_on.rstrip(" }").endswith("'ubuntu-latest'"), f"{name}: {runs_on}"


def test_the_suite_log_is_not_in_a_shared_tmp(workflow):
    """Several runners on one machine share /tmp. A fixed /tmp path lets one
    job's skip check read another job's log - green for the wrong tree."""
    body = yaml.safe_dump(workflow)
    assert "/tmp/pytest.txt" not in body
    runs = {name: "\n".join(s.get("run", "") for s in steps(job))
            for name, job in workflow["jobs"].items()}
    assert '"$RUNNER_TEMP/out/pytest.txt"' in runs["tests"]
    assert '"$RUNNER_TEMP/pytest.txt"' in runs["build"]


def test_the_suite_keeps_its_temporary_files_in_the_job(workflow):
    """pytest's default basetemp, /tmp/pytest-of-<user>, keeps old runs' trees.
    Three self-hosted runners share one user and one /tmp, and the kept trees
    filled it (ENOSPC, three PRs failed at once). Each job's temp lives under
    its own RUNNER_TEMP, which the runner deletes after the job."""
    run = next(s["run"] for s in steps(workflow["jobs"]["tests"])
               if s.get("name") == "tests")
    assert '--basetemp "$RUNNER_TEMP/pytest"' in run, run
    assert 'export TMPDIR="$RUNNER_TEMP/tmp"' in run, run
    assert run.index("TMPDIR") < run.index("python3 -m pytest"), run


def _pyproject():
    import tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_the_build_job_caches_pip_against_a_real_file(workflow):
    """The cache key has to be a file pip actually reads, or it never invalidates
    - and since #178 the dependency list lives in pyproject rather than in
    spec/requirements-ci.txt."""
    for name in ("dist", "tests"):
        body = yaml.safe_dump(workflow["jobs"][name])
        assert "cache: pip" in body, name
        assert "pyproject.toml" in body, name
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
    assert "npm test" in yaml.safe_dump(workflow["jobs"]["dist"])


# --- the split suite -----------------------------------------------------------

def test_the_required_check_is_still_called_build_and_waits_for_everything(workflow):
    """Branch protection requires a check named `build`. Splitting the suite
    must not rename it, and it must be red when any part of the build is: it
    needs `dist` and every shard, runs even when they fail, and its last step
    refuses unless both succeeded."""
    jobs = workflow["jobs"]
    build = jobs["build"]
    assert "name" not in build, "the check name is the job id, `build`"
    assert set(needs(build)) == {"dist", "tests"}
    assert "!cancelled()" in build["if"] and "always()" not in build["if"]
    last = steps(build)[-1]
    assert last.get("if") == "always()"
    assert last["env"] == {"DIST": "${{ needs.dist.result }}",
                           "TESTS": "${{ needs.tests.result }}"}
    assert '[ "$DIST" = success ] && [ "$TESTS" = success ]' in last["run"]
    assert needs(jobs["tests"]) == ["dist"]


def test_the_shards_split_by_the_matrix_and_build_checks_the_split(workflow):
    """The count lives in one place, the matrix, and reaches pytest as
    `strategy.job-total`. The split is measured after the run, and the skip
    guards read every shard's log."""
    jobs = workflow["jobs"]
    tests = jobs["tests"]
    shards = tests["strategy"]["matrix"]["shard"]
    assert shards == list(range(1, len(shards) + 1)) and len(shards) > 1, shards
    assert tests["strategy"]["fail-fast"] is False
    run = next(s["run"] for s in steps(tests) if s.get("name") == "tests")
    assert '--shard "${{ matrix.shard }}/${{ strategy.job-total }}"' in run
    assert "--shard-record" in run and "--shard-weights" in run
    build = {s.get("name"): s for s in steps(jobs["build"])}
    assert "shards.py check" in build["every test ran once"]["run"]
    guard = build["no silent skipping"]["run"]
    assert 'for log in "${logs[@]}"' in guard, "every shard must show a summary line"
    assert "check_skips.py" in guard
    for name in ("no silent skipping", "every test ran once"):
        assert build[name].get("if") == "always()", name


def test_the_shards_test_the_build_dist_made(workflow):
    """BUILD BEFORE PYTEST, across jobs now: a shard that tested without the
    build would skip four modules' worth and look green."""
    jobs = workflow["jobs"]
    bundle = next(s for s in steps(jobs["dist"]) if s.get("name") == "bundle")["run"]
    assert "library/dist" in bundle and "fetch-weights" in bundle
    names = [s.get("name") or s.get("uses", "") for s in steps(jobs["tests"])]
    unpack = names.index("unpack the build")
    assert names.index("tests") > unpack
    assert any("download-artifact" in n for n in names[:unpack])
    # poppler too: without pdftoppm the OCR tests skip
    assert "poppler" in names


def test_every_action_is_pinned_by_commit(workflow):
    """#456: a tag is a pointer its owner can move."""
    for name, job in workflow["jobs"].items():
        for s in steps(job):
            if "uses" in s:
                ref = s["uses"].split("@")[1]
                assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), (name, s["uses"])


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
