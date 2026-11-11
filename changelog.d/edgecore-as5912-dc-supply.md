### Added
- `edgecore/as5912-54x-psu-dc@1` (1.0.0), the 48 VDC supply of the Edgecore AS5912-54X (AGR100): a latch, a black pull handle, a grille and a
  blue Positronic PLA03 connector with a label (RTN, the earth symbol) beside it, as the quick start guide's figure draws it. No document held
  gives this supply a part number, so it is named for the chassis and states none; the DCS204's PSU-48V-650 numbers are not borrowed, because
  the guide rates this chassis's supply "36-75 VDC, 12 A maximum" and prints "-36 - -72 VDC" beside the connector, and the part states no
  input range until the maker says which is right. It composes the existing `common/pla03-receptacle@1` as `inlet`, so a cable's PLA03F7000/AA
  plug seats in it as a cord seats in an AC supply's C14, and says why it states no DC input port yet. Its module type is new, with one power
  port, `inlet`, of type other.

### Changed
- The Edgecore AS5912-54X (`edgecore/as5912-54x`, 3.0.9 to 3.1.0) seats that supply in both its DC builds in place of `common/psu-dc-650@2`,
  and its two PSU bays accept both beside it (a bay that stops accepting a part is a major bump). The back-to-front DC build sets the blue
  latch and the direction on the new supply as it set them on the generic one. A minor, with its lock, its exported device types and a
  new module type. No port, interface or id moves.
- `common/psu-dc-650@2` is not edited: the AS7326-56X still seats it (no document held names that switch's DC supply), so its record in
  the conformance records stays.
