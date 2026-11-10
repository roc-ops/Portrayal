### Added
- The 3D viewer builds a housing that states `chassis.section` as its end profile extruded along the
  width (`kit/section.js`), not as a plain box. Each side facet takes the texture of the face it looks
  toward by planar projection (a facet facing up or down samples the top or bottom drawing along its
  length and depth, one facing the front or rear samples that drawing at its own height and length), and
  the two ends take the end drawings, whose clear corners the profile now leaves empty. Picking, level of
  detail and the opening view read the body as they read a box. No device in the library states a
  `section` yet, so no published build changes; ports, bays and component relief on such a device still
  stand on the flat face plane, and fins, the image exports and an open state are not part of this change.
