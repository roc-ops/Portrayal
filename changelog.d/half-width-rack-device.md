### Added
- **Two rack devices of half the opening or less can stand side by side in one rack unit** (#1274, part 1).
  A `mount: rack` device that states a width of 225 mm or less may now say `side: left` or `side: right`.
  225 mm is half the 450 mm opening, so two of them fit. A finger bracket already worked this way.
  Fit lets one device stand on each rail at the same unit, and `side.place` and `side.set` take it.
  No key is added to a device: the width it already states decides.
  Lab checks L142 and L153 read the same width.
  A wider device, and a device with no `side`, take the whole unit as before.
  Such a device on a rail is judged by its rail.
  The elevation, the 3D view and the cable guides draw it upright and centred across the opening, not on the rail.
  Its port points are placed the same way, and the DCIM files state no rail.
  Nothing is turned, and a frame notice says it does not stand on its rail yet.
  A tray with bays is not part of this change, and `heldBy` still takes only null.
  This is one-way: a saved rack and a lab can now name `side` on a rack device.
