### Changed
- `edgecore/cor550-psu-dc@1` (1.0.0 to 1.1.0), the 48 VDC supply of the Edgecore COR550, composes its two terminal screws as
  parts, each a seat a ring lug lands on, and states one DC input port: two poles carrying the callouts of the vendor's quick
  start guide (`rtn` on the left screw, `batt` on the right), the 40 A input current and the #10 AWG wire size the guide gives.
  The supply now offers a power end a DC feed can land on. Its terminal block is drawn as before, with a screw head at the
  centre of each screw. The port states no voltage, because the two documents give different ranges and no nominal.
- The COR550 (`edgecore/cor550`, 3.1.1 to 3.2.0, a minor, because the build now publishes a DC port for it) takes its lock and
  the drawing version line of its six exported device types in each of NetBox and Nautobot; the supply's module type carries
  the new contract version. No port, interface or id moves. One row of the records file is gone and its `cap:` is 179.
