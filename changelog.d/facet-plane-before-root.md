### Fixed
- **A part whose box starts before its facet's root edge stands on the facet's plane carried on
  past the root** (`kit/relief.js`). `facetZ` held the height at the root's, so such a part floated
  by the overshoot times the tangent of the facet's angle (3.75 mm for 6.5 mm on a 30 degree
  facet). The slope now carries on in a straight line below the root's height, as a sunk facet's
  surface does. A part on the facet, and a facet's own wedge, are drawn exactly as before, and no
  library part starts before a root edge, so no built face and no published `data-z-*` value moves.
  The design note says so. The allowance the facet lint rule gives such an overshoot is unchanged.
  No record of the conformance list is closed.
