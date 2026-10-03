# Maintainer notes

Process that only the maintainer runs. A contributor does not need any of it:
open the pull request, and the maintainer merges it once the gates are green.

## How a merge happens, and why it is a script

```sh
.github/merge-if-green.sh <pr-number>
```

**The script checks what branch protection checks.** While the repository was
private, required status checks and rulesets were unavailable (a paid feature
for a private repository), so GitHub could not refuse a bad merge, and the
script was the stand-in: it checks the two things branch protection would have
checked, at the one place every merge goes through. Now that the repository is
public, #155 turns branch protection on for `main`. Until it has, the script is
still the only check.

The second of those two is the one that matters and the one a green tick does
not give you. **A green run on a branch says the branch works; it does not say
the branch works with what has landed since.** #100 and #101 were each green
and each correct, and `main` went red the moment both were in, because neither
had ever been run against the other. That is what `strict` means in branch
protection, and the script checks it by refusing to merge a branch that is
behind its base.

Use it rather than `gh pr merge` until branch protection is on. Before then,
nothing enforces it, and that is exactly how it gets skipped.

**Green is enough for a two-way door, and not for a one-way one.** Every pull
request states its merge danger; `CONTRIBUTING.md` lists what makes a change a
one-way door. A two-way door that is green and up to date is merged without
being read again. A one-way door is read first, by the maintainer, because a
revert will not undo it. A pull request that declares two-way while the diff
renames a component, removes an export or touches a workflow is treated as
one-way, and the declaration is corrected.
