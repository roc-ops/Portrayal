### Added
- **The drawings follow a housing's plan outline.** A device that states `chassis.plan-outline`
  now has its top and bottom faces drawn as the union of the bands' polygons, the corners left
  transparent (the bottom is the mirror in x), with the step between bands as a line inside it.
  Each rib stripe is cut to what the plan leaves of the body and joined into one path; a rib left
  in several pieces gets ids `-a`, `-b`, and a rib the plan removes is not drawn. The front and
  rear outline is the body's extent at each row of the section, so an inset casting is narrower
  than the flange and a rounded corner narrows it only where the corner is. An end face stays
  the section's outline and shades, in the plain tone, the part where the plan leaves no cap. A
  device that does not state the key is drawn byte for byte as before. The cut is one x-sweep in
  `portrayal/plan.py`, with its answers for small cases worked by hand in
  `spec/tests/fixtures/plan_outline/sweep-cases.json`, which the kit's version will read too.
- **Lint L226 to L234.** Errors: the body the plan leaves reaches each of the four sides of the
  box (L226); a part stands where its face has the surface it is drawn on (L227); a seam's rim on
  each half is not empty and is in one piece (L228) and reaches the line the lid turns on (L229).
  Warnings: a rib the plan removes or cuts (L230), a point outside the section's depth (L231), a
  point moved onto a side or a wall (L232), two bands that differ at a height that is not a row of
  the section (L233), and a depth of the section no x of the plan reaches (L234).

### Changed
- The two-way 2D side of the plan outline; no library device states the key yet and a test still
  fails if one does. This closes no row.
