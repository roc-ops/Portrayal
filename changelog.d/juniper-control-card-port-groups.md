### Changed
- The ports on five more Juniper boards now join a port group, so a port on a board seated in a slot says what it is
  for and, where the hardware guide prints it, the rate it runs at. They are the MX304 LMIC16 (sixteen QSFP-DD cages:
  the four the guide's figure colours 400G/100G form one group at up to 400 Gbps, the other twelve another at up to
  100 Gbps), the EX4500 Virtual Chassis module (its two Virtual Chassis ports, with no rate, because no page prints
  one), the RE-S-2000 routing engine (USB, auxiliary, console and Ethernet jacks) and the REMX2K-X8-128G and
  RE-MX2000-1800x4 control-board routing engines (a management group and a timing group for the BITS jack). On the
  three routing-engine boards the console and auxiliary jacks are now typed `rj45-serial` and the control boards'
  management Ethernet jack states the 1 Gbps its guide prints, as the REMX2K-X8-64G beside them already does; the
  RE-S-2000's Ethernet jack states no rate, because its guide's two passages disagree. Part ids, positions and drawn
  geometry are unchanged; each contract takes a minor, and the seven chassis that seat them (the MX240, MX480, MX960,
  MX304, MX2010, MX2020 and EX4500-40F) take a patch. No conformance row is closed or opened.
