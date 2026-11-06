### Changed
- `edgecore/csr310-psu-dc@1` (1.0.2 to 1.1.0), the -48 VDC supply of the Edgecore CSR310 and CSR430, and
  `edgecore/dcs500-psu-dc@1` (1.0.0 to 1.1.0), the DC supply of the Edgecore DCS500, each compose the three screws of their
  terminal block as parts, every one a seat a ring lug lands on, and state one DC input port whose three poles carry the callouts
  of the vendor's quick start guide, the earth terminal among them (`gnd`, with `batt` for the negative voltage range and `rtn`
  for the DC return). The earth terminal is a pole of the port, as for the UfiSpace supplies. Each port states the wire size the
  guide gives and no voltage, because the documents give a range and no nominal, and no current, because the documents disagree
  on it or print a pair of currents. Both supplies now offer a power end a DC feed can land on. Their terminal blocks are drawn as
  before, with a screw head at the centre of each screw; the CSR310 supply's skin is regrouped, nothing in it redrawn.
- The CSR310 (`edgecore/csr310`, 1.0.7 to 1.1.0), the CSR430 (`edgecore/csr430`, 1.0.8 to 1.1.0) and the DCS500
  (`edgecore/dcs500`, 4.1.0 to 4.2.0) each take a minor, because the build now publishes a DC port for them, with their locks and
  the drawing version line of their exported device types (36 files in NetBox and Nautobot); the two supplies' module types carry
  the new contract version. No port, interface or id moves. Two rows of the records file are gone and its `cap:` is 180.
