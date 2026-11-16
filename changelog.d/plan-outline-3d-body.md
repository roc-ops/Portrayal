### Added
- The 3D viewer builds the closed body of a housing that states `chassis.plan-outline` as the
  section cut band by band (`kit/plan.js`, the same x-sweep as `portrayal.plan`, and
  `kit/plan-body.js`): rounded corners and lobes show in 3D, a casting inset from the flange is
  narrower than it, and the transparent corners of the top and bottom faces are no longer holes.
  The front and rear walls the section has keep their drawings; a wall that comes from a plan edge
  is plain, in a new material slot (7) coloured as the faceplate, and a hit on one picks as the
  long face it is on. The mesh is watertight. Ribs are cut to the band they stand in. A housing
  without the key builds exactly as before. The open state of such a housing still builds its two
  halves from the section alone, parts do not yet stand on the plan, and the GLB and USDZ exports
  do not yet treat the new slot; no library device states the key.
