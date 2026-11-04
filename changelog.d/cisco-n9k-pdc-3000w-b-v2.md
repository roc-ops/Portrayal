### Added
- `cisco/n9k-pdc-3000w-b@2` (2.0.0), the Nexus 9500 3 kW DC supply redrawn from the vendor's installation guide. The guide's
  figures put the power switch and the FAIL/ID and OK lamps at the top as the supply stands in the chassis, a hexagon vent grille
  down the face, the release lever along the right edge and, down the lower left, a terminal box with four posts in a column under
  a three-screw safety cover, printed `-1+` and `+2-`; version 1 drew a large dark panel, the four posts in a row across the lower
  middle and a small switch near the bottom. Because the redraw moves the boxes of the supply's parts, it is a new major; the
  `ok` and `fail` lamp ids are kept. The supply composes its four posts as parts, each a seat a ring lug lands on (a declared
  stand-in on the library's terminal screw: no part draws a post with two nuts), and states two DC input ports, `input-1` on the
  first two posts and `input-2` on the last two, each with the roles `neg` and `pos` the guide gives and the guide's recommended
  cable size, 6 AWG. The ports state no voltage, because the guide prints two nominals, and no current, because the guide's
  45 A is the circuit's requirement. The supply has no earth terminal of its own, so none is composed. The Nexus 9504, 9508 and
  9516 guides print the same text and figures.

### Changed
- The Nexus 9504, 9508 and 9516 (`cisco/n9k-c9504` 2.2.0 to 2.3.0, `cisco/n9k-c9508` 1.2.0 to 1.3.0, `cisco/n9k-c9516` 2.2.0 to
  2.3.0) take a minor each: their DC build seats `cisco/n9k-pdc-3000w-b@2`, and their supply bays accept it beside `@1`. The
  build now publishes the two DC ports of each supply; the locks and the drawing version line of the exported device types move
  with them, and the supply's module types carry contract version 2.0.0 (the power port is still `{module}/Inlet`). One row of the
  records file is gone and its `cap:` is 144.
- `cisco/n9k-pdc-3000w-b@1` (1.0.0 to 1.0.1) says `superseded-by: cisco/n9k-pdc-3000w-b@2`. Its drawing is unchanged, the
  chassis' supply bays still accept it, and a manifest that pins `@1` still resolves to it; it is no longer exported as a module
  type, because `@2` carries the same part number.
