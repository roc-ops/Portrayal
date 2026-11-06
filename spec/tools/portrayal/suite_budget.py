#!/usr/bin/env python3
"""The test budget: each tier of the suite, held to spec/test-budget.json.

    suite_budget.py <junit.xml>... --tier light|full [--budget spec/test-budget.json]
                    [--base times.json | --fetch-base OWNER/REPO]

WHY IT CAN FAIL WHEN suite_times.py CANNOT. The suite grew from 5,200 to 11,600
summed seconds in three weeks, and the report that named each step of it was
built never to fail a run, so every step was accepted. A budget is the number
the growth runs into: past it the run is red, and the way on is to make a test
cheaper, to move it to the heavy tier, or to raise the number - and raising it
is a one-way door the maintainer decides (CONTRIBUTING.md, "Merge danger").

TWO RULES, BOTH WITH THE LOAD DIVIDED OUT the way suite_times.py does it - the
median, over the files this run shares with the base run, of how much slower
each was - since the same tree measures up to twice as slow on a busy runner:

  - the tier's summed seconds may not pass its `seconds`;
  - LIGHT TIER ONLY: a test function the base run did not have may not take
    `new_function_seconds` or more, its parameters summed - AND ADD that much
    to its file. A module fixture is billed to whichever test a worker runs
    first, so a cheap new test can measure the fixture while the old test that
    used to pay it drops to nothing; the file did not grow, and neither did the
    tier. The light tier is what every pull request push runs; a slow test
    belongs in the heavy tier, where it still counts against the full budget.

THE TOTAL IS READ IN THE REFERENCE RUN'S UNITS. Each budget number was set
from one run, and `spec/test-budget-reference.json` keeps that run's seconds
file by file (`--record` writes it). The load is the median, over the files a
run shares with that reference, of how much slower each was, so the total is
read in the units the budget was written in. A moving base moves the units:
two runs of the same 19,309 tests measured 8,410 s and 9,559 s, and against
whichever merged run was newest an unchanged suite read over budget. Raising a
number and re-recording the reference go together, and both are one-way.

THE NEWEST MERGED RUN STILL DECIDES WHAT IS NEW, for the light ceiling below:
A LIGHT RUN IS MEASURED AGAINST A LIGHT RUN: the newest merged pull request's
`test-times-light`, falling back to a full run's `test-times` until one exists.
A full run bills fixtures to heavy tests the light tier does not run, so its
per-file seconds are not a light file's, and the load read off them is wrong.

NEW MEANS ABSENT FROM THE BASE, AND THE BASE CAN LAG MAIN: a slow function
merged since the base run was measured reads as new to every pull request
after it. Given `--touched` (the pull request's changed files), a new slow
function in a file the change did not touch is a warning, not a failure; only
the change that holds it is failed for it.

WITH NO BASE RUN there is no load to divide out, and an overrun cannot be told
from a busy runner. The total is still measured, the run is not failed, and a
warning says what went unmeasured - also when the total is within budget,
because the new-function ceiling was not checked. A run that cannot find a
base is rare - every merge leaves one - and a rate limit must not hold a merge.

Exit status: 0 within budget (or no base), 1 over budget or no record to read.
"""
import argparse
import json
import os
import pathlib
import sys

import statistics

from portrayal.suite_times import (MIN_SHARED, by_file, fetch_base, fold_function,
                                   load_factor, read_junit)

BUDGET = "spec/test-budget.json"
LIGHT_ARTIFACT = "test-times-light"
REMEDY = {
    "light": "Make a test cheaper, or mark it @pytest.mark.heavy so it runs before a "
             "merge and nightly instead",
    "full": "Make a test cheaper, or fold or retire one, or raise the budget - which "
            "is a one-way door",
}


def reference_load(tests, files):
    """(load, files it rests on) against a reference run's seconds per file."""
    mine = by_file(tests)
    ratios = [mine[f] / files[f] for f in mine if files.get(f, 0.0) >= 1.0]
    if len(ratios) < MIN_SHARED:
        return 1.0, len(ratios)
    return statistics.median(ratios), len(ratios)


def measure(tests, base, files=None):
    """(summed seconds with the load divided out, load, files the load rests on):
    against the reference run's `files` when there are any, else the base."""
    if files:
        load, shared = reference_load(tests, files)
    elif base is not None:
        load, shared = load_factor(tests, base)
    else:
        return sum(tests.values()), 1.0, 0
    return sum(tests.values()) / load, load, shared


def _growers(tests, base, files, load, n=3):
    mine = by_file({k: v / load for k, v in tests.items()})
    theirs = by_file({k: v for k, v in base.items() if k in tests}) if base else (files or {})
    grew = sorted(((mine[f] - theirs.get(f, 0.0), f) for f in mine), reverse=True)
    return ", ".join(f"{f} +{g:,.0f} s" for g, f in grew[:n] if g > 0) or "no file grew"


def _test_file(stem):
    return f"spec/tests/{stem}.py"


def check(tests, base, budget, tier, touched=None, reference=None):
    """(failures, warnings), each a list of sentences; both empty is within budget.
    `touched` is the change's files, or None to treat every file as touched;
    `reference` is spec/test-budget-reference.json's content, or None."""
    entry = budget[tier]
    limit = entry["seconds"]
    files = ((reference or {}).get(tier) or {}).get("files")
    total, load, _ = measure(tests, base, files)
    if base is None and not files:
        unchecked = " and the new-function ceiling was not checked" if tier == "light" else ""
        over = " - over, and not failed on" if total > limit else ""
        return [], [f"{tier} tier: no base run, so the load is not divided out{unchecked}; "
                    f"{total:,.0f} s summed against a budget of {limit:,} s{over}. A run that "
                    "finds a base will measure it"]
    failures, warnings = [], []
    if tier == "light" and base is None:
        warnings.append("light tier: no base run, so the new-function ceiling was not checked")
    elif tier == "light":
        load_new, _ = load_factor(tests, base)
        known = {fold_function(k) for k in base}
        new = {}
        for k, v in tests.items():
            f = fold_function(k)
            if f not in known:
                new[f] = new.get(f, 0.0) + v / load_new
        ceiling = entry["new_function_seconds"]
        mine_files = by_file({k: v / load_new for k, v in tests.items()})
        base_files = by_file(base)
        for (stem, name), s in sorted(new.items()):
            if s < ceiling or mine_files[stem] - base_files.get(stem, 0.0) < ceiling:
                continue
            line = (f"light tier: the new test function {stem}::{name} took {s:.1f} s (load "
                    f"divided out); a light-tier function may take less than {ceiling:g} s. "
                    "Make it cheaper, or mark it @pytest.mark.heavy - it then runs before a "
                    "merge and nightly, and counts against the full budget")
            if touched is None or _test_file(stem) in touched:
                failures.append(line)
            else:
                warnings.append(line + f". This change does not touch {_test_file(stem)}, "
                                "so the base predates it and it is not failed on here")
    if total > limit:
        failures.append(
            f"{tier} tier: {total:,.0f} s summed (load {load:.2f} divided out) against a "
            f"budget of {limit:,} s in {BUDGET}. Grew most against the base: "
            f"{_growers(tests, base, files, load)}. {REMEDY[tier]}")
    return failures, warnings


def record(tests, tier, run, path):
    """Write `tests`' seconds, file by file, as `tier`'s reference run in `path`."""
    path = pathlib.Path(path)
    doc = json.loads(path.read_text()) if path.is_file() else {}
    doc[tier] = {"run": int(run), "files": {f: round(s, 3) for f, s in sorted(by_file(tests).items())}}
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def _read(paths):
    tests = {}
    for p in paths:
        if not pathlib.Path(p).is_file():
            raise ValueError(f"{p} does not exist - the suite wrote no record of its run")
        mine = read_junit(p)
        if not mine:
            raise ValueError(f"{p} holds no test - there is nothing to measure")
        for k, v in mine.items():
            tests[k] = round(tests.get(k, 0.0) + v, 3)
    return tests


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("junit", nargs="+", help="pytest's --junitxml output, one per shard")
    ap.add_argument("--tier", required=True, choices=("light", "full"))
    ap.add_argument("--budget", default=BUDGET)
    ap.add_argument("--base", help="an earlier full run's times, as suite_times.py --out writes them")
    ap.add_argument("--fetch-base", metavar="OWNER/REPO",
                    help="the newest merged pull request's published full-run times")
    ap.add_argument("--touched", help="the change's files, one path per line; a new slow "
                    "function elsewhere warns instead of failing")
    ap.add_argument("--reference", help="spec/test-budget-reference.json: the run each "
                    "budget was set from, file by file")
    ap.add_argument("--record", action="store_true",
                    help="write these runs' seconds as the tier's reference, and check nothing")
    ap.add_argument("--run", help="with --record: the run id the reference names")
    a = ap.parse_args(argv)
    try:
        tests = _read(a.junit)
    except ValueError as e:
        print(f"::error title=test budget::{e}")
        return 1
    if a.record:
        if not (a.reference and a.run):
            ap.error("--record needs --reference and --run")
        record(tests, a.tier, a.run, a.reference)
        print(f"{a.tier} tier: recorded run {a.run}, {sum(tests.values()):,.0f} s in "
              f"{len(by_file(tests))} files, as the reference in {a.reference}")
        return 0
    budget = json.loads(pathlib.Path(a.budget).read_text())
    reference = (json.loads(pathlib.Path(a.reference).read_text())
                 if a.reference and pathlib.Path(a.reference).is_file() else None)
    files = ((reference or {}).get(a.tier) or {}).get("files")

    base, label = None, "no base run was given"
    if a.base and pathlib.Path(a.base).is_file():
        base, label = json.loads(pathlib.Path(a.base).read_text())["tests"], a.base
    elif a.fetch_base:
        token, head = os.environ.get("GITHUB_TOKEN"), os.environ.get("HEAD_SHA")
        try:
            if a.tier == "light":
                base, label = fetch_base(a.fetch_base, token, head, artifact=LIGHT_ARTIFACT)
            if base is None:
                base, label = fetch_base(a.fetch_base, token, head)
                if base is not None and a.tier == "light":
                    label += " (a full run: no merged light run has been published yet)"
        except Exception as e:  # noqa: BLE001 - any failure here means "no base"
            base, label = None, f"the base run could not be fetched ({type(e).__name__}: {e})"

    total, load, shared = measure(tests, base, files)
    if files:
        against = (f"load {load:.2f} over {shared} files of reference run "
                   f"{reference[a.tier]['run']}; new tests against base {label}")
    elif base is not None:
        against = f"load {load:.2f} over {shared} shared files, base {label}"
    else:
        against = f"no base: {label}; the load is not divided out"
    print(f"{a.tier} tier: {total:,.0f} s summed against a budget of "
          f"{budget[a.tier]['seconds']:,} s ({against})")
    touched = None
    if a.touched and pathlib.Path(a.touched).is_file():
        touched = {l.strip() for l in pathlib.Path(a.touched).read_text().splitlines() if l.strip()}
    failures, warnings = check(tests, base, budget, a.tier, touched, reference)
    for w in warnings:
        print(f"::warning title=test budget::{w}")
    for f in failures:
        print(f"::error title=test budget::{f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
