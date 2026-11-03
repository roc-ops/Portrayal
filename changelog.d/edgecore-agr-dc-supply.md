### Added
- `edgecore/agr110-psu-dc@1` (1.0.0), the -36 to -72 VDC supply of the Edgecore AGR110 (AS5916-54XL) and AGR130 (AS5916-54XKS). The
  quick start guides show it with a barrier terminal block of three screws one above the other, DC return on the top one, the
  -36 to -72 VDC feed on the middle one and an earth symbol printed beside the bottom one, and the supply is drawn so. It composes
  the three screws as parts, every one a seat a ring lug lands on, and states one DC input port whose three poles carry the guides'
  callouts, the earth screw among them (`gnd`, with `batt` for the voltage range and `rtn` for the DC return), as for the UfiSpace
  and the other Edgecore supplies. The port states the wire size the guides give (#10 AWG; the AGR110 guide's French text prints #14
  and is recorded, not stated), no voltage, because the guides give a range and no nominal, and no current, because they print a pair
  of currents for the whole switch. No maker part number is held for this supply, so it is named for the two chassis and states
  no model.
- Its module type, `Edgecore/agr110-psu-dc`, in NetBox and Nautobot.

### Changed
- The Edgecore AGR110 (`edgecore/agr110`, 8.2.10 to 8.3.0) and AGR130 (`edgecore/agr130`, 0.1.10 to 0.2.0) seat that supply, and not
  `common/psu-dc-650@2`, in their `dc` configuration, and their rear bays accept it beside the generic supply (which they keep
  accepting: a bay that stops accepting a part is a major bump). Each takes a minor, because the build now publishes a DC port for it,
  with their locks and the drawing version line and the two PSU bay descriptions of their exported device types (16 files in NetBox
  and Nautobot). No port, interface or id moves. `common/psu-dc-650@2` is not edited: the AS5912-54X, AS7326-56X and AS7726-32X still
  seat it, and its record in the conformance records stays, so `cap:` is 172.
