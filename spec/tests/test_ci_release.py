"""The release workflow is the one file here that can write to a registry.

roc-ops/Portrayal#526. `release.yml` builds the library and hands it to
`npm_packages.py --from-registry --publish`. What is tested is its shape, as
test_ci_gates does for the gates: the parts that go wrong quietly, or go wrong
once and cannot be taken back, because npm never gives a version number back.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
RELEASE = ROOT / ".github/workflows/release.yml"
GATES = ROOT / ".github/workflows/gates.yml"


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(RELEASE.read_text())


@pytest.fixture(scope="module")
def job(workflow):
    (only,) = workflow["jobs"].values()
    return only


def _run(job, name):
    return next(s for s in job["steps"] if s.get("name") == name)


def test_it_runs_only_when_asked_and_a_real_publish_is_asked_for_twice(workflow, job):
    """No push, tag or release event publishes. The button's default is a dry
    run, so sending anything takes ticking the box as well as pressing it."""
    on = workflow.get("on", workflow.get(True))
    assert list(on) == ["workflow_dispatch"], on
    publish = on["workflow_dispatch"]["inputs"]["publish"]
    assert publish["type"] == "boolean" and publish["default"] is False
    step = _run(job, "packages")
    assert "--from-registry --publish $DRY_RUN" in step["run"]
    assert step["env"]["DRY_RUN"] == "${{ !inputs.publish && '--dry-run' || '' }}"


def test_only_main_is_released(job):
    """workflow_dispatch offers every branch. A branch's build under a version
    number is a version number main can never use."""
    assert "github.ref == 'refs/heads/main'" in job["if"]


def test_the_token_can_mint_an_identity_and_write_nothing(workflow, job):
    """`id-token: write` is what trusted publishing exchanges for a publish.
    Nothing here pushes, tags or comments, so the repository stays read-only."""
    assert workflow["permissions"] == {"contents": "read"}
    assert job["permissions"] == {"contents": "read", "id-token": "write"}


def test_it_runs_on_a_hosted_runner_and_no_variable_can_move_it(job):
    """npm's trusted publishing refuses a self-hosted runner, and none may be
    registered on this repository again (#656)."""
    assert job["runs-on"] == "ubuntu-latest"


def test_two_releases_never_run_at_once(workflow):
    """Each reads what npm holds and then publishes against it. Two at once
    price the same change twice and the slower one collides."""
    c = workflow["concurrency"]
    assert c["cancel-in-progress"] is False, "a cancelled release is a half-sent one"
    assert "github.ref" not in str(c["group"]), "one queue, whatever the ref"


def test_node_and_npm_are_new_enough_for_trusted_publishing(job):
    """npm asks for Node 22.14 and npm 11.5.1. The Node 20 the gates use ships
    npm 10, which ignores the identity token and fails as unauthenticated."""
    node = next(s for s in job["steps"] if "actions/setup-node" in s.get("uses", ""))
    assert str(node["with"]["node-version"]).split(".")[0] == "22"
    assert node["with"]["registry-url"] == "https://registry.npmjs.org"
    body = yaml.safe_dump(job)
    m = re.search(r"npm install -g npm@(\d+)\.(\d+)\.(\d+)", body)
    assert m, "npm is pinned to an exact version"
    assert tuple(map(int, m.groups())) >= (11, 5, 1)


def test_every_action_is_pinned_to_a_commit_the_gates_already_trust(job):
    """A tag is a pointer its owner can move (#456). The same pins as gates.yml,
    so one bump moves both."""
    trusted = {s["uses"] for j in yaml.safe_load(GATES.read_text())["jobs"].values()
               for s in j["steps"] if "uses" in s}
    used = {s["uses"] for s in job["steps"] if "uses" in s}
    assert used and used <= trusted, used - trusted


def test_it_publishes_the_build_it_just_made_and_lints_it(job):
    """The gates skip the build's lint because a lint job runs beside them.
    Nothing runs beside a release."""
    names = [s.get("name") for s in job["steps"]]
    assert names.index("build") < names.index("packages")
    build = _run(job, "build")["run"]
    assert "./publish.sh --no-images" in build and "NO_LINT" not in build


def test_the_bootstrap_token_is_optional_and_only_the_publish_step_sees_it(job):
    """A package's first publish cannot use trusted publishing, so a short-lived
    token covers it. No other step - the build least of all - is handed it."""
    holders = [s.get("name") for s in job["steps"] if "NPM_TOKEN" in yaml.safe_dump(s)]
    assert holders == ["packages"], holders
    assert _run(job, "packages")["env"]["NODE_AUTH_TOKEN"] == "${{ secrets.NPM_TOKEN }}"


def test_the_token_is_an_environment_secret(job):
    """A repository secret is readable by every workflow on a branch of this
    repository. An environment secret is readable by a job that names the
    environment, after the environment's own branch rule and approval."""
    assert job["environment"] == "npm"
    t = (ROOT / "docs/maintainers.md").read_text()
    assert "--env npm" in t and "--environment npm" in t


def test_a_failed_publish_fails_the_step(job):
    """The packager's output is piped to `tee` for the run summary. Without
    pipefail the step's status is tee's, and a failed publish is green."""
    run = _run(job, "packages")["run"]
    assert run.index("set -o pipefail") < run.index("npm_packages.py")


def test_the_summary_is_written_when_the_publish_failed(job):
    """A package sent before a failure is on npm, so the next run does not call
    it a first publish. The failed run's summary is the only list of them."""
    step = _run(job, "summary")
    assert step["if"] == "always()"
    assert "GITHUB_STEP_SUMMARY" in step["run"] and "published" in step["run"]


def test_the_maintainer_notes_say_how_a_first_publish_is_done():
    t = (ROOT / "docs/maintainers.md").read_text()
    assert "release.yml" in t and "trust github" in t and "first publish" in t
