### Added
- **Cable ends for the stack, StackPower and Virtual Chassis ports, and a FlexStack port**
  (`cisco/stackwise-480-plug`, `cisco/stackpower-plug`, `juniper/ex4200-vcp-plug`,
  `cisco/flexstack-plug`, `cisco/flexstack-port`). Each plug mates the key its port presents, in the
  form of the library's other cable ends. No maker drawing of any of the four plugs is held, so each
  is drawn estimated from the opening of its port and says which drawing it wants. The FlexStack
  port is drawn as the module art of the Catalyst 2960-S measured it and is placed by no device yet.

### Changed
- **`cisco/stackwise-480-port`, `cisco/stackpower-port` and `juniper/ex4200-vcp-port` present their
  interfaces** (`stackwise-480`, `stackpower`, `ex4200-vcp`) at a `mate` point, so each is a connector
  slot that accepts its cable end. Size, elements and skin are unchanged. The five Catalyst 9300
  models and the seven EX4200 models each take a minor version for the slots they now publish; no
  placement moves.
- **`juniper/ex4500-vc1` composes the EX4200's Virtual Chassis port at VCP-0 and VCP-1** in place of
  two drawn openings. The EX4500 guide says one 68-pin cable joins the EX4500's dedicated ports to an
  EX4200's, so it is one connector and one part. Each port keeps its centre and is drawn at the
  part's 36.2 x 8.3 mm, where the isometric figure's estimate was 24.0 x 8.0. `juniper/ex4500-40f`
  takes a minor version with it.
