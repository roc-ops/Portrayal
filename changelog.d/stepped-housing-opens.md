### Added
- A housing that states `chassis.section` may now also state `chassis.halves`, and
  opens in 3D as its stepped body in two parts. The seam is the plane
  `base.stands` from the base's `outer` face; each half is the body on its side of
  it, with the ribs that stand on it, ribs outside the box included; the lid turns
  about the line where the seam meets the hinge face's outline, parallel to the
  length, which in a flange is the flange's edge. The camera frames both parts. A
  device with no `section` opens as two plain boxes, exactly as before. The inside
  of a half is the authored open drawing's, as for any box that opens.
  **One-way:** stating `halves` with `section`, the faces it takes (`top` or
  `bottom` for the base, `front` or `rear` for the hinge), the seam at
  `base.stands` and the pivot line are published format; `docs/format-stability.md`
  has the section.
- Lint L217 (error): with a `section`, `base.outer` is `top` or `bottom` and
  `lid.hinge` is `front` or `rear`. L218 (warning): the section is at its widest at
  the seam. L219 (error): the seam cuts the section into two parts that each have
  outline, so it is not outside the section, not exactly on a horizontal edge and not
  in a stretch the ribs have cut away.
- `kit/section.js` exports `splitSection` and `sectionHalves`, and
  `housingPlan` in `kit/housing.js` takes the split as an optional third argument.

### Changed
- Lint L206 no longer refuses `halves` with `section`; its other clauses stand.
