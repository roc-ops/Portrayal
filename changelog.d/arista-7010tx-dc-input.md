### Changed
- The Arista 7010TX-48-DC terminal block (`arista/7010tx-dc-terminal@1`, 1.0.0 to 1.1.0) states one DC input port, `input`, on its two
  screws, with the roles the vendor's quick start guide prints beside them: `batt` on the upper screw (printed -48V) and `rtn` on the
  lower (printed RTN). The port states no voltage, because the guide prints the range -40 to -72 VDC, no current, because it prints
  2.5 A without saying per switch or per supply, no wire size, because it prints the range 14 to 18 AWG, and no side, because no
  document says which supply is feed A. The block's drawing is unchanged. Each supply's block is now a power end, so the DC
  configurations offer two places to land a cable.
- The switch that places it (`arista/7010tx-48`, 0.1.2 to 0.2.0) takes a minor, because the build now publishes its DC ports, with its
  lock and the drawing version line of its exported device types (8 files in NetBox and Nautobot). No port, interface or id moves. One
  row of the records file is gone and its `cap:` is 158.
