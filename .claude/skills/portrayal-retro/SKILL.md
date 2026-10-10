---
name: portrayal-retro
description: Use when asked for a retrospective on Portrayal work - one session, one pull request, or a period of merged pull requests. Proposes changes to the checks, the review standards, the documents and the test suite so that the same review comment is never written twice. Proposes only; it edits nothing.
disable-model-invocation: true
---

# A retrospective on Portrayal work

A review that catches something has done half its job. The other half is
making sure the next change cannot make the same mistake, or that the next
review is told to look. This skill reads what happened and proposes changes to
the environment the work is done in. It makes none of them: each accepted
proposal becomes an ordinary pull request.

## 1. Read what happened

Use what you were pointed at. With nothing named, take the pull requests merged
in the last seven days.

```sh
gh pr list --state merged --search "merged:>=<date>" --json number,title,mergedAt
gh pr view <n> --comments
git log --oneline --grep "review" origin/main --since=<date>    # fixes a review made
```

Read, for each: the body, the review comments, and above all the commits made
after the pull request was opened. A commit named for a review is a mistake
that reached review. Read your own notes from the sessions concerned if you
have them.

Read the test-time report in each run's job summary, and the `test-times`
artifact if you want the figures.

## 2. Look for candidates

For each thing that went wrong, or went slowly, ask which of these it is.

- **A check.** Could a tool have caught it? Classify first. A **mechanical**
  mistake - a fixed pattern, a missing key, a count, a file in the wrong
  place - gets a check: a lint rule, a test, a lock bucket. Read
  [`docs/lint-rules.md`](../../../docs/lint-rules.md) before proposing one; a
  rule that exists and did not fire is the finding, and a new rule is not.
  State the rule as a property of hardware, never of one vendor, and say what
  it finds when run against the library today.
- **A review standard.** If it is a judgement no tool can make, does
  [`docs/review-standards.md`](../../../docs/review-standards.md) tell the
  reviewer to look? Propose the line. Propose removing a line that a check now
  covers, or that has caught nothing.
- **A pitfall.** A misreading of a figure or a tool that the next modeller
  will repeat belongs in [`docs/modelling-pitfalls.md`](../../../docs/modelling-pitfalls.md),
  under the heading it fits. Propose it in the form that page asks for: the
  mechanism as a rule, then the check, and the device left out unless the
  entry is a measurement or the rule is not believable without the case.
- **Navigation.** Did the work spend a long time finding a file, a command or
  a convention? Propose a pointer in [`AGENTS.md`](../../../AGENTS.md), which
  holds pointers and nothing else.
- **Weight.** Is a document every agent must read carrying text that only a
  reviewer needs, or that changes nothing anyone does? Propose moving it to
  the review standards, or deleting it.
- **Test time.** Which tests were flagged, which files are slowest, and what
  are they doing? Propose the redesign: a shared run in place of a repeated
  one, a fixture built once, a lint rule in place of a test. A test that
  cannot fail, or that restates the code it tests, is proposed for removal.
- **Access.** Was something the work needed out of reach - a log, a rendered
  view, a document? Say what would have made it available.

## 3. Check each candidate before proposing it

A proposal nobody ran is a guess. For a check, write the probe and run it over
the real library; report what it found and what it missed. For a test-time
claim, give the seconds from the report. For a standard, name the pull request
where it would have changed the outcome.

## 4. Present

List the candidates, most valuable first. For each: what happened and where
(the pull request and the commit), which kind it is, the change proposed, and
what you ran to check it. Say which you would do first and why.

Then stop. Whoever asked decides which to take; each accepted one is its own
change, opened and reviewed like any other.
