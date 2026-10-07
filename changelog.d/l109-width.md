### Fixed
- Lint L109 judges a declared `optical.polarity` against the pattern for the
  trunk connector's own fibre count, read from its `optical.positions` as L80
  reads it, and compares only the ports actually wired (roc-ops/Portrayal#524).
  It used to count the paths, so an MTP-24 Type AF cassette with fibres
  declared `unused`, or wired to twelve ports, was judged as a narrower
  connector: its correct row-exchanged paths failed and the plain pair swap
  passed. A module whose trunk is stated in `optical.trunk` (#246) is now
  judged too; it used to be skipped without a word.

### Changed
- Lint L109 judges a polarity only at a width a held source draws it at
  (`POLARITY_WIDTHS`: Type A and AF at 12 and 24 fibres, universal at 12, all
  from the FHD MTP-12/24 Cassettes Datasheet). At any other width it warns
  "polarity not judged at this width" instead of passing or failing a
  generalisation (roc-ops/Portrayal#524). One library part is affected:
  `fs/fhd-fap12mtp16-a@1` declares Type A on twelve MTP-16 adapters, a width
  no held source draws Type A at, and now carries that warning where it used
  to pass.
