### Changed
- The Juniper EX4600 DC supplies (`juniper/ex4600-jpsu-650-dc-afi@1` and `-afo@1`), the QFX5100 DC supplies
  (`juniper/qfx5100-jpsu-650w-dc-afi@1` and `-afo@1`), the QFX5200 DC supplies (`juniper/qfx5200-jpsu-850w-dc-afi@1` and `-afo@1`)
  (each 1.0.0 to 1.1.0) and the MX204 DC supply (`juniper/mx204-psu-dc@1`, 1.2.0 to 1.3.0) compose the four screws of their terminal
  block as parts, each a seat a ring lug lands on, and state one DC input port of two poles. The block prints V-, V-, V+, V+ from the
  left and the guides say the two V+ screws are joined inside the supply, as are the two V- screws, and that a supply takes one
  feed: the port's `batt` pole is the left V- screw and its `rtn` pole the left V+ screw (the guides call V- the "(input)" terminal
  and V+ the "(return)" terminal), and the second screw of each pair is a seat outside the port. The guides do not say which screw
  of a pair carries the pole; the contracts declare it a choice. No port states a voltage, because the guides print ranges or two
  nominals. The 850 W pair states 10 A and the MX204 supply 20 A, the one figure each guide gives; the 650 W pairs state no current,
  because the chassis guides print 7, 8, 10 and 20 A for the same part number. The wire size, 14 and 16 AWG, is stated except on the
  EX4600 AFO supply, whose seating chassis guides disagree. The drawings are unchanged, with a screw head at the centre of each screw.
  The supplies now offer a power end, so a feed can land on each.
- The sixteen devices that seat them take a minor each, because the build now publishes their DC ports (EX4550-32F and -32T, EX4600-40F,
  EX4650-48Y, EX9251, MX204, QFX3500-48S4Q, QFX3600-16Q, QFX5100-24Q, -48S, -48T and -96S, QFX5110-32Q and -48S, QFX5120-48T,
  QFX5200-32C), with their locks and the drawing version line of their exported device types (144 files in NetBox and Nautobot); the
  supplies' module types carry the new contract version (14 files). No port, interface or id moves. Seven rows of the records file are
  gone and its `cap:` is 141.
