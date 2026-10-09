### Added
- Solid bodies and the `crosses-body` finding, step 2 of the cable lay
  (#949; `docs/cable-lay-design.md` section 1). `rack.json` gains `solids`
  for a sheet part and for a zero-U part that carries a lane, derived by
  `rack_index.py` (through the new `rack_solids.py`) from the compiled faces of
  its default configuration and never stated in a manifest: a sheet part is
  its plates (the floor of each well and each node that stands proud of it;
  never a ring, never drawn decor, and never anything inside a duct's
  footprint or mounted on a duct); a lane duct is what is left, its walls and
  back. Each box is `{part, box: {x, y, z, w, h, d}, holes?: [{via, box,
  size}]}`, x from the device's left as seen from its front, y up from its
  bottom, z back from its front; a hole is a declared pass-through. Any other
  device carries none and is its envelope; a device with cable space inside
  its envelope (the FHD enclosures) waits for step 6 of the note. The
  FHD-CMP5DR and the FS D-ring panels, finger ducts and vertical ducts gain
  `solids`. `format` stays 1.
- `@portrayal/kit` 0.11.0: a new module, `@portrayal/kit/rack/solids`
  (`solidsOf`, `legCrossings`, `detour`, `CLEAR`), and `bodyFindings` in
  `rack/route.js`. `routePath` returns `crossings` and `detours`; `inspect` of
  a cable returns `route.crosses`; `describe` with a route context adds a line
  "Findings: N cables cross a body."; `cableScheduleRows` takes `{bodies}` and
  writes each finding's sentence into its cable's notes. A cable crosses a body
  only through a ring, a duct, or a pass-through whose smaller side fits its
  diameter (`ctx.diameterOf`, else its media's); a tie slot is never an
  opening, and a cable lying against a plate (its centre line a radius
  outside it, on either face) is not crossing it. The finding warns and never
  refuses.

### Changed
- **Routed lengths change** wherever a straight leg of a route would cross a
  solid body: `routePath` adds detour points there (over the near edge, a
  tray's front edge first; else round the end; else by a side lane; a detour
  that meets a second body goes round it too), which count in the measured
  length and are never stored. Most of the change is a cable from a port on a
  device's far panel, which now goes round its own device to the lane: on a
  two-post rack most rear routes, on a four-post few. A saved rack's routed
  lengths and stock sizes are re-measured the next time a page measures them;
  an entered length is never touched. A sheet part read from an older
  `rack.json`, without `solids`, is open, as every sheet part was before.
- **A zero-U part that stands in the gutter and carries no lane** (a zero-U
  PDU) moves the cable lane beside its upright outboard of it, at the units it
  spans (`laneXAt`): the lane runs in a gutter as wide as the usual one just
  outside the PDU, so a cable runs beside it and not through it, and a port
  leg to that lane goes round the PDU on its back, the side facing into the
  rack, never over its outlet face. On a sample 42U rack with a 52 x 65 mm
  zero-U PDU, a route on that lane grew by 13 to 164 mm (median 63) on a
  four-post with the PDU on a rear upright, and by up to 421 mm (median 202)
  on a two-post.
