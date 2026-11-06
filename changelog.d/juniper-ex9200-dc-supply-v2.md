### Added
- `juniper/ex9200-pwr-mx480-2400-dc@2` (2.0.0), the 2400 W DC supply of the EX9204 and EX9208 redrawn from the vendor's hardware
  guides. The EX9204 guide's Figure 57 and the MX480 guide's Figure 83 show, on each supply, a block of two columns of two studs, the
  two studs of a column one above the other, with the legend RTN, a direct-current sign and -48V printed above it, left to right.
  Version 1 drew two studs side by side and no legend. Because the redraw changes the count and the place of the studs, it is a new
  major. Each column is a pair of studs on 5/8 in. centres, the pitch of the two-hole cable lug the guides dimension (holes 0.28 in.
  across, 0.625 in. apart, 6 AWG), composed as `juniper/mx240-dc-pole@1`, so each is a seat a two-hole lug lands across. The supply
  states one DC input port, `input`, with the roles `rtn` (left) and `batt` (right) the legend prints, the nominal -48 VDC and
  range -40.5 to -72 VDC of the guides' tables and the 6 AWG cable of every guide. It states no current, because the supply takes 60 A
  or 70 A by its input mode switch. The colours are version 1's, declared estimates: no photograph of this supply is held.

### Changed
- The EX9204 and the EX9208 (`juniper/ex9204` 0.1.2 to 0.2.0, `juniper/ex9208` 0.1.2 to 0.2.0) take a minor each: their DC
  configurations seat `juniper/ex9200-pwr-mx480-2400-dc@2`, their supply bays accept it beside `@1`, and the `dc-supply-face` gap
  says the terminal block is redrawn from line-art figures. The build now publishes the DC port of each supply.
- `juniper/ex9200-pwr-mx480-2400-dc@1` (1.0.0 to 1.0.1) says `superseded-by: juniper/ex9200-pwr-mx480-2400-dc@2`. Its drawing is
  unchanged and a saved rack that seats `@1` still opens. The one conformance record that named `@1` goes.
