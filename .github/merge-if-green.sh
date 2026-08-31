#!/usr/bin/env bash
# Refuse to merge a pull request that CI has not blessed, and that has not been
# tested against what it will land on.
#
# WHY THIS EXISTS INSTEAD OF BRANCH PROTECTION. Required status checks and
# rulesets are both gated behind GitHub Pro for a private repository, so the
# server will not enforce anything here. This is the client-side stand-in: it
# checks the two things branch protection would have checked, at the one place
# every merge in this repo actually goes through.
#
# IT CHECKS TWO THINGS, AND THE SECOND IS THE ONE THAT BIT US. A green run on a
# branch says the branch works. It does not say the branch works with what has
# landed since. #100 and #101 were each green and each correct; main went red
# the moment both were in, because neither had ever been run against the other.
# That is what `strict` means in branch protection - the branch must be up to
# date with the base before its result counts - and it is checked here.
#
#   .github/merge-if-green.sh 104
set -euo pipefail
PR="${1:?usage: merge-if-green.sh <pr-number> [extra gh pr merge args...]}"
shift || true
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

read -r STATE HEAD BASE MERGEABLE < <(gh pr view "$PR" --json state,headRefName,baseRefName,mergeable \
  -q '[.state, .headRefName, .baseRefName, .mergeable] | @tsv')
[ "$STATE" = "OPEN" ] || { echo "PR #$PR is $STATE, not OPEN"; exit 1; }
[ "$MERGEABLE" = "MERGEABLE" ] || { echo "PR #$PR is $MERGEABLE - resolve conflicts first"; exit 1; }

SHA=$(gh pr view "$PR" --json headRefOid -q .headRefOid)

# 1. every check that reported must have passed, and `gates` must be among them.
#    A PR with no checks at all is the failure this script exists to catch, so
#    an empty list is a refusal rather than a pass.
runs=$(gh api "repos/$REPO/commits/$SHA/check-runs" -q '.check_runs[] | "\(.name)\t\(.status)\t\(.conclusion // "-")"')
[ -n "$runs" ] || { echo "no checks reported on $SHA - has the workflow run?"; exit 1; }
echo "$runs" | while IFS=$'\t' read -r name status conclusion; do
  printf '  %-24s %s %s\n' "$name" "$status" "$conclusion"
done
echo "$runs" | grep -q "^gates	completed	success$" || {
  echo "the 'gates' check has not completed successfully on $SHA"; exit 1; }
bad=$(echo "$runs" | awk -F'\t' '$2=="completed" && $3!="success" && $3!="neutral" && $3!="skipped"' | wc -l | tr -d ' ')
[ "$bad" = "0" ] || { echo "$bad check(s) did not pass"; exit 1; }

# 2. the branch must have been tested against the current base. See above.
git fetch -q origin "$BASE"
behind=$(git rev-list --count "$SHA..origin/$BASE")
if [ "$behind" != "0" ]; then
  echo "#$PR is $behind commit(s) behind origin/$BASE."
  echo "Its green run tested $HEAD alone, not $HEAD on top of what is there now -"
  echo "which is exactly how main went red on 2026-08-31. Update the branch and"
  echo "let CI run again:  gh pr update-branch $PR"
  exit 1
fi

echo "gates green on $SHA and up to date with $BASE - merging"
gh pr merge "$PR" --merge --delete-branch "$@"
