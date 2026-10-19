### Fixed
- **A zero-U part's pass-through hole is judged on the cable's tube, not its
  centre line** (#992, `kit/rack/solids.js`). The hole's box is taken less the
  cable's radius across the hole, so a 6 mm cable whose centre is 2 mm inside
  the edge now crosses the plate instead of passing with a third of its tube
  in the wall. The box is not shortened along the way through the plate. A
  route through a pass-through hole can change, and its length with it, on
  saved racks. The design note says a tube touching a plate the cable rests on
  is contact, not a fault.
