### Changed
- On a housing that states `chassis.section`, the 3D viewer now stands a part on the casting under it
  instead of on the flat plane of the bounding box. A part on the front or rear face is placed at the
  depth of the section's outer surface under the row of its centre, and a part on the top or bottom face
  at the height of the section under the column of its centre; relief `out` is measured from there.
  The end faces are flat and nothing on them moves (`surfaceUnder` in `kit/section.js`, `partSeats` in
  `kit/relief.js`). A device with no section is placed exactly as before, and no device in the library
  states one, so no published build changes. A front or rear part that runs across a step takes the depth
  under its centre row, and lint does not refuse it; fins, relief from a fin field and an open state are
  not part of this change.
