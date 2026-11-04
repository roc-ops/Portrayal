### Added
- `juniper/mx240-dc-pole@1`, one pole of the MX240 and MX480 normal-capacity DC power entry module: two terminal studs on the
  5/8 in. centres of the lug the guide dimensions (0.625 in. between holes, the MX240 guide's Figure 22), a pair that one two-hole
  lug lands across (`stud-pair-5-8`, mate `generic/two-hole-lug-5-8@1`). The studs' own spacing is not dimensioned by any document
  and the part says so.
- The MX240 and MX480 DC power entry module (`juniper/mx240-psu-dc@1`, 1.1.0) composes its two terminal poles as seats a two-hole
  lug lands across, and states one DC input port: the left column of studs is the return (`rtn`) and the right column the
  -48 V feed (`batt`), as the supply prints them. The port states the guide's -48 V nominal (range -40.5 to -72 V) and its 6 AWG
  wire, and no current: the guide gives a rating of 33.3 A and a maximum of 40 A.

### Changed
- The MX240 (6.2.1 to 6.3.0) and the MX480 (7.2.1 to 7.3.0) each take a minor: the build now publishes a DC port for the supply
  they seat. Their device files and the drawing version line of their exported device types move with them, and the supply's
  module types carry the new contract version. The drawing gains only the seats' small screw heads. One row of the records file
  is gone and its `cap:` is 144.
