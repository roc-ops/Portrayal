### Changed
- Four Edgecore DC supplies compose the two screws of their terminal block as parts, every one a seat a ring lug lands on, and state
  one DC input port of two poles that carry the callouts of the vendor's quick start guide (`rtn` for the DC return, `batt` for the
  negative voltage range): `edgecore/agr-psu-dc@1` (1.0.2 to 1.1.0, the supply of the AS7946-30XB and AS7946-74XKSB),
  `edgecore/fsj033-610g@1` (1.0.0 to 1.1.0, the COR580's), `edgecore/ais800-psu-dc@2` (2.0.0 to 2.1.0, the AIS800-32D's and
  AIS800-32O's) and `edgecore/csr440-psu-dc@1` (1.0.0 to 1.1.0, the CSR440's). Each port states the wire size, and the input current
  where the documents give one figure (not the CSR440's, whose documents print a pair), and no voltage, because the guides give a
  range and no nominal. Their earth screw or stud stands beside the block, not on it, so it is not a pole of the port: each supply
  composes it as a ground part of its own, a seat a ring lug lands on outside the port, drawn as `common/ground-screw@1` or
  `common/ground-stud@1` and declared a stand-in because no document held gives its thread. The COR580's earth part, a decorative
  screw head until now, is a ground screw at the same centre and keeps its id. The supplies' terminal blocks are drawn as before,
  with a screw head at the centre of each screw. All four now offer a power end a DC feed can land on.
- The AS7946-30XB (`edgecore/as7946-30xb`, 4.0.6 to 4.1.0), the AS7946-74XKSB (`edgecore/as7946-74xksb`, 4.0.7 to 4.1.0), the COR580
  (`edgecore/cor580`, 3.1.1 to 3.2.0), the CSR440 (`edgecore/csr440`, 2.1.1 to 2.2.0), the AIS800-32D (`edgecore/ais800-32d`, 2.0.2 to
  2.1.0) and the AIS800-32O (`edgecore/ais800-32o`, 3.0.2 to 3.1.0) each take a minor, because the build now publishes a DC port for
  them, with their locks and the drawing version line of their exported device types (56 files in NetBox and Nautobot); the four
  supplies' module types carry the new contract version (8 files). No port, interface or id moves. Four rows of the records file
  are gone and its `cap:` is 178.
