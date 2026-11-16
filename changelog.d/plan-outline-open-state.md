### Added
- The 3D viewer opens a housing that states `chassis.plan-outline` as two halves the plan cuts:
  each half is the body the plan leaves of it on its side of the seam, with round corners, lobes and
  a casting inset from the flange, and each shows its rim as the plan outline, the polygon of the band
  on that half's side of the seam, in the plain material. The rims exist only in the open state; a
  seam exactly on a band edge gives the two halves two rims. The lid turns about the same hinge line
  as before and its lobes swing with it; the camera frames each half's own extent. The o-ring groove
  stays art in the authored open drawing, and no library device states the key.
- A part on the top, bottom, front or rear of such a housing is seated on the body the plan leaves
  under it, at its own place along the width and the depth: over a lobe or a rounded corner it stands
  on the flange, not on a casting the plan does not have there.

### Fixed
- The USDZ export of any 3D body with more than one material (a box's six faces, a stepped body, an
  open half) held no geometry, because the exporter skips a mesh whose material is a list. It now
  writes one mesh a material. The GLB export is unchanged.
