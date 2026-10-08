### Changed
- `@portrayal/kit` 0.5.0: a routed cable passes THROUGH a D-ring along the
  ring's `run`, not to a point inside it (#930). Each ring waypoint becomes
  the point where the cable enters, on the side of the point before it, and
  the point where it leaves, half the ring's `depth` either side of its centre,
  with a straight run between them. A ring that states no depth is taken as
  `RING_DEPTH`, 10 mm, marked estimated. The new `routePath(rack, cable, ctx)`
  is that path, and `routedLength`, `fill` and `inspect` (`route.rings`) read
  it; `routed2d` and `routePoints3d` take the rings as an optional last
  argument and round their corners outside the ring (`throughRings` in
  `rack/route-path.js`). A route that would enter and leave a ring by one face
  is not drawn through it, is counted neither in that ring's fill nor in its
  manager's capacity, and is reported by `ringFindings(rack, ctx)`; a point
  steeper than 45 degrees off the run (a port below the ring) stands on
  neither side. `pathLength(path)` measures a `routePath`. The automatic route takes only the rings on the
  way from the port to its gutter, no longer a ring behind the port.
  **Routed lengths change**: a ring adds up to its depth, and a cable whose
  automatic route used to double back through a ring is up to about 100 mm
  shorter. Stored routed lengths are re-measured the next time a page
  measures them; an entered length is never touched. Ducts and pass-throughs
  keep a single point. The Rack Builder's half (re-vendoring, passing `run`
  and the ring marks to the drawings, showing the findings) is listed in
  `docs/cable-managers-design.md` section 13.
