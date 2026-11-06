### Changed
- The Cisco Catalyst 3650 640 W DC supply (`cisco/pwr-c2-640wdc@1`, 1.0.0 to 1.1.0) composes the five screws of its terminal block as
  parts, every one a seat a ring lug lands on, and states one DC input port per feed, as the vendor's hardware installation guide
  labels them: `feed-a` on the A+ and A- screws (side a) and `feed-b` on the B- and B+ screws (side b), each with the roles `pos` and
  `neg` and the guide's one input wire size, 12 AWG. The grounding terminal between the two feeds is common to both, so it is a ground
  seat outside both ports, drawn with the library's nominal ground screw as a declared stand-in. The ports state no voltage, because
  the guide prints two nominals, and no current, because it prints a pair. The block's drawing is unchanged, with a screw head at the
  centre of each screw. The supply now offers two power ends, so the two feeds can land on two sources.
- The Catalyst 3650 switch that seats it (`cisco/ws-c3650-48pd`, 1.1.1 to 1.2.0) takes a minor, because the build now publishes its DC
  ports, with its lock and the drawing version line of its exported device type (2 files in NetBox and Nautobot); the supply's module
  type carries the new contract version (2 files). No port, interface or id moves. One row of the records file is gone and its `cap:`
  is 159.
