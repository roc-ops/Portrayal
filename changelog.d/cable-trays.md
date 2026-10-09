### Added
- **Trays: a floor a cable lies on** (#949, `docs/cable-lay-design.md`
  section 2). A component contract declares `tray:` (its `floor`
  rectangles, the `height` of the floor's top above the bottom of the
  envelope, `lip`, `run`, the tie slots cut in it as `ties`, and `slack`,
  `area` or a `spool`), so every placement of the part carries it; a device
  plan (its top view, and no other) declares `trays:` by id. Each compiles to unpainted
  `data-class="tray"` and `data-class="tie"` rects, and `rack.json` carries
  each device's `trays` in the frame of its `solids`, with the openings of the
  rings standing on the floor. A route names a tray by its id, as it names a
  ring. L170 holds a floor inside its part or view, each tie slot on a floor,
  a tray's id to one pathway, its height to the depth of its well, and its
  ties to the slots the device draws on its bottom view. The schema's
  recorded shape is re-recorded: the component and device schemas now accept
  `tray` and `trays`.
- **A ring places its opening**: `guide` gains `depth` (along the run),
  `sill` (from the base it stands on to the lowest inside edge of the
  opening) and `aperture.at` (the opening's corner on the drawing). They
  compile to `data-guide-depth`, `data-guide-sill` and
  `data-guide-aperture-at`. L138 holds each inside the part.
- **fs/fhd-cmp5dr-tray@1 1.1.0** states its tray: the strip and its two arms,
  3.0 mm up the envelope, no lip, the sixteen slots as ties, slack as area.
  **fs/d-ring-snap-in@1 1.2.0** states its opening: 6.8 mm along the tray, its
  sill 5.6 mm above the floor (read off the ring-profile view, where 2 mm was
  estimated before), its corner at 12.75, 5.8. **fs/fhd-cmp5dr 1.1.0**.

### Changed
- **Cables rest** (`@portrayal/kit` 0.14.0, #949, `docs/cable-lay-design.md`
  section 3). A ring on a tray holds a cable on its sill, its radius above
  the opening's lowest inside edge as mounted, at the side nearer the rail; a
  route through a tray lays the cable on the floor at its radius, or, where
  the page pins it (`ctx.trayFaceOf`) and the tray has tie slots, strapped
  under the plate, sagging between two straps no lower than the strap line;
  every other free span hangs by the 3D drawing's catenary scaled by the
  `DRAPE` of its family (fibre and AOC 1, twisted pair 0.5, DAC and power
  0.35) and no tighter than its installed bend radius allows, and lands on
  any surface it would pass below. `routePath` gains points `at: 'tray'` and
  `at: 'rest'` and a list of `rests`, which `inspect` gives as
  `route.rests`; `solids.js` gains `traysOf`. **ONE-WAY: routed lengths
  change on saved racks.** On the owner's rack of #949 the upper leaf's cords
  grow 34 to 42 mm and the lower leaf's 125 to 144 mm (they now go round the
  tray's front edge to reach a ring on its sill), and thirteen of sixteen
  measure past the 0.5 m stock break where seven did; a free span to a
  gutter, or an unrouted jumper, grows by its hang. A saved rack's routed
  lengths and stock sizes are re-measured the next time a page measures
  them; an entered length is never touched.
- The `cable.route` refusal names trays among what a device offers ("has no
  ring, duct, pass-through or tray called ...").
- **Rule 7 of the modelling guide is narrowed**: cable management that is
  part of the product (a lacer and its rings, a tray, a spool, a bend-radius
  bracket) is declared, and drawn where it is a part, with the tie slots cut
  in a plate declared as `ties`; accessories added in the field (loose ties,
  straps, retainer bails) stay undrawn.
