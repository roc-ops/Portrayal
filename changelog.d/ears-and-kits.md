### Added
- `chassis.ears` may be an object as well as the string `behind` (#906):
  `{behind?, h?, y?, positions: [{name, label?, at?, default?, racks?,
  part?: {kit, part}}]}`, where `name` is `flush`, `recessed`, `mid`, `rear`
  or `proud` and `at` is millimetres from the faceplate front back to the ear
  plane. `chassis.kits` lists the rail kits a device takes:
  `[{ref, supply: in-box|optional, variant?: reversed, depth?: {config,
  range}}]`. Both are optional, for a rack device only (L125), and documented
  in `docs/format-stability.md`. No device states either yet.
- Lint L160 to L163 check them: at most one default position; each listed kit
  ref is a `kind: kit`, listed once; a position's `{kit, part}` names a listed
  kit and one of its part ids; a `depth` override names a configuration of the
  kit, in that configuration's shape, with min below max.

### Changed
- A `kind: kit` placed in a view, accepted or defaulted by a bay (L5),
  composed as a part or seated in a component's bay (L10) is refused at lint
  instead of failing at render. A kit's `superseded-by` names a kit, and a
  component's names a component (L101). L43 stands down for
  `ears: {behind: true}` as for `ears: behind`.
- devicelock files `chassis.kits` as chassis surface beside `ears`, so stating
  either is a patch. A listed kit, its parts and its accessories join the
  device's `composed` digest, so a kit edited in place asks each device that
  lists it for a patch. L89 counts a kit a device lists as reached, with its
  parts, and `lint --device` lints the kits a device lists.
- The component catalogue and `composed-by` in `components.json` no longer
  count a kit as composing its parts or accessories.
