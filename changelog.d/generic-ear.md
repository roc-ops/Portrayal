### Added
- A generic L-bracket rack ear, drawn from `chassis.ears` (#909): a flange each
  side reaching from the body to the 482.6 mm rack face, with a slot over each
  rail hole, and a 30 mm leg back along the body, `ears.h` tall and `ears.y`
  up (the chassis's height, and 0, where they are absent), its flange on the
  default position's `at`. `render.py --with ears` draws it on all six faces as
  `ear-left` and `ear-right`; the kit's viewer builds it in 3D with
  `createViewer(el, {ears: true})` or `viewer.setEars(true)`, from relief.js
  `genericEars`, and a GLB taken then carries it. A device that is not a
  `rack` device, states `ears: behind`, has a front as wide as the rack face or
  still places `common/rack-ear@1` gets none in 2D. The default build draws no
  ears, so no published face, export or device lock changes.
- Lint L164 warns when `chassis.ears` `y + h` is above the chassis, and L165
  when two ear positions have the same `name` and `label`.

### Changed
- devicelock keeps `chassis.ears.h` and `y` as surface now that an ear is drawn
  from them, since that ear is never in a published face; the reasoning is in
  `docs/format-stability.md`, which also now says a kit's missing
  `description` is published as an empty string, as the code always wrote it.
