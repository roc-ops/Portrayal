"""One run per session of what many tests each ran for themselves.

Four tests linted the whole library and sixteen fixtures indexed every
component, each for itself. `onebuild` makes each of those once and hands the
result to whoever asks next - across xdist's workers too. What is asserted here
is the part that would go quietly wrong: a second build that still happens, a
failed build that is kept and served, a shared copy a test can write into, and
an "index" that is really `library/dist`.
"""
import json
import os
import pathlib
import subprocess
import sys
import textwrap

import pytest

import onebuild

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def shared(tmp_path, monkeypatch):
    """A shared directory of this test's own, so nothing here reads or disturbs
    what the session has really built."""
    monkeypatch.setenv("PORTRAYAL_TEST_SHARED", str(tmp_path / "shared"))
    return tmp_path / "shared"


def test_the_second_caller_is_handed_what_the_first_built(shared):
    calls = []

    def make(d):
        calls.append(d)
        (d / "answer.txt").write_text("42")

    first = onebuild.once("thing", make)
    second = onebuild.once("thing", make)
    assert first == second == shared / "thing"
    assert (first / "answer.txt").read_text() == "42"
    assert len(calls) == 1


def test_a_build_that_fails_is_not_kept(shared):
    """A half-written directory served to the next test would fail it somewhere
    unrelated, or pass it on nothing. The next caller builds again."""
    def broken(d):
        (d / "half.txt").write_text("partial")
        raise AssertionError("the indexer failed")

    with pytest.raises(AssertionError, match="the indexer failed"):
        onebuild.once("thing", broken)
    assert not (shared / "thing").exists()

    built = onebuild.once("thing", lambda d: (d / "whole.txt").write_text("ok"))
    assert sorted(p.name for p in built.iterdir()) == ["whole.txt"]


@pytest.mark.skipif(onebuild.fcntl is None, reason="no flock on this platform")
def test_processes_asking_at_once_build_it_once(shared, tmp_path):
    """xdist's workers are separate processes. Four ask together; one builds."""
    log = tmp_path / "builds.log"
    script = textwrap.dedent(f"""
        import time
        import onebuild
        def make(d):
            with open({str(log)!r}, "a") as f:
                f.write("built\\n")
            time.sleep(0.5)
            (d / "answer.txt").write_text("42")
        print((onebuild.once("thing", make) / "answer.txt").read_text())
    """)
    env = {**os.environ, "PORTRAYAL_TEST_SHARED": str(shared),
           "PYTHONPATH": os.pathsep.join([str(ROOT / "spec/tools"), str(ROOT / "spec/tests")])}
    procs = [subprocess.Popen([sys.executable, "-c", script], env=env,
                              stdout=subprocess.PIPE, text=True) for _ in range(4)]
    assert [p.communicate()[0].strip() for p in procs] == ["42"] * 4
    assert log.read_text() == "built\n"


def test_the_index_is_this_trees_and_not_library_dist():
    """THE GUARANTEE THE FIXTURES IT REPLACED EACH GAVE. A stale dist is a stale
    answer, so what a test reads is built in this session by the indexer."""
    idx = onebuild.components_index()
    assert (ROOT / "library/dist") not in idx.parents and idx != ROOT / "library/dist"
    comps = json.loads((idx / "components.json").read_text())["components"]
    on_disk = len(list((ROOT / "library/components").glob("*/*/v*/contract.yaml")))
    assert len(comps) == on_disk > 100, (len(comps), on_disk)


def test_a_copy_can_be_written_into_without_touching_the_shared_index(tmp_path):
    shared_json = onebuild.components_index() / "components.json"
    before = shared_json.read_bytes()
    mine = onebuild.components_index_into(tmp_path / "dist")
    (mine / "components.json").write_text("{}")
    (mine / "a-render.svg").write_text("<svg/>")
    assert shared_json.read_bytes() == before
    assert not (shared_json.parent / "a-render.svg").exists()


@pytest.mark.xdist_group("full-lint")
def test_the_lint_run_is_the_real_command_over_the_whole_library():
    """NON-VACUITY for the three tests that read it: a run that linted nothing
    would satisfy `"NEW since the baseline" not in stdout` just as well."""
    r = onebuild.full_lint()
    devices = len(list((ROOT / "library/devices").glob("*/*/device.yaml")))
    assert devices > 100
    assert r.stdout.rstrip().splitlines()[-1].startswith("LINT: ok ("), r.stdout[-300:]
    files = int(r.stdout.rstrip().splitlines()[-1].split("(")[1].split(" files")[0])
    assert files > devices, f"lint read {files} files; the library has {devices} devices"
