### Added
- `juniper/ex9214-pwr-mx960-4100-dc@2` (2.0.0), the EX9214 4100 W DC supply redrawn from the vendor's hardware guide. The guide's
  figures put the power switch, a door over the input mode switch and the four lamps at the top as the supply stands in the chassis, a
  vertical handle below them, and, about three fifths of the way down, a terminal strip printed `INP0` and `INP1` over four
  legends, `-48V`, `RTN`, `RTN` and `-48V`, above a lower cover; version 1 drew the switch at the top middle, the lamps at the upper left
  and a plain strip with no terminal. Because the redraw moves the boxes of the supply's parts, it is a new major; the lamp, switch
  and handle ids are kept. The supply composes four poles of `juniper/mx240-dc-pole@1`, one for each legend, each a pair of studs on
  the 5/8 in. centres of the two-hole lug the guide draws, a landing that lug lands across, and states two DC input ports, `input-0`
  on the first two poles and `input-1` on the last two, with the roles the legends give (`batt` and `rtn`) and the guide's -48 V
  nominal and -40 to -72 V range. The ports state no current, because the guide gives two figures per feed, and no wire size, because
  the EX9214 and MX960 guides print 6 and 4 AWG for the same part number. No figure draws a stud: the poles stand at the legends and
  their height on the face is an estimate, and the contract says so.

### Changed
- `juniper/ex9214-pwr-mx960-4100-dc@1` (1.0.0 to 1.0.1) says `superseded-by: juniper/ex9214-pwr-mx960-4100-dc@2`. Its drawing is
  unchanged, byte for byte.
- The EX9214 (`juniper/ex9214` 0.2.1 to 0.3.0) takes a minor: its four supply bays accept the @2 beside the @1 and its DC
  configurations seat the @2, so the build publishes the supply's two DC ports. Its lock and the drawing version line of its exported
  device types move with it, and the supply's module types carry the new contract version. A saved rack that seats the @1 still opens.
  The device gains one gap, `dc-terminal-studs`, and the gap `dc-supply-face` is reworded. The one conformance record that named the @1
  goes.
