### Added
- **Version 2 of the six MX10000-line fan trays** (Refs #39): `juniper/jnp10004-fan2@2`,
  `juniper/jnp10008-fan@2`, `juniper/jnp10008-fan2@2`, `juniper/jnp10008-fan3@2`, `juniper/jnp10016-fan@2` and
  `juniper/jnp10016-fan2@2`, drawn to the 6.6 in. (167.6 mm) width and the height and depth the Juniper hardware
  guides give (the MX10004 guide's Table 9, the MX10008 guide's Table 12, the MX10016 guide's Table 7): 167.6 x
  306.8 x 139.7 mm, 167.6 x 569.0 mm and 167.6 x 929.6 mm. Version 1 drew them 176 mm wide, from a photograph and
  two line drawings, which was wider than the tables and wider than the bays they stood in.

### Changed
- **The MX10004, MX10008 and MX10016 seat the version 2 trays**, in bays the trays' own size that stand against
  the supply column and against each other, as the guides' rear figures show them. Each is 4.0.0. The QFX10008
  accepts `juniper/jnp10008-fan@2` and `juniper/jnp10008-fan2@2` in place of version 1 and goes to 4.0.0; the
  QFX10016 takes no MX tray and goes to 2.0.2 for the note on its own fan. The `fan-tray-width` gaps are closed
  and the overhang warnings they explained are out of the lint baseline.

### Removed
- **The six version 1 trays are retired, not deleted.** Nothing seats them. Each says `superseded-by` the `@2`
  and stays so a saved rack that names `@1` still resolves.
