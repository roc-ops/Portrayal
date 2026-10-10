### Changed
- The rule for a retired component major is stated the same way in
  `spec/DESIGN.md` section 9, `docs/format-stability.md` and
  `library/components/README.md`. While the package is at 0.x, a superseded
  major may be removed, and every removal is listed in `CHANGELOG.md` with the
  ref that replaces it. The deprecation mechanism is required before 1.0: the
  `superseded-by:` marker, a stated support window, and L89 telling a
  deprecated major from a dead one. No lint behaviour changes
  (roc-ops/Portrayal#448).
- `library/components/README.md` says that moving decoration nothing
  addresses, inside an unchanged part outline, is a minor bump, and names
  `fs/d-ring-snap-in@1` 1.3.0 as the precedent (#968).
