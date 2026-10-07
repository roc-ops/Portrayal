### Added
- `chassis.full-depth: false` states that a rack device leaves the opposite
  face of its rack units free, and the DCIM export writes it as
  `is_full_depth: false`. A rack device that says nothing keeps the `true` it
  has always exported; this is stated rather than derived from `depth`, so no
  existing export changes. L125 refuses it on a device that is not `rack`
  mounted (#854).

### Changed
- `fs/cmh-4drb1u` 1.0.1 and `fs/cmh-sfd1u` 0.1.1 state `full-depth: false`;
  both export `is_full_depth: false` (#854).
