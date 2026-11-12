### Added
- Raritan PX2-2475 zero-U rack PDU, 1539 x 52 x 65 mm, with six views: 24 NEMA 5-20R outlets in three groups of eight on the
  printed 35 mm pitch, a controller panel with two display windows, five lamps, a reset pinhole, Ethernet, feature, sensor,
  USB-B, USB-A and console jacks, two mounting buttons on the back, and a cord that ends in a NEMA L5-20P plug. The maker's
  specification and its mechanical diagram disagree on the input (a plug on a cord against a C20 inlet); the device follows the
  specification and records the disagreement as a gap. Positions are read off the maker's drawing to about 1 mm; colours, the
  cord gland and the mounting button's head are estimates. This closes no row of the port records.
- Part for the PX2: `raritan/px2-cord-l5-20p@1`, the cord's gland, which exports one `nema-l5-20p` power port. Its size is an
  estimate, declared in the contract.

### Changed
- The DCIM export reads a `std/db9@1` placement that says `role: console` as a `de-9` console port, as it already reads a
  card's D-sub console. No other device places that part, so no other export moves.
