### Added
- The library's first two `kind: kit` contracts, which no device lists yet (#904): `cisco/69-2037`, the
  standard rack-mount kit of the Catalyst 4948E and 4948E-F (two brackets, rack depth 488.95 to 825.5 mm),
  and `cisco/n9k-c9500-rmk`, the Nexus 9500 bottom-support rail kit (two rails, rack depth 609.6 to
  812.8 mm). Their parts are `cisco/69-2037-bracket@1` and `cisco/n9k-c9500-rmk-rail@1`, with estimated
  sizes, which each kit's `gaps` entry `part-dimensions` records. They appear in `kits.json` and the catalogue's "Rail kits" table; `components.json` does not
  list them. No DCIM export or device lock changes.

### Fixed
- The whole-library census tests accept a `kind: kit`: the class vocabulary, the cage census, the catalogue
  and the index columns tests, and the `components.json` count in `test_onebuild.py`, no longer expect a kit
  to have a `class` or a row of `components.json` (a kit is counted from `kits.json`). A new
  `test_kit_census.py` checks each kit is in `kits.json` and the "Rail kits" table and in neither
  `components.json` nor the component tables (#904).
