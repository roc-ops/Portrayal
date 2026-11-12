### Added
- `nokia/lpwr-f-dc-pole@1`, one two-stud power terminal of the Lightspan MF-8 LPWR-F power module: two studs on the 5/8 in. centres
  the installation manual's 16 mm (0.63 in.) lug spacing reads as, a pair that one two-hole lug lands across (`stud-pair-5-8`, mate
  `generic/two-hole-lug-5-8@1`). The thread of the studs is not stated by any document held, and the part does not claim one.

### Changed
- The Lightspan MF-8 power module (`nokia/lpwr-f@1`, 1.0.0 to 1.1.0, a minor) composes its BAT and RET terminals as two of those poles,
  turned to the slant the unit's figures draw, and states one DC input port, `input`, with the roles `batt` (BAT, left) and `rtn` (RET,
  right). The port states no voltage, no current and no wire size, because the guides print two nominals and two ratings for the
  module's two builds and no AWG size for its cable. The BAT pair stands where the skin already draws its studs; the RET pair, which
  the hazard label hides, is placed from the open-door figure and is a declared estimate, and stays hidden under the label. The
  drawing is unchanged but for a small screw head on each of the two BAT studs.
- The Lightspan MF-8 shelf that seats it (`nokia/lmfs-f`, 2.0.2 to 2.1.0, a minor) now offers the power module's DC feed, with its
  lock and the drawing version line of its exported device types; the module's type carries the new contract version. No port,
  interface or id moves. The shelf's empty-shelf configuration seats no power module and still has no power end to offer, so its
  row of the records file stays.
