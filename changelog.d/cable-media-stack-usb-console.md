### Added
- A cable's `media` has three more values, `stack`, `usb` and `console`, so a
  stack or USB cable is no longer a mismatch for its own ends. A console cable
  is told from a USB one by the port's role, which the Rack Builder's port
  readers do not pass yet, so it still reads as its connector there. A rack file that saves one holds a value an older kit does not know.
  **A reader that does not know a media must keep it** and draw the cable as one
  with no media, as for any media it does not know. The kit (`kit/rack`) gives
  each of them a label, a family, a plug reach, an end allowance, a diameter, a
  drape, a bend radius and a colour; every figure is an estimate and the cable
  types table says so. The stacking interfaces (`flexstack`, `stackwise-480`,
  `ex4200-vcp`) are stack ends and the USB receptacles are USB ends; an end
  whose port role is `console` is a console end whatever its connector
  (`connectorOf` takes `role`). The `stackpower`, `cisco-rps2300` and
  `ex3300-rps` interfaces are power ends. The published `rack.schema.json` and
  `site.schema.json` list the new values in the description of a cable's
  `media`.
- `cable-types.json` (table version 1.2.0) gains DC feed types by gauge (`dc`,
  `conductors`, `ampacity-a`, `ampacity-sources`), ground-wire types by gauge,
  the bare types `ground`, `stack`, `usb` and `console`, the Cisco RPS 2300
  cable (`cab-rps2300-e`), the StackPower cables (`cab-spwr-30cm`,
  `cab-spwr-150cm`) and the FlexStack cables (`cab-stk-e-0-5m`, `cab-stk-e-1m`,
  `cab-stk-e-3m`). Families `ground`, `stack`, `usb` and `console` are new, and
  a type may carry `sources` and `note`. A consumer that does not know a key or
  a family ignores it.
- The DCIM cables file writes the three new media with the `CABLE_TYPE` row the
  kit holds for each, which is blank: the cable-type choices of the two tools
  were not read, so no value is written. Such a cable is in the file with its
  type blank.

### Changed
- A ground wire that names no type is judged by the bare `ground` type's bend
  radius (50.4 mm) and drapes as a power cord does, where it took the unset
  figures before. A USB-C or other USB port reads as a USB end, where it was
  an end of no known family.
