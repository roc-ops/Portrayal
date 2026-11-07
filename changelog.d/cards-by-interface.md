### Added
- **A slot can seat cards by form** (`docs/cards-by-interface-design.md`). A
  component bay may state `interface`, beside `accepts` or instead of it, and a
  card states `mates`, as an optic seats in a cage. `spec/schemas/connectors.yaml`
  gains the interface keys `pcie-fh` and `pcie-lp`, each pointing at its
  `pcie-bracket-*` standards entry; the two-slot bracket mates `pcie-fh` and
  states `slot-width: 2`. A bay that states both takes the union: every ref in
  its list and every part that mates the interface. A bay that states no
  `interface` stays a closed list. A card `slot-width: n` is taken through an
  interface only by a bay whose `span` names at least `n - 1` bays, so adding a
  two-slot card to the library does not fail a riser that can never span.
- **`components.json` and `<device>.configs.json` publish every ref a bay
  takes** as `accepts`, and an `interface` beside it for a bay that states one.
  For a bay that states none, `accepts` is the list the contract states.
- **Lint L194** (warning): a bay that states an `interface` also lists, in
  `accepts`, a part that mates it and is wide enough. L6, L8 and the nested-bay
  check ask the one predicate, `manifest.takes`; L185's third clause reads
  explicit lists only.

### Changed
- **L11 no longer asks a `mate` connection point for the `mates` of a part with
  `behaviour: fills`**: the bay places a card by `at`. A part that occupies a
  receptacle, or states no behaviour, is asked as before. The schema's
  description of `mates` says so.
- The DCIM description of a module bay that states an `interface` says the
  interface's note and then any list.
- No library part states `interface` or the new `mates` yet, so no part, device
  lock or export changes with this.
