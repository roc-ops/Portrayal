### Fixed
- `edgecore/ais800-psu-dc@2`: the vent lattice is 23.46 tall from y 13.56,
  measured module edge to module edge on the quick start's Connect Power
  figure, where 1.x drew it 20.12 from 15.01 (#397). `edgecore/ais800-32d`
  2.0.0 and `edgecore/ais800-32o` 3.0.0 accept it.

### Removed
- `edgecore/ais800-psu-dc@1`, replaced by `edgecore/ais800-psu-dc@2` (#397).
  Element ids are unchanged; `vent-field` moved and grew.
