### Changed
- The two pluggable connectors of the Juniper EX4100-H switches now present the registered key of the connector they are
  (`juniper/ex4100-h-psu-connector@1` presents `terminal-381-5` and `juniper/ex4100-h-alarm-connector@1` presents
  `terminal-350-6`, each 1.0.0 to 1.1.0), each at a mate point, and each has a part that mates it
  (`juniper/ex4100-h-psu-plug@1` and `juniper/ex4100-h-alarm-plug@1`, new, the conductor ends the guide clamps into the
  connector, drawn as declared stand-ins because the guide names no maker or part). The marks printed beside each connector are
  recorded as roles. The alarm connector carries no power: it takes dry contacts and gives relay contacts.
- The four EX4100-H power supplies (`juniper/ex4100-h-24f-dc-psu@1`, `-24mp-dc-psu@1`, `-jpsu-340w-ac@1` and `-jpsu-90w-ac@1`,
  each 1.0.0 to 1.1.0) say in their contracts that no cable lands on them: the guide lands the AC or DC wires on the power input
  terminals on the front of the switch, so the supplies draw no inlet or terminal. Their faces are unchanged.
- The three switches that place them (`juniper/ex4100-h-12mp`, `-24f` and `-24mp`, each 0.2.0 to 0.2.1) take a patch, with their
  locks and the drawing version line of their exported device types. Six rows of the port records are gone.
