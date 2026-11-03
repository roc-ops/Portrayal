### Added
- `ufispace/psu-151-dc@2` (2.0.0), the DC supply of the UfiSpace S6301-56ST redrawn from the vendor's installation guide: its
  terminal block is 31.6 mm wide with the three clamp screws 9.6 mm apart (version 1 draws it 24.6 mm wide with the screws
  7.5 mm apart, the third against the block's edge), and its handle stands against the block's right edge. Because the redraw
  moves the boxes of its `terminal-block` and `handle` elements, it is a new major; every id is kept. The supply composes its
  three terminal screws as parts, each a seat a ring lug lands on, and states one DC input port: three poles carrying the legend
  the guide prints under the screws (`rtn` on the left, `batt` in the middle, `gnd` for the earth symbol on the right), the
  datasheet's input current of 6 A and the guide's cable size of 18 AWG. The port states no voltage, because the documents give
  a range without a nominal, and the earth pole is no conductor of a feed.
- `dc-feed-2x18awg`, a DC power feed of two 18 AWG conductors, joins the cable types table (1.2.0 to 1.3.0): the cable the
  UfiSpace S6301-56ST guide names for its DC supply. Its diameter, ampacity and bend radius are estimates, and the type says so,
  as the other DC feeds do. A feed to a DC port that states 18 AWG can now be typed without a cable-size warning.

### Changed
- The S6301-56ST takes a minor (3.1.2 to 3.2.0): its two DC configurations seat `ufispace/psu-151-dc@2`, and its supply bays
  accept it beside `@1`. The build now publishes a DC port for each supply; the lock and the drawing version line of its exported
  device types move with it, and the supply's module types carry contract version 2.0.0. One row of the records file is gone and
  its `cap:` is 155.
- `ufispace/psu-151-dc@1` (1.1.0 to 1.1.1) says `superseded-by: ufispace/psu-151-dc@2`. Its drawing is unchanged, the
  S6301-56ST's supply bays still accept it, and a manifest that pins `@1` still resolves to it; it is no longer exported as a
  module type, because `@2` carries the same part number.
