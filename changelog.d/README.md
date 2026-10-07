# Changelog fragments

A pull request records its change here, in one new file, and does not edit
`CHANGELOG.md`. Every pull request used to add its entry at the top of the
same section of that file, so any two of them conflicted and the second to
merge had to merge main in again. A new file that no other pull request
touches cannot conflict.

Name the file after the branch or the topic (`fibrain-hd-lc.md`,
`ground-stud-lugs.md`) and put each entry under the heading it belongs to.
Only these four headings are accepted:

```markdown
### Added
- What is new, what seats it, what a consumer has to do (#123).

### Changed
- ...

### Removed
- ...

### Fixed
- ...
```

Leave out a heading with nothing under it. An entry starts with `- ` and its
continuation lines are indented two spaces, the way `CHANGELOG.md` writes
them, and the prose follows the same rules: say what is true after the
change, mark a change that re-files DCIM data **BREAKING for DCIM data
already imported**, and name the ref that replaces a removed component major.

Until a version is cut, the unreleased record is the `## Unreleased` section
of `CHANGELOG.md` followed by every file here.
`python3 spec/tools/portrayal/changelog.py --show` prints the two together;
`--check` is what the test suite runs on these files. Cutting a version runs
`--assemble`, which folds each entry in after the ones already under its
heading and deletes the fragments (`docs/maintainers.md`).
