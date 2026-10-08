---
name: portrayal-review
description: Use when reviewing a Portrayal change - a branch, a pull request or work in progress - before it is merged. Checks the diff against its sources and against docs/review-standards.md in two separate passes, fixes what it finds, and comments only on what needs a decision.
---

# Reviewing a change to Portrayal

The standards live in the repository, written for a person and equally binding
on an agent: **[`docs/review-standards.md`](../../../docs/review-standards.md)**.
This skill is how to apply them.

Review is a separate pass from building, on purpose. Whoever builds a device is
finding sources, drawing and debugging, and has no attention left for a
checklist. The reviewer is handed a diff and has nothing else to do, so this is
where the standards are imposed.

## 1. Pin what is under review

Take the fixed point you were given: a pull request number, a branch, a commit.
With none given, use the merge base with `origin/main`.

```sh
git fetch origin main
git diff origin/main...HEAD --stat          # three dots: against the merge base
git log origin/main..HEAD --oneline
```

Stop here if the ref does not resolve or the diff is empty. A review of nothing
reads as a clean review.

## 2. Find the sources

- The issue the commits or the pull request name, read with `gh issue view`.
- For a device or component: the `datasheet`, `references` and `provenance`
  the manifest cites. The documents themselves are not in the repository. If
  you hold them, read them; if you do not, say which claims you could not
  check, and do not report them as checked.
- If there is no issue and no cited source, the sources pass reports exactly
  that and nothing else.

## 3. Run two passes, apart

Use two subagents when you have them, so that neither reads the other's
conclusions; otherwise do one pass, write it down, then do the other.

**Sources.** Give it the diff command, the commit list and the sources. Ask
for: what the sources asked for that is missing or partial; what the diff adds
that nothing asked for; what is present but wrong. Each finding quotes the line
of the source it rests on.

**Standards.** Give it the diff command, the commit list and
`docs/review-standards.md`. Ask for every place the diff departs from a
standard, citing the standard. Tell it to skip anything lint, the lock or the
suite already enforces, and to mark the tool-and-kit heuristics as judgement
calls and never as violations.

For a device or component, the standards pass must look at the drawing, not
only at the YAML. Render what changed and view every face and module zoomed:

```sh
./build.sh --device <model>
```

For a device that states `chassis.ears` or `chassis.kits`, or a new
`kind: kit`, the sources pass also does two checks the standards name. It puts
the `default` ear position beside the rack-mounting figure of the
installation guide. And it reads the range of each kit in every source that
gives one, confirms the contract carries the newest, and confirms provenance
names the source that lost. A kit range checked against one source only is
reported as checked against that source.

Keep each report short. Do not merge or rerank the two: a change that follows
every standard and models the wrong thing fails one pass and passes the other,
and a single ranked list hides that.

## 4. Fix, then commit

For each finding you can settle from the sources and the standards, make the
fix on the branch and commit it, naming the review in the message:

```sh
git add <the paths you changed>
git commit -m "<what changed> (#<pr> review)"
```

Stage explicit paths. Re-run the gates the fix touches (`./build.sh --device`,
the lock check before `--update`, the tests for the file) before pushing.

Leave a comment, and no commit, only where the answer is not yours to give:

- a choice between two readings of a figure that the sources do not settle;
- a one-way door the pull request did not declare, or declared as two-way;
- a waiver, a new allowed skip, a raised census cap;
- a test of five seconds or more with no stated reason.

## 5. Report

Give the two passes under their own headings, each with what was found, what
you fixed (with the commit) and what you left as a question. End with one line
per pass. If a pass could not run, say so; do not let a short list read as a
clean result.
