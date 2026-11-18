### Added
- Kit: `routeToExit(rack, cable, ctx)` in `rack/route.js` routes a cable stored outside the rack.
  It runs from a port to an entry of the rack's product, named `{exit: id}` or taken as
  `{exit: 'any'}`. It returns `inRack` in mm, the entry taken, where the route ends and the rings
  and ducts it passes. With no length to give, `inRack` is null and `reason` says why (#1299).
- Kit: `ctx.outside`, a list of such cables. A port one of them has reads taken in `portFree`
  and `freePorts`. `fill` counts each ring or duct its route passes once, by its media's diameter.
  The rack file never holds them, and an absent `outside` is not an empty one (#1299).

### Changed
- Kit: when `ctx.outside` is absent, `describe` ends with one more line. It says that cables
  stored outside the rack are not passed in, and the ports they use read free.
  A caller that shows the description shows that line after it takes this kit.
  `capacityOver` does not read `outside` yet (#1299).
