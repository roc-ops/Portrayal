### Added
- **`juniper/jnp10k-pwr-blnk@2`**, the JNP10K-PWR-BLNK supply cover at 91.4 x 88.9 mm, the size of the
  JNP10K-PWR-AC2 it stands beside (Refs #39). Its size is derived, as before: no guide gives one for the cover.

### Changed
- **The MX10004, MX10008, MX10016 and QFX10016 seat `juniper/jnp10k-pwr-ac2@2`** (Refs #39), the supply
  drawn to the 3.6 x 3.5 in. (91.4 x 88.9 mm) every Juniper hardware guide gives it (the MX10004 guide's
  Table 22, the MX10008 guide's Table 55, the MX10016 guide's Table 39 and the QFX10016 guide's Table 16).
  Their supply bays were 84.0 wide and 91.0 to 97.0 high, the size the supply was first drawn from a
  photograph, spread over the height of the fan trays. They are now 91.4 x 88.9 mm and stand one above the
  next, as the guides' figures draw them, and the two fan trays beside them are 175 mm wide, not 176. The
  MX10004, MX10008 and MX10016 go to 3.0.0 and the QFX10016 to 2.0.0, with the MX10000 covers on `@2` of
  the cover. The QFX10008 goes to 3.0.1 for its notes. The DCIM device types change only in the drawing
  version they name in their comments; no bay is renamed.

### Removed
- **`juniper/jnp10k-pwr-ac2@1` and `juniper/jnp10k-pwr-blnk@1` are retired, not deleted.** Nothing seats them.
  Each says `superseded-by` the `@2`, and stays so a rack or a contract that names `@1` still resolves.
