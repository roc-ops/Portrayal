### Added
- A position field may list `drawn-by-absence`: the options drawn by showing
  none of its SHOW nodes. Lint L148 now asks every other option of a field with
  SHOW nodes to show at least one node (#874).

### Fixed
- In 3D, a part whose only SHOW node is hidden by default now rebuilds when
  that node should appear: each part group records its position fields as
  `data-position-fields` before hidden nodes are removed, and the viewer's
  rebuild check reads it (#874).
- A `data-move` entry whose number is not one (`.`, `1.2.3`) is refused by the
  kit as the build refuses it, instead of writing `NaN` (#874).
