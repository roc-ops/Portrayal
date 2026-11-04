### Changed
- The Juniper EX-PWR-190-DC supply of the EX4200 switches composes the four screws of its terminal block as parts, every one a seat a
  ring lug lands on, and states the two DC ports its hardware guide describes (`juniper/ex4200-pwr-190-dc@1`, 1.0.1 to 1.1.0).
  The block prints A+, B+, A- and B-, so the supply has one port per feed: `feed-a` on A+ and A- and `feed-b` on B+ and B-, with the
  roles `pos` and `neg` for the + and - it prints and the sides a and b. Each port states the guide's 7 A maximum input current and its
  12 to 14 AWG cable, and no voltage, because the guide's table prints a range and no nominal. The supply is shipped with a jumper from
  A+ to B+ and another from A- to B-, which tie the two feeds into one source; the jumpers are not modelled. No skin is redrawn: the
  supply gains a screw head at the centre of each terminal its skin already draws, and each screw head is an estimate, which its
  contract says.
- The three EX4200 switches that seat it (`juniper/ex4200-24f`, `juniper/ex4200-24t` and `juniper/ex4200-48t`) take a minor, 0.2.1 to
  0.3.0, because the build now publishes its DC ports. Their version records and the drawing version line of their exported device types move
  with them, and the supply's module type carries the new contract version. No port, interface or id moves. One row of the records
  file is gone and its `cap:` is 144.
