### Added
- `generic/mini-usb-b-plug@1`, the cable plug that mates the `mini-usb-b` receptacle. The plug shell and
  the overmould maximum are read from the USB 2.0 Mini-B connector ECN (figures 6-8, 6-11 and 6-15); the
  overmould length, the strain relief, the stub and the cable diameter are estimated, each with the drawing
  it needs named in the part's provenance. It seats 1.3 in front of the receptacle face (6.8 shell less 5.5
  of receptacle), where `std/mini-usb@1` models a depth of 9.0, 3.5 more than the drawing gives.

### Changed
- `juniper/ex4300-console-usb-mini@1` (1.1.0) now presents `mini-usb-b`, as the EX4300 and EX4550 hardware
  guides name its form, so the console of the eight EX4300 and EX4550 devices that place it is a connector
  slot that accepts the new plug. Its size, elements, skin and mate point do not change. The eight devices
  (`ex4300-24p`, `-24t`, `-32f`, `-48mp`, `-48p`, `-48t`, `ex4550-32f`, `-32t`) are re-locked, a minor each.
  No drawing, position or id changes, and no port name or interface type changes in any export; the 50 DCIM
  export files differ only in the version number in their description text. The `std/mini-usb@1` slot of the six Catalyst
  9300 and 3650 switches that place it now accepts the plug too.
