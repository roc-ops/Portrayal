### Added
- `spec/tools/portrayal/preflight.py`, one command a builder runs before
  asking for review (#924). Against the merge base with `--base` (default
  `origin/main`), working tree and untracked files included, it prints PASS or
  FAIL per check with the command that fixes it, and `--json` for an agent:
  the DCIM exports regenerated from the tree and compared with
  `library/exports` (no build: the exporter's dist is derived from the
  sources), added skip reasons against `spec/allowed-skips.txt`, private
  strings in added lines, the changelog fragment, `devicelock` (also against
  the base lock for a device the diff re-locked), lint on the touched devices
  and every device that seats a touched component plus the library-wide
  rules a `--device` run skips, with no warning beyond the baseline, and
  `npm test` with the kit behaviour tests that name a changed module when
  `kit/` changed. No build and no suite run.
