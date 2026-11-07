### Changed
- `juniper/qfx5230-jnp-3000w-dc-afo@1` (1.0.0 to 1.1.0), the DC supply of the Juniper QFX5230-64CD and QFX5700, composes its two input
  terminals as parts, each a pair of studs on 5/8 in. centres that one two-hole lug lands across, and states one DC input port with
  `rtn` and `batt` poles, the roles the QFX5230-64CD hardware guide prints for its terminals (RTN and -48V/-60V). The supply now
  offers a power end a DC feed can land on. The pitch is the one the QFX5700 hardware guide prints for the lugs of this part. No held
  figure shows the studs, which pair is which or any mark printed at the block, so the stud positions and the order of the two pairs
  are estimated, drawn inside the footprint of the terminal block cover, and the contract says so. The port states no voltage and no
  current, because the guides give a range and two currents for one supply.
- The two devices that place it, the QFX5230-64CD and the QFX5700, each take a minor, because the build now publishes a DC port for
  them, with their locks and the drawing version line of their exported device types; the supply's module type carries the new
  contract version. No port, interface or id moves. One row of the records file is gone.
