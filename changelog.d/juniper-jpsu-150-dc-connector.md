### Added
- The connector interface `juniper-dc-block-3`, the three-position pluggable DC power connector of the Juniper JPSU-150-DC-AFO supplies
  of the EX3400 and EX4100 switches, a block with three cells in a column printed "+", "-" and an earth symbol and a mounting hole at
  each end (EX3400 Switch Hardware Guide, Figures 46 and 47; EX4100 Switch Hardware Guide, Figures 74 and 75, the same drawing). The
  guides name no maker, series, pitch or dimension for it (the EX3400 guide names Molex 192120005 for the wire pins only), so the key
  claims none.
- `juniper/jpsu-150-dc-header@1` (1.0.0), that connector as the two supplies carry it, and `juniper/jpsu-150-dc-plug@1` (1.0.0), the
  cable connector of the figures, which mates it. Both are declared stand-ins with estimated sizes (10.0 by 25.0), and no document
  names a part number for either.

### Changed
- `juniper/ex3400-jpsu-150-dc-afo@1` and `juniper/ex4100-jpsu-150-dc-afo@1` (1.0.0 to 1.1.0) compose the header inside the block their
  skins already draw, so a cable plugs into the supply as a cord plugs into an AC supply's inlet. The roles of the three cells (`rtn`,
  `batt` and `gnd`, from the marks and the guides' note on them) are recorded in their provenance and no DC port is stated yet, because
  the three poles are the cells of one pluggable connector. The skins are unchanged, so the header covers the three round screw heads
  they drew there. Their two records in the conformance records go.
- The four devices that seat them (`juniper/ex3400-24t`, `juniper/ex3400-48t`, `juniper/ex4100-24t` and `juniper/ex4100-48t`, a patch
  each) take new locks and the drawing version line of their exported device types; the supplies' module type carries the new
  contract version. No port, interface or id of a device moves.
- The module type of the supplies, in NetBox and Nautobot, exports its power port as `{module}/dc-header`, of type other and labelled as
  the DC power connector block, where it exported `{module}/Inlet` of type dc-terminal. A DCIM that imported the earlier type keeps the
  old port until it is re-imported.
