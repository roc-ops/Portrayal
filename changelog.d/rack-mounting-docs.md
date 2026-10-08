### Added
- `docs/rack-mounting-design.md`, the design for ear positions and rail kits:
  `chassis.ears` positions, `chassis.kits`, the `kind: kit` contract, what the
  exports carry and what stays in provenance (#904, #911).
- The modelling method gains a step after the panel for a rack device: write
  `chassis.ears` with the positions the installation guide names and
  `chassis.kits` with every kit, referencing a kit the library has and writing
  a `kind: kit` contract for one it does not (`docs/modelling-a-device.md`,
  the `portrayal-model-device` skill). `library/components/README.md`
  documents `kind: kit` (#911).
- Vendor intake stages rail and mounting-kit guides, rail sizing matrices,
  accessory tables and the rack-mounting figures of each installation guide
  (the `portrayal-vendor-intake` skill). Review checks the default ear
  position against that figure, and the range of a kit against its newest
  source, with provenance naming the source that lost
  (`docs/review-standards.md`, the `portrayal-review` skill) (#911).
