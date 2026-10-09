### Added
- Solid bodies and the `crosses-body` finding, step 2 of the cable lay
  (#949; `docs/cable-lay-design.md` section 1). `rack.json` gains `solids`
  per device where a device is not simply its envelope, derived by
  `rack_index.py` (through the new `rack_solids.py`) from the compiled faces of
  its default configuration and never stated in a manifest: a sheet part is
  its plates (the floor of each well, each node that stands proud of it, each
  ear its plan draws; never a ring, and never a duct's fingers or clips); a
  zero-U part that carries a lane is its walls and back; a device with cable
  space inside its envelope (a plan that marks a pathway) is its shell walls,
  its patch plate, the modules seated behind it and the plates inside. Each box
  is `{part, box: {x, y, z, w, h, d}, holes?: [{via, box, size}]}`, x from the
  device's left as seen from its front, y up from its bottom, z back from its
  front; a hole is a declared pass-through. A plain box device carries none.
  The FHD-CMP5DR, the FS D-ring panels, finger ducts and vertical ducts gain
  `solids`; no device in the library declares cable space inside its envelope
  yet. `format` stays 1.
- `@portrayal/kit` 0.11.0: a new module, `@portrayal/kit/rack/solids`
  (`solidsOf`, `legCrossings`, `pathCrossings`, `inside`, `detour`, `CLEAR`,
  `POST_D`, `partText`, `isFloor`), and in `rack/route.js` `bodyFindings` and
  `cableDiameter`. `routePath` returns `crossings` and `detours`; `inspect` of
  a cable returns `route.crosses`; `describe` with a route context adds a line
  "Findings: N cables cross a body."; `cableScheduleRows` takes `{bodies}` and
  writes each finding's sentence into its cable's notes. A cable crosses a body
  only through a ring, a duct, or a pass-through whose smaller side fits its
  diameter; a tie slot is never an opening, and a cable lying against a plate
  (its centre line a radius outside it, on either face) is not crossing it.
  The finding warns and never refuses.

### Changed
- **Routed lengths change** wherever a straight leg of a route would cross a
  solid body: `routePath` adds two detour points there (over the near edge,
  else round the end, else by a side lane), which count in the measured length
  and are never stored. A saved rack's routed lengths and stock sizes are
  re-measured the next time a page measures them; an entered length is never
  touched. A sheet part read from an older `rack.json`, without `solids`, is
  open, as every sheet part was before.
