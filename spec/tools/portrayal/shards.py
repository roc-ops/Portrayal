#!/usr/bin/env python3
"""Split the suite across CI jobs, and prove afterwards that the split lost nothing.

The suite is the long pole of a CI run: about 4,100 summed seconds, eighteen
minutes on a four-core runner. Merges are serial, so every minute of it is a
minute of queue for the next pull request. Several runners each take a share.

    pytest spec/tests --shard 2/4 --shard-weights w.json --shard-record r.json
    shards.py fetch-weights OWNER/REPO --out w.json
    shards.py check r1.json r2.json r3.json r4.json

WHAT IS SPLIT IS A UNIT, NOT A TEST. A test with an `xdist_group` mark goes
with its group, whichever files the group spans - the group exists because its
tests wait on one shared run (spec/tests/onebuild.py), and split across two
jobs that run would be made twice. Every other test goes with its FILE, so a
module-scoped fixture is built in one job rather than in all of them.

BALANCED BY WHAT EACH TEST COST LAST TIME. The weights are the per-test seconds
the newest merged pull request's run published (suite_times.py, artifact
`test-times`). A test that is not in them - a new one - weighs the median. The
units are dealt longest first, each to the job with least so far.

THE SPLIT IS A PURE FUNCTION of the collected ids, the weights and the count,
and every job reads the same weights file, so the jobs agree without talking.
That is an argument, and `check` is the measurement: each job records what it
collected and what it kept, and the check refuses unless every job collected
the same tests and the kept sets cover them exactly once.

THE PYTEST HOOKS ARE PLAIN FUNCTIONS, imported by spec/tests/conftest.py. No
plugin to install, and nothing happens unless `--shard` is given - a local run,
and the nested pytest some tests start, see the whole suite.
"""
import argparse
import json
import os
import pathlib
import statistics
import sys


def junit_key(nodeid):
    """The id suite_times.read_junit writes for a test: the module's stem, then
    the class and name joined by dots - `test_x::TestC.test_y[p]`."""
    path, _, rest = nodeid.partition("::")
    stem = pathlib.PurePosixPath(path).stem
    return f"{stem}::{rest.replace('::', '.')}"


def split_id(nodeid, groups):
    """(the test's id without xdist's group suffix, the unit it travels with).

    xdist's `loadgroup` renames a grouped test to `id@group` on the worker, and
    whether that has happened when this runs depends on hook order - so the
    suffix is taken off and the id is the same either way."""
    if groups:
        suffix = "@" + "_".join(sorted(groups))
        if nodeid.endswith(suffix):
            nodeid = nodeid[:-len(suffix)]
        return nodeid, "group:" + "_".join(sorted(groups))
    return nodeid, nodeid.partition("::")[0]


def weigh(tests, weights):
    """{unit: seconds} for [(id, unit, groups)], from suite_times' per-test
    record. A grouped test is recorded under `key@group`, as junit saw it."""
    known = [v for v in weights.values() if v > 0]
    default = statistics.median(known) if known else 1.0
    out = {}
    for nodeid, unit, groups in tests:
        key = junit_key(nodeid)
        if groups:
            key += "@" + "_".join(sorted(groups))
        out[unit] = out.get(unit, 0.0) + weights.get(key, default)
    return out


def assign(units, n):
    """{unit: shard index, 1..n}. Longest first, each to the lightest shard,
    ties by name and then by the lower index - deterministic."""
    if n < 1:
        raise ValueError(f"cannot split into {n} shards")
    load = [0.0] * n
    out = {}
    for unit, w in sorted(units.items(), key=lambda kv: (-kv[1], kv[0])):
        i = min(range(n), key=lambda j: (load[j], j))
        out[unit] = i + 1
        load[i] += w
    return out


def select(tests, weights, index, n):
    """The ids of [(id, unit, groups)] that shard `index` of `n` keeps."""
    where = assign(weigh(tests, weights), n)
    return [nodeid for nodeid, unit, _ in tests if where[unit] == index]


def parse_shard(text):
    i, _, n = str(text).partition("/")
    i, n = int(i), int(n)
    if not 1 <= i <= n:
        raise ValueError(f"--shard {text}: want I/N with 1 <= I <= N")
    return i, n


def read_weights(path):
    """A missing or unreadable file is no weights: every test weighs the same.
    Every job reads the same file, so they still agree."""
    try:
        doc = json.loads(pathlib.Path(path).read_text())
        return {k: float(v) for k, v in (doc.get("tests") or {}).items()}
    except (OSError, ValueError, AttributeError):
        return {}


# --- the pytest side ----------------------------------------------------------

def pytest_addoption(parser):
    g = parser.getgroup("shard", "run one share of the suite (spec/tools/portrayal/shards.py)")
    g.addoption("--shard", default=None, metavar="I/N",
                help="keep only shard I of N")
    g.addoption("--shard-weights", default=None, metavar="FILE",
                help="per-test seconds to balance by, as suite_times.py writes them")
    g.addoption("--shard-record", default=None, metavar="FILE",
                help="write what was collected and what was kept, for `shards.py check`")


def _groups(item):
    out = set()
    for m in item.iter_markers("xdist_group"):
        name = m.args[0] if m.args else m.kwargs.get("name")
        if name:
            out.add(str(name))
    return out


def pytest_collection_modifyitems(config, items):
    spec = config.getoption("--shard")
    if not spec:
        return
    index, n = parse_shard(spec)
    weights = read_weights(config.getoption("--shard-weights") or "")
    tests = []
    for item in items:
        groups = _groups(item)
        nodeid, unit = split_id(item.nodeid, groups)
        tests.append((nodeid, unit, groups))
    keep = set(select(tests, weights, index, n))
    kept = [it for (nodeid, _, _), it in zip(tests, items) if nodeid in keep]
    dropped = [it for (nodeid, _, _), it in zip(tests, items) if nodeid not in keep]
    items[:] = kept
    if dropped:
        config.hook.pytest_deselected(items=dropped)

    record = config.getoption("--shard-record")
    # ONE WRITER. Under xdist every worker collects and runs this hook, with the
    # same answer; the first worker (or the only process) writes it down.
    if record and os.environ.get("PYTEST_XDIST_WORKER", "gw0") == "gw0":
        p = pathlib.Path(record)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps({
            "shard": index, "of": n,
            "collected": sorted(t[0] for t in tests),
            "kept": sorted(keep),
        }) + "\n")
        tmp.replace(p)


# --- after the jobs -----------------------------------------------------------

def check(records):
    """[problem] for a list of shard records; empty when they partition the suite."""
    if not records:
        return ["no shard records at all - no shard wrote one, or none was downloaded"]
    problems = []
    ns = {r["of"] for r in records}
    if len(ns) != 1:
        return [f"the shards disagree on how many there are: {sorted(ns)}"]
    (n,) = ns
    seen = sorted(r["shard"] for r in records)
    if seen != list(range(1, n + 1)):
        problems.append(f"expected shards 1..{n} once each, found {seen}")
    collected = set(records[0]["collected"])
    if len(collected) != len(records[0]["collected"]):
        problems.append("a shard collected the same test id twice")
    if not collected:
        problems.append("nothing was collected")
    for r in records[1:]:
        if set(r["collected"]) != collected:
            problems.append(f"shard {r['shard']} collected a different suite from "
                            f"shard {records[0]['shard']}")
    owner = {}
    for r in records:
        if not r["kept"]:
            problems.append(f"shard {r['shard']} kept nothing")
        for t in r["kept"]:
            if t in owner:
                problems.append(f"{t} ran in shard {owner[t]} and shard {r['shard']}")
            owner[t] = r["shard"]
        stray = set(r["kept"]) - collected
        if stray:
            problems.append(f"shard {r['shard']} kept {len(stray)} tests nobody collected")
    lost = collected - set(owner)
    if lost:
        problems.append(f"{len(lost)} collected tests ran in no shard, e.g. {sorted(lost)[:3]}")
    return problems


def fetch_weights(repo, out, token=None, skip_sha=None):
    """The newest merged run's per-test times, or an empty record when there is
    none - balance is a convenience and must never fail a run."""
    from portrayal import suite_times
    try:
        tests, label = suite_times.fetch_base(repo, token, skip_sha)
    except Exception as e:  # noqa: BLE001 - any failure means "no weights"
        tests, label = None, f"could not be fetched ({type(e).__name__}: {e})"
    pathlib.Path(out).write_text(json.dumps({"tests": tests or {}, "from": label}) + "\n")
    print(f"shard weights: {len(tests or {})} tests, from {label}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch-weights", help="write the newest merged run's test times")
    f.add_argument("repo", metavar="OWNER/REPO")
    f.add_argument("--out", required=True)
    c = sub.add_parser("check", help="refuse unless the records partition the suite exactly")
    c.add_argument("records", nargs="*", help="the --shard-record file of every shard")
    a = ap.parse_args(argv)

    if a.cmd == "fetch-weights":
        fetch_weights(a.repo, a.out, os.environ.get("GITHUB_TOKEN"), os.environ.get("HEAD_SHA"))
        return 0
    records = [json.loads(pathlib.Path(p).read_text()) for p in a.records]
    problems = check(records)
    for p in problems:
        print(f"::error::{p}")
    if problems:
        return 1
    n = records[0]["of"]
    kept = {r["shard"]: len(r["kept"]) for r in records}
    print(f"{len(records[0]['collected'])} tests collected, split {n} ways: "
          + ", ".join(f"shard {i} kept {kept[i]}" for i in sorted(kept))
          + " - every test in exactly one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
