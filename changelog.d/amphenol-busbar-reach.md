### Fixed
- The -C panels of the Amphenol Network Solutions 300CB08 family
  (`amphenol-ns/300cb08-c`, `nrg300cb08-ctrl-c`, `nrg300cb08-sens-c`) are
  367.0 deep, front of the metal to the tops of the output receptacles, as
  their own bottom view (installation guide Fig. 3-13) measures, not the stud
  panel's 330.8; their bottom is re-read off that view. Their busbar landings
  (`amphenol-ns/input-feed-busbar@1`, 1.0.1) now stand 38.1 and 95.2 behind
  that, the two lengths the drawing dimensions, where both stood 147, a figure
  that subtracted a depth without the front guards from one with them (#860).
  Each of the three panels takes a major (2.0.0): its geometry moved, though
  no id or slot did. Their DCIM exports change in the drawing version line
  only.
