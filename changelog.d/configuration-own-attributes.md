### Added
- **A configuration can carry its own attributes and export description.** A
  configuration takes `attrs`, the device's own sections and types, for what that
  build states differently (its power figures, its memory), and
  `export-description`, up to 200 characters, for the description a DCIM shows
  for its device type. A key the configuration names wins and the rest of its
  section stays the device's; with neither key a configuration exports exactly as
  before. NetBox and Nautobot read the configuration's own values for the facts
  in `comments` and for `description`; neither key is legal on an `example`.
  `<device>.configs.json` gains `configs[].attrs`, the configuration's own keys
  (`{}` where it has none). Both keys and the new field are optional and
  additive: `format` and `contract` do not change, and no device uses them yet,
  so no export changes.
