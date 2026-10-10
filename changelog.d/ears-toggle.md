### Added
- A "Rack ears" toggle in the kit's Explorer (#909), off by default and shown
  only for a device that gets a generic ear. It turns the generic L-bracket
  ear on in 3D (`viewer.setEars`) and in 2D, where the published face has no
  ears and the kit draws them as an overlay. The choice is remembered per
  viewer, not written into the page's location. Ears built into a face are
  part of the drawing and always shown.
- `@portrayal/kit/ears2d` (kit 0.9.0, the version that also carries the bundle
  exports of #923; kit 0.8.0 is the bend check of #922 alone): `drawEars` and
  `clearEars` draw the generic ear over a published face as
  `render.py --with ears` draws it (the same shapes, ids and colours, and the
  viewBox grown to hold them), from
  `earPlan`, the plan the 3D viewer builds. The overlay is not a part: it
  carries no `data-path`, takes no pointer events, and an export of the live
  drawing carries it as picture. relief.js `EAR` gains `EDGE`, the outline
  colour ears.py draws with.
- `chassis.ears.color` (optional, additive): the colour the generic ear is
  drawn in. configs.json publishes it in `ears` where it is stated, and the
  plan from ears.py and relief.js `genericEars` carries it as `color`.
  devicelock hashes it with the rest of `ears` as chassis surface, so stating
  it is a patch.

### Changed
- The generic rack ear is silver (`#c8cacc`, ears.py `SILVER`, relief.js
  `EAR.SILVER`) unless the device states otherwise, in `render.py --with
  ears`, the 3D viewer and the 2D overlay alike; it was drawn in
  `common/rack-ear@1`'s near-black, which relief.js `EAR.FILL` still names.
  Nothing published moves: no published face draws the ear.
