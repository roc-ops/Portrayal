### Added
- The FS steel finger ducts, five horizontal cable managers built hollow like
  `fs/cmh-sfd1u`: a sheet body whose backbone is the floor of a well, two rows
  of fingers standing `in:` it, and a cover that can be pulled.
  `fs/cmh-sfds1u` (1U, cover 51 mm high), `fs/cmh-sfds2u` (2U) and
  `fs/cmh-bs-sfds1u` (1U, steel channel with ABS fingers) are single-sided and
  state `full-depth: false`. `fs/cmh-dfds1u` (1U, covers 57.8 mm high) and
  `fs/cmh-dfds2u` (2U) are dual-sided, with a channel and a cover facing the
  front and another facing the rear, and are full depth. Each brings its own
  base, finger and cover components (`fs/<model>-base@1`, `-finger@1`,
  `-cover@1`, and `fs/cmh-bs-sfds1u-finger-end@1`). Only CMH-BS-SFDS1U has a
  stated cable capacity; the other four carry a `vendor-silent` gap for it.
