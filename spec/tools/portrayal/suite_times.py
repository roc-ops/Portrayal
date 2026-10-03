#!/usr/bin/env python3
"""What the suite cost, and what this change added to it.

The suite is the long pole of every run, and it grew one reasonable test at a
time. Nothing reported the growth, so nobody saw it until the job reached its
timeout. This reads pytest's own record of a run, says where the time went, and
when it is given an earlier run to compare against it names what is new.

    suite_times.py <junit.xml> --out times.json [--base base.json] [--summary FILE]

IT FLAGS AND NEVER FAILS. A slow test is a question for a reviewer - is this
worth what it costs, could a lint rule answer it - and a timing is not exact
enough to refuse a merge on. The exit status is 1 only when the record is
missing or holds no test at all, because a report over nothing reads the same as
a suite that got no slower.

SUMMED TEST SECONDS, NOT THE STEP'S WALL CLOCK. The wall clock is the suite
divided by however many workers the runner had, plus its queue. The sum of what
each test took is the suite.

TWO RUNS ARE NOT COMPARED SECOND FOR SECOND. The same tree measures up to twice
as slow on a busy runner, so a raw difference is mostly a reading of the
machine. The comparison finds the LOAD first - the median, over the test files
both runs share, of how much longer each took - and divides it out. A file that
slowed by the same factor as everything else did not change; one that slowed by
more did.

WHAT THAT CANNOT SEE, AND SAYS INSTEAD. A change that slows EVERY file - a
fixture in conftest, the YAML loader - looks exactly like a busy runner, and
dividing it out would report a suite that tripled as unchanged. So a load of
1.5 or more is itself flagged, as the one or the other: a re-run tells them
apart, and the reader is told to ask.

A REGRESSION IS REPORTED PER FILE AND A NEW TEST PER TEST. A module-scoped
fixture is charged to whichever test happens to run first in a worker, so one
test's time moves between runs while its file's does not.
"""
import argparse
import io
import json
import os
import pathlib
import statistics
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

SLOW = 5.0          # a new test at or over this many seconds is named
FILE_GREW = 5.0     # a file is named when its shared tests grew by this much ...
FILE_RATIO = 1.25   # ... and by this factor, with the load divided out
TOTAL_GREW = 0.03   # the suite is named when it grew by this fraction
MIN_SHARED = 20     # fewer shared files than this and the load is not estimated
LOAD_SUSPECT = 1.5  # a load this high is named: a busy runner, or everything slowed
ARTIFACT = "test-times"


def read_junit(path):
    """{test id: seconds} from a junit file. The id is `file::name`, where the
    file is the classname up to its `test_` module - a class, when a test has
    one, stays in the name."""
    tests = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        parts = (case.get("classname") or "").split(".")
        cut = next((i for i, p in enumerate(parts) if p.startswith("test_")), len(parts) - 1)
        name = ".".join(parts[cut + 1:] + [case.get("name") or ""])
        key = f"{parts[cut]}::{name}"
        tests[key] = round(tests.get(key, 0.0) + float(case.get("time") or 0), 3)
    return tests


def by_file(tests):
    out = {}
    for key, s in tests.items():
        f = key.split("::")[0]
        out[f] = out.get(f, 0.0) + s
    return out


def load_factor(tests, base):
    """How much slower this run's machine was than the base run's, and how many
    files the answer rests on. 1.0 when there are too few to say."""
    mine, theirs = by_file({k: v for k, v in tests.items() if k in base}), \
        by_file({k: v for k, v in base.items() if k in tests})
    ratios = [mine[f] / theirs[f] for f in mine if theirs.get(f, 0) >= 1.0]
    if len(ratios) < MIN_SHARED:
        return 1.0, len(ratios)
    return statistics.median(ratios), len(ratios)


def compare(tests, base):
    """What this run has that the base run did not, with the load divided out."""
    load, shared_files = load_factor(tests, base)
    new = {k: round(v / load, 3) for k, v in tests.items() if k not in base}
    mine = by_file({k: v / load for k, v in tests.items() if k in base})
    theirs = by_file({k: v for k, v in base.items() if k in tests})
    grew = {f: (round(theirs[f], 1), round(mine[f], 1)) for f in mine
            if mine[f] - theirs[f] >= FILE_GREW and mine[f] >= theirs[f] * FILE_RATIO}
    base_total = sum(base.values())
    total = sum(tests.values()) / load
    return {
        "load": round(load, 2), "shared_files": shared_files,
        "new": new, "new_seconds": round(sum(new.values()), 1),
        "slow_new": {k: v for k, v in new.items() if v >= SLOW},
        "grew": grew,
        "base_total": round(base_total, 1), "total": round(total, 1),
        "total_grew": base_total > 0 and (total - base_total) / base_total >= TOTAL_GREW,
    }


def flags(cmp):
    """One sentence per thing a reviewer should look at."""
    out = []
    if cmp["load"] >= LOAD_SUSPECT:
        out.append(f"every shared file took {cmp['load']:.2f}x as long as in the base run: "
                   "a busy runner, or a change that slowed everything (a shared fixture, "
                   "the loader) - re-run to tell which")
    for k, s in sorted(cmp["slow_new"].items(), key=lambda kv: -kv[1]):
        out.append(f"new test {k} takes {s:.1f}s")
    for f, (was, now) in sorted(cmp["grew"].items(), key=lambda kv: kv[1][0] - kv[1][1]):
        out.append(f"{f} went from {was:.1f}s to {now:.1f}s")
    if cmp["total_grew"]:
        pct = 100 * (cmp["total"] - cmp["base_total"]) / cmp["base_total"]
        out.append(f"the suite went from {cmp['base_total']:.0f}s to {cmp['total']:.0f}s "
                   f"of summed test time ({pct:+.1f}%)")
    return out


def report(tests, cmp=None, base_label=None):
    """The report as Markdown, for the job summary."""
    files = by_file(tests)
    total = sum(tests.values())
    lines = ["## Test time", "",
             f"{len(tests)} tests in {len(files)} files took {total:.0f}s of summed test time.", ""]
    if cmp is None:
        lines += ["No earlier run to compare against, so nothing is flagged.", ""]
    else:
        lines += [f"Compared with {base_label or 'the base run'}: this runner was "
                  f"{cmp['load']:.2f}x as slow over {cmp['shared_files']} shared files, "
                  "and that is divided out below.", ""]
        found = flags(cmp)
        if found:
            lines += ["**Flagged for the reviewer:**", ""] + [f"- {f}" for f in found] + [""]
        else:
            lines += ["Nothing flagged.", ""]
        lines += [f"{len(cmp['new'])} tests are new and cost {cmp['new_seconds']:.1f}s.", ""]
    lines += ["| Seconds | Slowest files |", "|---:|---|"]
    lines += [f"| {s:.1f} | {f} |" for f, s in sorted(files.items(), key=lambda kv: -kv[1])[:15]]
    return "\n".join(lines) + "\n"


# --- the base run -------------------------------------------------------------

def choose_base(artifacts, merged):
    """The newest unexpired artifact whose run tested the head of a MERGED pull
    request. A head that merged is a tree main contains, so every test in it is
    one this run has too; an open branch's artifact would report main's newer
    tests as this change's additions.

    `merged` is {head sha: pull request number}; returns (artifact, number)."""
    for a in sorted(artifacts, key=lambda a: a.get("created_at") or "", reverse=True):
        sha = (a.get("workflow_run") or {}).get("head_sha")
        if a.get("name") == ARTIFACT and not a.get("expired") and sha in merged:
            return a, merged[sha]
    return None, None


class _TokenStaysHome(urllib.request.HTTPRedirectHandler):
    """An artifact's download URL redirects to a signed address on a storage
    host. urllib carries every header across a redirect, and the token must not
    follow: it is not that host's to see, and a request bearing both a signature
    and a bearer token is refused - which would read here as "no base", for
    ever."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and (urllib.parse.urlsplit(newurl).netloc
                                != urllib.parse.urlsplit(req.full_url).netloc):
            for held in (new.headers, new.unredirected_hdrs):
                held.pop("Authorization", None)
        return new


def _api(url, token):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.build_opener(_TokenStaysHome).open(req, timeout=30) as r:
        return r.read()


def fetch_base(repo, token, skip_sha=None):
    """(tests, label) from the newest merged run's artifact, or (None, why)."""
    root = f"https://api.github.com/repos/{repo}"
    pulls = json.loads(_api(f"{root}/pulls?state=closed&sort=updated&direction=desc&per_page=50", token))
    merged = {p["head"]["sha"]: p["number"] for p in pulls
              if p.get("merged_at") and p["head"]["sha"] != skip_sha}
    arts = json.loads(_api(f"{root}/actions/artifacts?name={ARTIFACT}&per_page=100", token))
    art, number = choose_base(arts.get("artifacts") or [], merged)
    if art is None:
        return None, "no merged pull request has published its test times yet"
    blob = _api(art["archive_download_url"], token)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        doc = json.loads(z.read(z.namelist()[0]))
    return doc["tests"], f"#{number}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("junit", help="pytest's --junitxml output")
    ap.add_argument("--out", help="write this run's times here, for a later run to compare against")
    ap.add_argument("--base", help="an earlier run's times, as written by --out")
    ap.add_argument("--fetch-base", metavar="OWNER/REPO",
                    help="compare against the newest merged pull request's published times")
    ap.add_argument("--summary", help="append the Markdown report to this file")
    a = ap.parse_args(argv)

    if not pathlib.Path(a.junit).is_file():
        print(f"::error::{a.junit} does not exist - the suite wrote no record of its run.")
        return 1
    tests = read_junit(a.junit)
    if not tests:
        print(f"::error::{a.junit} holds no test - there is nothing to time.")
        return 1
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps({"tests": tests}, sort_keys=True) + "\n")

    base, label = None, None
    if a.base and pathlib.Path(a.base).is_file():
        base, label = json.loads(pathlib.Path(a.base).read_text())["tests"], a.base
    elif a.fetch_base:
        # BEST EFFORT. The comparison is a convenience; a rate limit or an
        # expired artifact must not fail a run whose tests all passed.
        try:
            base, label = fetch_base(a.fetch_base, os.environ.get("GITHUB_TOKEN"),
                                     os.environ.get("HEAD_SHA"))
        except Exception as e:  # noqa: BLE001 - any failure here means "no base"
            label = f"the base run could not be fetched ({type(e).__name__}: {e})"
        if base is None:
            print(f"test times: {label}")

    cmp = compare(tests, base) if base else None
    text = report(tests, cmp, label)
    print(text)
    for f in flags(cmp) if cmp else []:
        print(f"::warning title=test time::{f}")
    if a.summary:
        with open(a.summary, "a") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
