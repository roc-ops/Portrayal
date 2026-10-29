### Added
- **`lint.py --list-rules --out <path>`** writes the listing to a file instead of standard output. It
  works with `--json`, `--markdown` or neither, writes the same bytes the standard-output form prints
  (UTF-8), creates the file's folder, and replaces an existing file. `--out` without `--list-rules` is
  an error. The standard-output form is unchanged.

### Changed
- **`build.sh` writes `lint-rules.json` with `lint.py --list-rules --json --out`** rather than a shell
  redirect, so a build that runs its steps one at a time from a script makes the file too.
