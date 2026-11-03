#!/usr/bin/env python3
"""The merge train: test a set of ready pull requests together, once, before any
of them is merged.

    python3 .github/merge-train.py [--dry-run] PR [PR ...]

Every merge to main is a change to the library people import, and a pull
request's own green run tested it alone. Two green pull requests can still
break each other (#100 and #101 did), and requiring each branch to be up to
date makes every merge put the rest behind. So `main` no longer requires it.
Instead, before the owner merges a set of ready pull requests the coordinator
runs this: it checks each pull request is ready, builds `train/<date>-<n>` from
origin/main with each head merged in, in the order given, pushes that branch,
runs the full gates on it, waits, and prints the `gh pr merge` lines to run in
that order with nothing else merged between.

IT NEVER MERGES, AND IT NEVER TOUCHES main. The only ref it pushes is the train
branch (the push is refused in code for any other name), and `gh pr merge` is
printed, not run. The train is made with `git merge-tree`, in the object
database, so the caller's checkout, index and branch are not touched.

READY means, for every pull request: open, not a draft, aimed at the base; the
latest `REVIEW:` comment is `REVIEW: approve` and is newer than the head
commit; if the template's `**Door:**` line is not two-way (or is missing), an
`OWNER DECISION: approve` comment is the latest owner-decision comment; and the
`gates` workflow succeeded on the head with every check run finished and
passing, `lint` and `build` among them as successes (a draft's `build` is
skipped, and a skip is not a pass). A pull request push runs only the light
tier, whose verdict is `light suite`; `build` comes from a full run, which
the `full-gates` label starts on the pull request (docs/merging.md). Every problem
with every pull request is listed before it stops.

THE FULL RUN is `gates.yml`'s `workflow_dispatch`. On a dispatch `dist`,
`tests` and `build` all run (their `if:` only excludes a push and a draft), so
it is the whole suite on any branch it is pointed at; a pushed train branch
starts neither of the other triggers, which is why the run is asked for.
`--dry-run` does every read and the merges, in memory, and then stops: nothing
is created, pushed or started.

Exit status: 0 the train is green; 1 a pull request is not ready; 2 a conflict;
3 the run failed or timed out; 4 the answer is stale (main or a head moved
while it ran); 64 usage.

Environment: TRAIN_WORKFLOW (gates.yml), TRAIN_POLL_SECS (30),
TRAIN_TIMEOUT_SECS (3600; the suite takes about twenty minutes),
TRAIN_DATE (today, YYYY-MM-DD).
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

WORKFLOW_FILE = os.environ.get("TRAIN_WORKFLOW", "gates.yml")
# The workflow's `name:`, which is what a check run's workflow is called.
WORKFLOW_NAME = "gates"
# Check runs that must be on the head and must have SUCCEEDED (a skip is not a
# pass for these), by name prefix. Whatever else reported has to be finished and
# not failed, but nothing else is required to exist. `build` is the one branch
# protection names; `lint` is the other that is always run.
REQUIRED_CHECKS = ("lint", "build")
MERGE_FLAGS = "--merge"
OK_CONCLUSIONS = {"success", "neutral", "skipped"}


def die(code, msg):
    print(msg)
    sys.exit(code)


def run(cmd, check=True, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if check and r.returncode:
        die(1, f"{' '.join(cmd[:3])} failed ({r.returncode}): {r.stderr.strip() or r.stdout.strip()}")
    return r


def git(*args, check=True):
    return run(["git", *args], check=check)


def gh_json(*args):
    return json.loads(run(["gh", *args]).stdout or "null")


# ── readiness ────────────────────────────────────────────────────────────────
# Workers start every comment with their task id, `[P-0012] REVIEW: approve`; the
# id is optional. An owner decision is the coordinator's and has no id, so
# DECISION takes none.
VERDICT = re.compile(r"\A\s*(?:\[[A-Za-z0-9-]+\]\s+)?REVIEW:\s*(approve|changes)\b", re.I)
DECISION = re.compile(r"\A\s*OWNER DECISION:\s*(\w+)", re.I)
DOOR = re.compile(r"\*\*Door:\*\*\s*(.*)")


# Only these may give a verdict or a decision: anyone can comment on a public
# repository, and a stranger's `OWNER DECISION: approve` is not one.
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}


def latest(comments, pattern):
    """(match, comment) for the newest trusted comment whose first line matches."""
    found = None
    for c in sorted(comments, key=lambda c: c.get("createdAt", "")):
        if c.get("authorAssociation") not in TRUSTED:
            continue
        m = pattern.match(c.get("body") or "")
        if m:
            found = (m, c)
    return found


def problems_with(n, base, repo):
    """Everything wrong with PR n, as a list of sentences; empty when ready."""
    p = gh_json("pr", "view", str(n), "--json",
                "state,isDraft,baseRefName,headRefOid,body,comments,commits")
    bad = []
    if p["state"] != "OPEN":
        bad.append(f"is {p['state']}, not OPEN")
    if p.get("isDraft"):
        bad.append("is a draft")
    if p["baseRefName"] != base:
        bad.append(f"is aimed at {p['baseRefName']}, not {base}")
    sha = p["headRefOid"]

    # The head commit by its id, not the last in the list: gh returns at most 100
    # commits, and after a force-push the head can be older than the others. If it
    # is not in the list, the newest date there is.
    commits = p.get("commits") or [{}]
    head_date = next((c.get("committedDate", "") for c in commits if c.get("oid") == sha),
                     max(c.get("committedDate", "") for c in commits))
    review = latest(p.get("comments") or [], VERDICT)
    if not review:
        bad.append("has no `REVIEW: approve` comment")
    elif review[0].group(1).lower() != "approve":
        bad.append("latest review verdict is `REVIEW: changes`")
    elif review[1].get("createdAt", "") < head_date:
        bad.append(f"`REVIEW: approve` ({review[1].get('createdAt')}) is from before the head "
                   f"commit ({head_date}); it needs a fresh review")

    door = DOOR.search(p.get("body") or "")
    two_way = bool(door) and door.group(1).strip().lower().startswith("two-way")
    if not two_way:
        why = "no `**Door:**` line, so treated as one-way" if not door else "is a one-way door"
        decision = latest(p.get("comments") or [], DECISION)
        if not decision or decision[0].group(1).lower() != "approve":
            bad.append(f"{why}, and has no `OWNER DECISION: approve` comment")

    runs = gh_json("api", f"repos/{repo}/actions/runs?head_sha={sha}")
    if not any(r.get("name") == WORKFLOW_NAME and r.get("conclusion") == "success"
               for r in (runs or {}).get("workflow_runs", [])):
        bad.append(f"has no successful '{WORKFLOW_NAME}' workflow run on {sha[:9]}")
    checks = (gh_json("api", f"repos/{repo}/commits/{sha}/check-runs?per_page=100") or {}).get("check_runs", [])
    if not checks:
        bad.append(f"has no checks reported on {sha[:9]}")
    for c in checks:
        if c.get("status") != "completed":
            bad.append(f"check '{c['name']}' is not finished ({c.get('status')})")
        elif c.get("conclusion") not in OK_CONCLUSIONS:
            bad.append(f"check '{c['name']}' {c.get('conclusion')}")
    for prefix in REQUIRED_CHECKS:
        if checks and not any(c["name"].startswith(prefix) and c.get("conclusion") == "success"
                              for c in checks):
            bad.append(f"has no passing '{prefix}' check")
    return sha, bad


# ── the train ────────────────────────────────────────────────────────────────
def next_branch(date):
    prefix = f"train/{date}-"
    names = [l.split("refs/heads/", 1)[1] for l in
             git("ls-remote", "--heads", "origin", f"refs/heads/{prefix}*").stdout.splitlines()]
    names += git("for-each-ref", "--format=%(refname:short)", f"refs/heads/{prefix}*").stdout.split()
    taken = [int(m.group(1)) for n in names if (m := re.fullmatch(re.escape(prefix) + r"(\d+)", n))]
    return f"{prefix}{max(taken, default=0) + 1}"


def build_train(base, prs, heads):
    """Merge each head onto the base in order, in memory. Returns the tip sha,
    or exits 2 naming the pull request and the files that conflict."""
    if git("config", "user.name", check=False).stdout.strip() == "":
        os.environ.setdefault("GIT_AUTHOR_NAME", "merge-train")
        os.environ.setdefault("GIT_COMMITTER_NAME", "merge-train")
        os.environ.setdefault("GIT_AUTHOR_EMAIL", "merge-train@localhost")
        os.environ.setdefault("GIT_COMMITTER_EMAIL", "merge-train@localhost")
    tip, ahead = base, []
    for n in prs:
        r = git("merge-tree", "--write-tree", "--name-only", tip, heads[n], check=False)
        if r.returncode == 1:
            lines = r.stdout.splitlines()
            files = []
            for l in lines[1:]:
                if not l.strip():
                    break
                files.append(l)
            with_ = "main" + "".join(f" + #{a}" for a in ahead)
            die(2, f"#{n} conflicts with {with_} in: {', '.join(files) or '(see git merge-tree)'}\n"
                   f"Nothing was pushed. Fix #{n} (merge origin/main into its branch, or change the order).")
        if r.returncode:
            die(1, f"git merge-tree failed: {r.stderr.strip()}")
        tree = r.stdout.split()[0]
        tip = git("commit-tree", tree, "-p", tip, "-p", heads[n],
                  "-m", f"Merge #{n} ({heads[n][:9]}) into the train").stdout.strip()
        ahead.append(n)
    return tip


def push_train(branch, tip):
    if not re.fullmatch(r"train/[\w.-]+", branch):
        die(1, f"refusing to push {branch}: only train/* branches are ever pushed")
    git("update-ref", f"refs/heads/{branch}", tip)
    git("push", "-q", "origin", f"refs/heads/{branch}:refs/heads/{branch}")


def wait_for_run(branch, tip, poll, timeout):
    """Find the dispatched run on the tip and wait for it. Returns (id, final view)."""
    deadline = time.monotonic() + timeout
    run_id = None
    while run_id is None:
        runs = gh_json("run", "list", "--workflow", WORKFLOW_FILE, "--branch", branch,
                       "--event", "workflow_dispatch", "--json",
                       "databaseId,headSha,event", "--limit", "10")
        run_id = next((r["databaseId"] for r in runs or [] if r["headSha"] == tip), None)
        if run_id is None:
            if time.monotonic() >= deadline:
                die(3, f"timed out waiting for the run on {branch} to appear")
            time.sleep(poll)
    while True:
        v = gh_json("run", "view", str(run_id), "--json", "status,conclusion,url,jobs")
        if v["status"] == "completed":
            return run_id, v
        if time.monotonic() >= deadline:
            die(3, f"timed out waiting for run {run_id} ({v.get('url', '')}); it is still {v['status']}")
        time.sleep(poll)


def main():
    ap = argparse.ArgumentParser(description="Test ready pull requests together, once, before they are merged.")
    ap.add_argument("prs", nargs="*", type=int, help="pull request numbers, in merge order")
    ap.add_argument("--dry-run", action="store_true",
                    help="check and merge in memory; create, push and start nothing")
    ap.add_argument("--base", default="main")
    a = ap.parse_args()
    if not a.prs:
        ap.print_usage()
        sys.exit(64)
    if len(set(a.prs)) != len(a.prs):
        die(64, "a pull request is listed twice")
    poll = float(os.environ.get("TRAIN_POLL_SECS", "30"))
    timeout = float(os.environ.get("TRAIN_TIMEOUT_SECS", "3600"))
    date = os.environ.get("TRAIN_DATE") or datetime.date.today().isoformat()

    repo = gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    base = a.base

    shas, report = {}, []
    for n in a.prs:
        sha, bad = problems_with(n, base, repo)
        shas[n] = sha
        report += [f"  #{n} {b}" for b in bad]
    if report:
        die(1, "Not ready, nothing was built:\n" + "\n".join(report))

    git("fetch", "-q", "origin", f"+refs/heads/{base}:refs/remotes/origin/{base}")
    base_sha = git("rev-parse", f"refs/remotes/origin/{base}").stdout.strip()
    heads = {}
    for n in a.prs:
        git("fetch", "-q", "origin", f"refs/pull/{n}/head")
        heads[n] = git("rev-parse", "FETCH_HEAD").stdout.strip()
        if heads[n] != shas[n]:
            die(1, f"#{n} moved while it was being checked ({shas[n][:9]} -> {heads[n][:9]}); run again")

    tip = build_train(base_sha, a.prs, heads)
    branch = next_branch(date)
    order = " then ".join(f"#{n}" for n in a.prs)

    def merge_lines():
        return "\n".join(f"  gh pr merge {n} --repo {repo} {MERGE_FLAGS} --match-head-commit {heads[n]}"
                         for n in a.prs)

    if a.dry_run:
        print(f"DRY RUN - nothing created, pushed or started.\n"
              f"{order} are ready and merge cleanly in that order onto {base} ({base_sha[:9]}).\n"
              f"Would push {branch} ({tip[:9]}) and run {WORKFLOW_FILE}. A real run would then print:\n"
              f"{merge_lines()}")
        return

    push_train(branch, tip)
    # A branch pushed a moment ago can be a 404 to the workflow API for a few seconds.
    for attempt in range(5):
        r = run(["gh", "workflow", "run", WORKFLOW_FILE, "--ref", branch], check=False)
        if r.returncode == 0:
            break
        time.sleep(poll if attempt < 4 else 0)
    else:
        die(3, f"{branch} was pushed but the run could not be started: {r.stderr.strip()}")
    print(f"Pushed {branch} ({tip[:9]}): {base} {base_sha[:9]} + {order}. Started {WORKFLOW_FILE}; waiting.")
    sys.stdout.flush()
    run_id, v = wait_for_run(branch, tip, poll, timeout)
    if v.get("conclusion") != "success":
        failed = [j["name"] for j in v.get("jobs", []) if j.get("conclusion") not in OK_CONCLUSIONS]
        die(3, f"The train FAILED ({v.get('conclusion')}): {v.get('url', '')}\n"
               f"Failed jobs: {', '.join(failed) or '(none named)'}\nDo not merge this set as it is.")

    git("fetch", "-q", "origin", f"+refs/heads/{base}:refs/remotes/origin/{base}")
    now = git("rev-parse", f"refs/remotes/origin/{base}").stdout.strip()
    if now != base_sha:
        die(4, f"The train passed, but main moved while it ran ({base_sha[:9]} -> {now[:9]}), so it "
               f"tested a main that no longer exists. Run the train again.")
    for n in a.prs:
        now_head = gh_json("pr", "view", str(n), "--json", "headRefOid")["headRefOid"]
        if now_head != heads[n]:
            die(4, f"The train passed, but #{n} has a new head ({heads[n][:9]} -> {now_head[:9]}). "
                   f"Run the train again.")
    print(f"The train PASSED: {v.get('url', '')}\n"
          f"{branch} tested {order} on {base} {base_sha[:9]} with the full suite.\n"
          f"Merge in this order, with nothing else merged in between:\n{merge_lines()}")


if __name__ == "__main__":
    main()
