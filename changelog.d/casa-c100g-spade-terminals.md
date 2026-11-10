### Added
- `spade-m4`, a connector interface for a spade (fork) terminal slid onto an M4 post, and `generic/spade-lug@1`, the spade terminal that mates it:
  a tongue with an open slot, a yellow sleeve and a stub of wire, drawn at the 9.3 mm outside diameter the Casa C100G Hardware Installation
  Guide allows at most. The guide's chapter 6 says 9.2 mm for the same terminal; the part names both. The terminal's length, slot, thickness
  and wire are estimates, each with its method, because no terminal drawing is held.

### Changed
- The eight DC posts of the Casa C100G power entry module (`casa/pem@1`, 1.9.0) are now seats a spade terminal lands on. Each post is
  `casa/pem-post@1`, a seat that draws nothing and stands on the nut the module already draws, and presents `spade-m4`. The module's drawing,
  its nuts and every id of it are as they were. The C100G takes a patch for it (its lock, and the `Drawing version` line of its exported
  device types), the module types carry the new contract version and a sentence of the description, and the chassis no longer has a row in
  the records of powered devices that offer no power end.
