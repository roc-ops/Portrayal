### Added
- `spec/tools/portrayal/infrahub_export.py` writes Infrahub object files for every
  device type and module type from the NetBox export tree: one manufacturers file,
  then one file per maker. A type's name is `<manufacturer> <model>`; `height` is
  the `u_height` rounded up (a half-unit type says its nominal height, a zero-U type
  has no `height`); a device type carries `weight` in whole kilograms and an exact
  `weight_grams`. The tool also writes the schema overlay and a README that lists
  the schema files to load and what is left out (racks, placed devices, interfaces,
  cables, type-level ports and bays, drawings, console and power ports). It writes
  where `--out` says and nothing is published yet. The overlay and the file shape
  follow `docs/infrahub-export-design.md` and are unverified against an Infrahub
  instance.
