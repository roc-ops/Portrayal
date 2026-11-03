### Changed
- Four Juniper EX DC supplies compose the screws of their terminal blocks as parts, every one a seat a ring lug lands on, and state
  the DC ports their hardware guides describe (each contract takes a minor, 1.0.0 to 1.1.0). `juniper/ex4300-jpsu-550-dc-afo@1`
  and `juniper/ex4300-jpsu-550-dc-afi@1` (the EX4300 550 W supplies, one block of five screws printed + - earth - +) state one port
  per feed, `feed-a` on the left pair and `feed-b` on the right pair, with the roles `pos` and `neg` for the V+ and V- the supply
  prints, the guide's -48 VDC nominal with its range and its 14 to 16 AWG cable; the earth screw between the feeds is common to
  both and is a ground seat outside both ports, drawn with the library's nominal ground screw as a declared stand-in.
  `juniper/ex4500-psu-dc-fb@1` states one input port with the poles `batt` (-48V) and `rtn` (RTN), the guide's -48 VDC nominal and
  range and its 30 A. `juniper/ex9253-jnp-pwr1100-dc@1` states one input port with the poles `rtn` and `batt`, a 32 A rating and no
  voltage, because its table prints two nominals; its two studs with nuts are a declared stand-in on the terminal screw part.
  No skin is redrawn: each supply gains a screw head at the centre of each terminal its skin already draws, and every screw head,
  the earth screw's included, is an estimate, and its contract says so.
- The four EX switches that seat them take a minor (`juniper/ex4300-32f`, `juniper/ex4300-48t` and `juniper/ex4500-40f` from 0.2.1 to
  0.3.0, `juniper/ex9253` from 0.1.1 to 0.2.0), because the build now publishes their DC ports; and `juniper/ex4300-24p`,
  `-24t` and `-48p`, which only accept the two EX4300 supplies, take a patch (0.2.1 to 0.2.2). Their locks and the drawing version line
  of their exported device types move with them, and the supplies' module types carry the new contract versions. No port, interface
  or id moves. Four rows of the records file are gone and its `cap:` is 151.
