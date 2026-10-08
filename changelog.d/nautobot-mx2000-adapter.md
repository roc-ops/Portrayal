### Fixed
- Nautobot: the MX2000 line-card adapter (`MX2000-LC-ADAPTER`) exports its
  `mpc` bay, so an MPC can be installed in it in an MX2008, MX2010 or MX2020
  slot (#917). The bay has a blank position: Nautobot skips a blank position
  when it names ports, so an MPC in the adapter in `fpc3` names its ports
  `fpc3/port-0-0`, the names the same MPC takes in an MX960's `fpc3`. NetBox
  is unchanged and still says `fpc3/mpc/port-0-0`. A carrier's only bay that
  accepts a module also seated directly in a chassis bay is given this way;
  the adapter is the only one today.
- Nautobot: the MICs that only an MPC takes (`MIC-3D-4XGE-XFP` and the four
  `MIC3-3D-*`) name their ports `{module.parent}/{module}/x` again, as before
  #261 made the adapter count as a second depth for every MPC. **BREAKING for
  DCIM data already imported** from an export taken since #261 merged: those
  five module types need re-importing. Their bays on the MPC1E, MPC2E and
  MPC3E are still withheld from Nautobot (nautobot/nautobot#5823), as in an
  MX240, MX480 or MX960.
