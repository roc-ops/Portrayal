### Added
- `<device>.configs.json` carries `chassis.kits`: each rail kit the device
  lists, resolved inline in the order listed - the device's `supply`,
  `variant` and `depth` override, and the kit's `version`, `description`,
  `motion`, `travel`, `install`, `configurations` (with the override applied),
  `parts` and `accessories`, each part and accessory with its `version`,
  `class`, `size` and `body` (#907). These are the refs devicelock's
  `composed` follows from `chassis.kits` (#906), and `render.py --if-stale`
  now rebuilds a device when a kit it lists, or a kit's part or accessory,
  changes. No device lists a kit yet.
- The DCIM exports say a device's ear positions and rail kits in the
  comments, beside the overhang line, since neither NetBox nor Nautobot has a
  field for either (#907).

### Changed
- `<device>.configs.json` publishes `chassis.ears` as an object, always: the
  bare `ears: behind` is `{"behind": true}`, and an object is published with
  the keys it states, lengths as floats (#907). `fs/uscmh-sfdabsb2u`, the one
  device that states `ears`, publishes `{"behind": true}` where it published
  `"behind"`, and its NetBox and Nautobot exports gain one comment line saying
  its ear flanges fold back behind the body. The string form was never in a
  release. Documented in `docs/format-stability.md`.
- The L5 catalogue text says what the rule checks: no placement ref, and no
  bay's `accepts` or `default`, is a `kind: kit`.
