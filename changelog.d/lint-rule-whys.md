### Added
- Every lint rule says why it exists: what it prevents, and for whom (#952).
  `docs/lint-rules.md` gains a why column and a severity column, saying
  whether a finding warns, fails, or warns until a device claims
  `maturity: verified`.
- `lint-rules.json` in the dist: the rule table as data for the site's rule
  page, written by `lint.py --list-rules --json` from the same table as the
  page. Each rule carries its code, scope, rule, why, fix, severity, and
  `fails`, `warns` and `fails-at-verified` (#952). It ships in
  `@portrayal/index`.
