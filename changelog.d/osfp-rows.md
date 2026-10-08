### Changed
- Lint L108 now checks stacked OSFP cages, which it used to skip. A stacked
  OSFP cage is one connector that seats both modules heat sink up (OSFP MSA
  rev 5.22 section 7.1, Table 7-1, Figures 7-1 and 7-2), so an OSFP pair has
  to be turned alike: 0 over 0, 180 over 180 for a cage on the underside of
  the board, or both 90 or both 270 on a card drawn on its side. SFP, QSFP
  and QSFP-DD stacks are still belly-to-belly (upper 0 over lower 180). An
  OSFP pair turned 0 over 180 needs a recorded reading in
  `stack-exceptions:` (#799).
- `edgecore/ais800-32o` 2.0.0: the lower OSFP row is now drawn the same way
  up as the upper (rotate 0), as the quick start guide's elevation and its
  install render show. Two optics seated in one column no longer overlap
  nose to nose by 1.66 mm. 0.06 mm of overlap remains because the drawn row
  pitch is 14.54, against the MSA's 14.90. Its DCIM exports change in the
  drawing version line only (#799).
- `celestica/ds4100` and `celestica/ds4101` 0.1.1 keep their lower OSFP
  rows turned 180, and now say why: each install guide's elevation draws the
  lower cage as the upper turned over. Their 18.9 and 18.4 mm row pitches
  leave room for a board between the rows, so these are single cages on both
  faces of one board rather than stacked cages. Each pair is named in
  `stack-exceptions:` (#799).
- `celestica/ds5000`, `ds6000` 0.1.1, `ds6001` 0.1.2 and
  `edgecore/ais800-64o` 4.0.1 keep their OSFP turns for now. Each pair is
  named in `stack-exceptions:`, and a new `stacked-osfp-orientation` gap says
  what would settle it. Their drawings read as the lower bank turned over
  (0/0 over 180/180), which neither the current geometry nor the first #799
  proposal matches. `ufispace/s9321-64eo` 1.0.16 corrects a provenance note
  that still said OSFP stacks were not checked (#799).
