### Changed
- The Juniper QFX5130 DC supplies (`juniper/qfx5130-jpsu-1600-dc-afi@1` and `-afo@1`, 1.0.0 to 1.1.0) and the MX104 DC supply
  (`juniper/mx104-psu-dc@1`, 1.1.0 to 1.2.0) compose their two terminal screws as parts, each a seat a ring lug lands on, and state one
  DC input port of two poles, with the roles the vendor's hardware guides give. On the QFX5130 supplies the left screw is the V+
  "(return)" terminal, role `rtn`, and the right screw the V- "(input)" terminal, role `batt`, and the port states the guide's wire
  sizes, 10 and 12 AWG. On the MX104 supply the left screw is the input (-) terminal, `batt`, and the right the return (+) terminal,
  `rtn`. No port states a voltage, because the guides print a range or three nominals, and none states a current, because the guides
  print a different figure for each chassis or each voltage. The drawings are unchanged, with a screw head at the centre of each
  screw. The supplies now offer a power end, so a feed can land on each.
- The QFX5130-32CD, QFX5130-48C, QFX5220-32CD and MX104 that seat them take a minor each, because the build now publishes their DC
  ports, with their locks and the drawing version line of their exported device types (42 files in NetBox and Nautobot); the supplies'
  module types carry the new contract version (6 files). No port, interface or id moves. Three rows of the records file are gone and
  its `cap:` is 156.
