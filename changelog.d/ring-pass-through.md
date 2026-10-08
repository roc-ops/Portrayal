### Changed
- `@portrayal/kit` 0.5.0: a routed cable passes THROUGH a D-ring along the
  ring's `run`, not to a point inside it (#930). Each ring waypoint becomes
  the point where the cable enters, on the side of the point before it, and
  the point where it leaves, half the ring's `depth` either side of its centre,
  with a straight run between them. A ring that states no depth is taken as
  `RING_DEPTH`, 10 mm, marked estimated. The new `routePath(rack, cable, ctx)`
  is that path, and it decides each ring once, in the rack's frame: which way
  through, or not through at all. `routedLength` (`pathLength`), `fill`,
  `capacityOver` and `inspect` (`route.rings`) read it, and `ringMarks(rack,
  cable, ctx)` hands its decisions to the drawings: `routed2d` and
  `routePoints3d` take them as an optional last argument, draw each ring the
  way it was decided, and round their corners outside it (`throughRings` in
  `rack/route-path.js`). A route that would enter and leave a ring by one face
  is not drawn through it, is counted neither in that ring's fill nor in its
  manager's capacity, and is reported by `ringFindings(rack, ctx)`. A point
  further off the run in the face than along it (a port well below the ring)
  stands on neither side; a manager's stand-off out of the face does not
  count. The automatic route takes only the rings on the way from the port to
  its gutter, no longer a ring behind the port.
  **Routed lengths change**: a ring adds up to its depth, and a cable whose
  automatic route used to double back through a ring is up to about 100 mm
  shorter. Stored routed lengths are re-measured the next time a page
  measures them; an entered length is never touched. Ducts and pass-throughs
  keep a single point. The Rack Builder's half (re-vendoring, passing `run`
  and the ring marks to the drawings, showing the findings) is listed in
  `docs/cable-managers-design.md` section 13.
