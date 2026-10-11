### Added
- `docs/rack-mounting-design.md`, the design note for ear positions and rail
  kits, written to match what merged: `chassis.ears` and its positions,
  `chassis.kits`, the `kind: kit` contract, the generic ear that is drawn only
  when asked for, what `configs.json`, `kits.json` and the DCIM exports carry,
  the lint rules by code, and what stays in provenance. It says what is not
  built (#908, #910, the worked examples), and its kits are examples under a
  made-up namespace, since the library holds no kit yet (#904, #911).
- The modelling method gains a step after the panel for a rack device, with
  gate 1b: write `chassis.ears` with the positions the installation guide
  names and `chassis.kits` with every kit, referencing a kit the library has
  and writing a `kind: kit` contract for one it does not. Each rule has its
  check (`docs/modelling-a-device.md`, the `portrayal-model-device` skill).
  `library/components/README.md` documents `kind: kit` (#911).
- Vendor intake stages rail and mounting-kit guides, rail sizing matrices,
  accessory tables and the rack-mounting figures of each installation guide
  (the `portrayal-vendor-intake` skill). Review checks the default ear
  position against that figure, and the range of a kit against its newest
  source, with provenance naming the source that lost
  (`docs/review-standards.md`, the `portrayal-review` skill) (#911).

### Changed
- The ear cases of Stage 1 in `docs/modelling-a-device.md` are written as
  rules with their checks, each device a marked illustration, and a fourth is
  added: a plate as wide as the rack is drawn whole, with its ears (#911).
- `library/README.md` lists `kits.json` and `rack.json` among the files of a
  build. `docs/adjustable-positions-design.md`, `docs/rack-products-design.md`
  and `docs/pdu-model-design.md` link the rack mounting note where they cited
  it by issue number (#911).
