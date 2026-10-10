### Added
- **A ring says what of its loop is solid** (#968, `docs/cable-lay-design.md`
  section 3.3): `guide` gains `wall` (each leg beside the opening), `height`
  (the top of the loop over its base) and `slit` (`[from, to]`, the gap in
  the far leg of an open loop). They compile to `data-guide-wall`,
  `data-guide-height` and `data-guide-slit`, and L138 holds each inside the
  part. A sheet part's `solids` in rack.json now carry each such ring's legs,
  bar, seat and hook as `ring/<id>/<part>`. The schema's recorded shape and
  L138's rule text are re-recorded.
- **fs/d-ring-snap-in@1 1.3.0** states them: legs 5.8, the loop 41 high,
  the slit 28.6 to 30.8 mm over the tray. **fs/fhd-cmp5dr 1.1.1**.

### Changed
- **A ring is solid, and a route enters it through its opening**
  (`@portrayal/kit` 0.15.0, #968). `solidsOf` places a ring's parts with the
  other solids; `legCrossings` and `detour` meet them with the cable's tube,
  the part grown by its radius, so a leg that would graze a leg or the bar is
  gone round. A zero-U part (a PDU in the gutter) is met by the tube too, so
  a leg to the lane beside it never runs across its outlet face. Every pass through a ring whose opening is placed starts and
  ends at an approach point on the run outside the band, the cable's radius
  and `CLEAR` past it (`at: 'approach'`), so a detour or a leg from behind or
  below ends there and the cable enters along the run; a ring a route would
  double back at is gone to as far as that point (the path's `face` point,
  where the ring's own `face` stays on the band). `bodyFindings` names the
  part ("ring 3 front leg") and says to "route it into the ring along its
  run, through its opening". **ONE-WAY: routed lengths change on saved
  racks.** On the owner's rack of #949 the upper leaf's cords grow 10 to 38
  mm (five now go over their ring to the approach point on its far side) and
  the lower leaf's 2 to 6 mm; c2 and c3 pass the 0.5 m stock break. On a
  sample of 3,120 generated cables, lengths move from 89 mm shorter to 131
  mm longer (median 10 mm longer), 67 stock sizes up and 67 down. A saved rack's routed lengths
  and stock sizes are re-measured the next time a page measures them; an
  entered length is never touched.

### Fixed
- **The snap-in ring's relief agrees with its guide**: each leg was built
  6.8 mm thick in the plane of the loop, which narrowed the drawn opening to
  30.0 mm against the guide's 32.0 and stood a route's sill point 1 mm inside
  the rear leg. The legs are 5.8, as the plan's 43.6 less the opening gives
  and the ring-profile view reads to a pixel. The slit, re-read, is 2.2 mm
  where 3.8 had been read, in the relief and in fs/fhd-cmp5dr-profile@1
  1.0.1's side view.
