### Added
- Juniper EX4200 fixed access switches (#39): the EX4200-24T, EX4200-24P, EX4200-24PX, EX4200-24F,
  EX4200-48T, EX4200-48P and EX4200-48PX (`juniper/ex4200-24t`, `-24p`, `-24px`, `-24f`, `-48t`, `-48p`,
  `-48px`), each with its front and rear panels. The -24T, -24F and -48T have a -DC build (EX4200-24T-DC,
  -24F-DC, -48T-DC) and the -24F and -48T a spare-chassis build (EX4200-24F-S, EX4200-48T-S); the Trade
  Agreements Act codes of the others are part numbers of the same configurations. The uplink module bay
  is modelled with its cover panel; the four EX-UM uplink modules are left for their own slice.
- The EX4200's own field-replaceable parts, family-prefixed: the fan tray (`juniper/ex4200-fan-tray`), the
  EX-PWR-320-AC, EX-PWR-600-AC, EX-PWR-930-AC, EX-PWR2-930-AC, EX-PWR3-930-AC and EX-PWR-190-DC power
  supplies, the power supply and uplink slot cover panels, the LCD navigation buttons and the Virtual
  Chassis port (`juniper/ex4200-vcp-port`). The model plate's "8PoE" line and the orange numerals 0 to 7 of
  the -24T and -48T are two small parts placed on the AC build only, because the -DC builds give no PoE
  (`juniper/ex4200-poe-plate`, `juniper/ex4200-port-numerals`).
- The DCIM device types for the EX4200 builds, in the NetBox and Nautobot exports, and the module types for
  the six power supplies.
