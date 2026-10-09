### Added
- `@portrayal/kit` 0.8.0: the bend check for cable bundles (#922,
  `docs/cable-bundles-design.md` section 5.2). With `ctx.bendOf`
  (`loadCableTypes(dist).bendOf`, #919), `bundleCheck` and every bundle
  command's findings check the bundle at each corner of its trunk, and at each
  pathway whose guide states a `radius`, against the largest installed radius
  among the members present there, so one fibre makes a bundle as strict as
  fibre. A corner's room is worked out from its legs, `min(a_in, a_out) /
  tan(theta / 2)`, and marked estimated; a pathway's stated radius is its
  room. Each miss is a warning, never a refusal, naming the place, the room,
  the member that sets the need and how far it falls short. A member with no
  radius is listed as unchecked, never passed. `inspect` of a bundle gives
  `bend: {radius_mm, by, unchecked, points, violations}` where it gave `null`,
  and `cornersOf` and `bendCheck` are exported from
  `@portrayal/kit/rack/bundles`. Cables outside a bundle are not checked.
