### Added
- `edgecore/as7326-56x-psu-dc@1` (1.0.0), the -48 VDC supply of the Edgecore DCS203 (AS7326-56X): a latch, a black pull handle, a grille and a
  blue Positronic PLA03 connector with a label (RTN, the earth symbol) beside it, as the quick start guide's figure draws it. No document held
  gives this supply a part number (the data sheet lists the AC supplies' only), so it is named for the chassis and states none; the DCS204's
  PSU-48V-650 numbers are not borrowed. The guide and the data sheet print one input range, so the part states it as printed, "-36 - -72 VDC",
  and no nominal voltage. It composes the existing `common/pla03-receptacle@1` as `inlet`, so a cable's PLA03F7000/AA plug seats in it as a cord
  seats in an AC supply's C14, and says why it states no DC input port yet. Its module type is new, with one power port, `inlet`, of type other.

### Changed
- The Edgecore DCS203 (`edgecore/as7326-56x`, 4.0.0 to 4.1.0) seats that supply in both its DC builds in place of `common/psu-dc-650@2`, and
  its two PSU bays accept both beside it and the AC supply (a bay that stops accepting a part is a major bump). The back-to-front DC build sets
  the blue latch and the direction on the new supply as it set them on the generic one; the generic supply's terminal-cover colour is not
  carried over, because the new supply has no cover. A minor, with its lock, its exported device types and a new module type. No port,
  interface or id moves.
- No device seats `common/psu-dc-650@2` bare now, so its row in the conformance records is gone: this change closes one row. The part is not
  edited, and the devices that only list it among the supplies a bay accepts are not touched.
