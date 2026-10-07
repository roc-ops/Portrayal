"""CI splits the suite across jobs, and a split that loses a test is a silent skip.

A test that lands in no shard never runs and is never reported: no SKIPPED
line, no failure, a green check. That is the failure this workflow exists to
prevent, so the split is proven twice - here, by running real pytest sessions
over a small suite and comparing what each shard kept, and on every CI run by
`shards.py check` over the records the real shards wrote.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

from portrayal import shards as S

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "spec/tools/portrayal/shards.py"

# Three files, a parametrised test, a class, and one xdist group that spans two
# files - the shapes the real suite has.
SUITE = {
    "test_alpha.py": '''
import pytest

@pytest.mark.parametrize("n", range(12))
def test_param(n):
    pass

class TestThing:
    def test_one(self):
        pass
    def test_two(self):
        pass

@pytest.mark.xdist_group("shared")
def test_grouped_alpha():
    pass
''',
    "test_beta.py": '''
import pytest

def test_plain():
    pass

@pytest.mark.parametrize("ref", ["bracket@2", "cage@1", "x"])
def test_at_in_an_id(ref):
    pass

@pytest.mark.xdist_group("shared")
def test_grouped_beta():
    pass
''',
    "test_gamma.py": "\n".join(f"def test_g{i}():\n    pass\n" for i in range(9)),
}


@pytest.fixture(scope="module")
def suite(tmp_path_factory):
    d = tmp_path_factory.mktemp("suite")
    for name, body in SUITE.items():
        (d / name).write_text(body)
    return d


def run(suite, out, *args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "spec/tools"))
    env.pop("PYTEST_XDIST_WORKER", None)
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "portrayal.shards",
                        "-p", "no:cacheprovider", "-q", "-W", "ignore", str(suite),
                        "--rootdir", str(suite), *args],
                       capture_output=True, text=True, cwd=suite, env=env)
    return r


def shard(suite, tmp_path, i, n, *extra):
    rec = tmp_path / f"shard-{i}-of-{n}{'-x' if extra else ''}.json"
    r = run(suite, tmp_path, "--shard", f"{i}/{n}", "--shard-record", str(rec), *extra)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    return json.loads(rec.read_text())


def every_test(suite):
    r = run(suite, None, "--co")
    assert r.returncode == 0, r.stdout[-800:]
    return {l.strip() for l in r.stdout.splitlines() if "::" in l}


@pytest.fixture(scope="module")
def three(suite, tmp_path_factory):
    """The suite split three ways, once for the tests that read it."""
    out = tmp_path_factory.mktemp("three")
    return [shard(suite, out, i, 3) for i in range(1, 4)]


@pytest.mark.parametrize("n", [1, 3])
def test_the_shards_partition_the_collected_tests_exactly(suite, tmp_path, three, n):
    """No test lost, none run twice, and the union is what an unsharded run
    collects - checked against pytest's own collection, not against the
    function that made the split."""
    records = three if n == 3 else [shard(suite, tmp_path, 1, 1)]
    assert S.check(records) == []
    whole = every_test(suite)
    assert len(whole) == 12 + 2 + 1 + 1 + 3 + 1 + 9, sorted(whole)
    kept = [t for r in records for t in r["kept"]]
    assert len(kept) == len(set(kept)), "a test ran in two shards"
    assert set(kept) == whole
    assert all(r["kept"] for r in records), "a shard was given nothing"


def test_a_group_stays_in_one_shard_and_a_file_stays_together(three):
    """The group waits on one shared run; split, that run is made twice."""
    where = {t: r["shard"] for r in three for t in r["kept"]}
    assert where["test_alpha.py::test_grouped_alpha"] == where["test_beta.py::test_grouped_beta"]
    for f in ("test_gamma.py", "test_beta.py::test_at"):
        assert len({s for t, s in where.items() if t.startswith(f)}) == 1, f


def test_xdist_workers_keep_what_a_single_process_keeps(suite, tmp_path, three):
    """CI runs each shard under `-n auto --dist loadgroup`, where every worker
    collects and xdist renames a grouped test to `id@group`. The record must
    not change."""
    plain = three[1]
    under = shard(suite, tmp_path, 2, 3, "-n", "2", "--dist", "loadgroup")
    assert under["kept"] == plain["kept"]
    assert under["collected"] == plain["collected"]


def test_weights_move_tests_between_shards_but_never_drop_one(suite, tmp_path):
    w = tmp_path / "w.json"
    w.write_text(json.dumps({"tests": {"test_gamma::test_g0": 500.0,
                                       "test_alpha::test_grouped_alpha@shared": 400.0}}))
    records = [shard(suite, tmp_path, i, 3, "--shard-weights", str(w)) for i in range(1, 4)]
    assert S.check(records) == []
    where = {t: r["shard"] for r in records for t in r["kept"]}
    # the two heaviest units are dealt first, to different shards
    assert where["test_gamma.py::test_g0"] != where["test_alpha.py::test_grouped_alpha"]


def test_no_option_no_split(suite, tmp_path):
    """A local run, and the nested pytest some tests start, see everything."""
    r = run(suite, tmp_path)
    assert r.returncode == 0 and "deselected" not in r.stdout, r.stdout[-400:]


# --- the check, on records it must refuse -------------------------------------

def rec(i, n, kept, collected):
    return {"shard": i, "of": n, "kept": sorted(kept), "collected": sorted(collected)}


ALL = {"a", "b", "c", "d"}


def test_the_check_refuses_a_lost_test():
    p = S.check([rec(1, 2, {"a", "b"}, ALL), rec(2, 2, {"c"}, ALL)])
    assert any("ran in no shard" in x for x in p), p


def test_the_check_refuses_a_test_run_twice():
    p = S.check([rec(1, 2, {"a", "b"}, ALL), rec(2, 2, {"b", "c", "d"}, ALL)])
    assert any("ran in shard 1 and shard 2" in x for x in p), p


def test_the_check_refuses_a_missing_shard_and_a_different_suite():
    p = S.check([rec(1, 3, {"a", "b"}, ALL), rec(3, 3, {"c", "d"}, ALL)])
    assert any("expected shards 1..3" in x for x in p), p
    p = S.check([rec(1, 2, {"a", "b"}, ALL), rec(2, 2, {"c", "d"}, ALL | {"e"})])
    assert any("different suite" in x for x in p), p
    assert S.check([]) != []


def test_the_check_command_says_what_it_measured(tmp_path):
    files = []
    for i, kept in ((1, {"a", "b"}), (2, {"c", "d"})):
        f = tmp_path / f"r{i}.json"
        f.write_text(json.dumps(rec(i, 2, kept, ALL)))
        files.append(str(f))
    r = subprocess.run([sys.executable, str(TOOL), "check", *files],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=str(ROOT / "spec/tools")))
    assert r.returncode == 0, r.stdout
    assert "4 tests collected, split 2 ways" in r.stdout
    r = subprocess.run([sys.executable, str(TOOL), "check", files[0]],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=str(ROOT / "spec/tools")))
    assert r.returncode == 1 and "::error::" in r.stdout


def test_the_junit_key_is_the_one_suite_times_writes():
    """The weights are read from suite_times' record, so the two ids must match
    or every test weighs the median and the balance is by count."""
    assert S.junit_key("spec/tests/test_x.py::TestC::test_y[p]") == "test_x::TestC.test_y[p]"
    assert S.junit_key("spec/tests/test_x.py::test_y[bracket@2]") == "test_x::test_y[bracket@2]"
