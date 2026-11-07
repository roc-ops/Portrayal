### Added
- `juniper/mx304-psu-dc@2` (2.0.0), the MX304 DC power supply redrawn from the hardware guide's figures. They show the round fan grille
  with the orange handle crossing it at the left, and at the right a raised terminal block printed -48V/-60V and RTN with four studs
  under four nuts; version 1 drew two studs 11 mm apart on a flat black plate. Because the redraw moves the supply's boxes, it is a new
  major. The guide's cable lug has two holes 0.63 in. apart, so each of the two terminals takes one two-hole lug across a pair of
  studs: the supply composes two of `juniper/mx240-dc-pole@1`, a pair of studs on 5/8 in. centres (`stud-pair-5-8`, mate
  `generic/two-hole-lug-5-8@1`), as `pole-batt` for -48V/-60V and `pole-rtn` for RTN, and states one DC input port of those two poles,
  with the guide's 6 AWG wire and its 50 A input current rating, and no voltage, because the guide prints two nominals. Which pair of
  studs is which terminal is read from the isometric figures, which do not bracket the studs under the labels, and the studs' own
  spacing and thread are not dimensioned by any document held; the contract says so. The photograph of the rear of the router shows
  two large bolts where the figures show four studs, and the drawing follows the figures.

### Changed
- The MX304 (`juniper/mx304`, 4.0.4 to 4.1.0) takes a minor: its supply bays accept `juniper/mx304-psu-dc@2` beside `@1`, its `dc`
  configuration seats the `@2`, and the build now publishes the two DC ports of the two supplies. Its device file, its lock and the
  drawing version line of its exported device types move with it, and the supply's module types carry the new contract version. One
  gap's text records that it was re-read. One row of the records file is gone.
- `juniper/mx304-psu-dc@1` (1.0.1 to 1.0.2) says `superseded-by: juniper/mx304-psu-dc@2`. Its drawing is unchanged, the chassis'
  supply bays still accept it, and a manifest that pins `@1` still resolves to it; it is no longer exported as a module type, because
  `@2` carries the same part number.
