### Added
- A two-hole lug across a pair of studs (#828). Three connector interfaces,
  `stud-pair-5-8`, `stud-pair-3-4` and `stud-pair-1`, each spanning two
  `terminal-stud` seats at the pitch in its name (15.875, 19.05, 25.4), and a
  lug for each, `generic/two-hole-lug-5-8@1`, `-3-4@1` and `-1@1`, drawn
  across with the wire leaving along the pair. Pair hosts compose two studs at
  the pitch and present the pair at their midpoint, at the top of the studs:
  `juniper/mx-ground-stud-pair-5-8@1`, `juniper/mx-ground-stud-pair-3-4@1`,
  `common/ground-stud-pair-5-8-m6@1`, `-5-8-1-4@1`, `-3-4-1-4@1` and
  `-1-1-4@1`. A pair and its two studs are one level or the other (L115); each
  stud still takes the ring lug alone. docs/connectors-dc-terminal-design.md
  section 13.7.
- Sized ground screws (#830): `common/ground-screw-m6@1` (ISO 7045 pan head)
  and `common/ground-screw-1-4@1` (ASME B18.6.3 pan head), used only inside the
  pair hosts. `common/ground-lug@1` stays the nominal, unsized ground screw.

### Changed
- L116's depth arm reads where a spanned part PRESENTS, its placed `lift` plus
  its own seat out, rather than its `lift` alone. Nothing the library placed
  before changes: an LC bore presents at its own face. A stud presents at its
  top, which is where a lug across a pair lies (#828).

### Fixed
- `devicelock` no longer calls a change minor because it added an id while
  something already there moved: the added placements are taken back out and
  the rest must still hash to the old shape, or the change is a major (#828).
