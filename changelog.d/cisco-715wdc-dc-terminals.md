### Changed
- The Cisco Catalyst 9300 715 W DC supply (`cisco/pwr-c1-715wdc@1`, 1.0.0 to 1.1.0) composes the three screws of its terminal block as parts,
  every one a seat a ring lug lands on, and states one DC input port of three poles that carry the words and signs of the vendor's hardware
  installation guide: `pos` for the positive polarity terminal, `neg` for the negative polarity terminal and `gnd` for the grounding terminal,
  which is one of the block's three screws and so a pole of the port. The port states the guide's input voltage (-48 nominal, range -36 to
  -72) and no current and no wire size, because the guide prints a pair of currents and two wire sizes. The terminals' drawing is unchanged,
  with a screw head at the centre of each. The supply now offers a power end a DC feed can land on.
- The five Catalyst 9300 switches that seat it (`cisco/c9300-24p`, `c9300-24u`, `c9300-48p`, `c9300-48t` and `c9300-48u`, each 1.1.0 to
  1.2.0) take a minor, because the build now publishes a DC port for them, with their locks and the drawing version line of their exported
  device types (10 files in NetBox and Nautobot); the supply's module type carries the new contract version (2 files). No port,
  interface or id moves. One row of the records file is gone and its `cap:` is 163.
