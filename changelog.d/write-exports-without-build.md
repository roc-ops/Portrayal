### Added
- `preflight.py --write-exports` writes the DCIM exports into `library/exports` without a build,
  for a change that needs no rendered drawing. It deletes an export nothing writes any more and
  leaves the gitignored pictures alone. CI still checks that the exports are current.
