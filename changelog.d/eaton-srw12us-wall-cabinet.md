### Added
- **The Eaton (Tripp Lite) SRW12US swinging 12U wall cabinet as a rack product,
  `eaton/srw12us`** (#1110, in part). A `wall-cabinet` with 19 in rails and square
  holes for M6 cage nuts, equipment up to 520.7 mm deep, an outer box of
  623.07 x 637 x 548 mm, 27.21 kg and a static load of 90.7 kg, read from the
  maker's specification sheet, submittal drawing and manual for swinging
  wall-mounted enclosures. The
  cabinet has four rails; the product states its front rail alone, as the
  library does for every wall cabinet, and a `gaps` entry holds what is left:
  the rear rails and the range they slide through. The sheet and the drawing
  differ on the height and the width of the box, and on the size of the cable
  entry; the dimensioned drawing is written and `gaps` entries name both
  prints. The door, side panels, fan ports, swing, keyhole wall fixing (16 in
  apart) and the optional SRCASTER caster base are in the description and in
  `gaps` entries, because the rack product has no key for them. The unit
  numbering, the hole spacing and the clear opening are EIA-310 stand-ins that
  `gaps` names. Its NetBox and Nautobot rack types are exported. The product
  ships as an npm package, `@portrayal/racks-eaton-srw12us`. The SRW12USG
  glass-door build and the caster base are not in this change. This closes no
  row of the conformance records.
