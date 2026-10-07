### Changed
- From 1.0, a retired component major is deprecated with the `superseded-by:`
  key the schema already has, naming the ref that replaces it, not with a new
  `deprecated:` marker as `spec/DESIGN.md` section 9 and
  `docs/format-stability.md` said. Nothing implemented the marker, so no
  manifest changes (roc-ops/Portrayal#448).
