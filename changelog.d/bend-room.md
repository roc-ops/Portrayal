### Added
- **A routed cable's tight bends are a finding** (`@portrayal/kit` 0.17.0,
  #973; `docs/cable-lay-design.md` section 3.4). `routePath` returns `bends`,
  each corner of the path with less room than the cable's own installed bend
  radius (`ctx.bendOf(cable)`, else its media's), as `{kind: 'tight-bend',
  cable, point, between, at, angle_deg, legs_mm, room_mm, need_mm,
  short_mm}`, and `bendFindings(rack, ctx, nameOf)` gives them rack-wide with
  a sentence. `cornersOf` and `STRAIGHT_DEG` move to `rack/route-path.js`
  (`rack/bundles.js` still exports both), and `cornersOf(points, {share:
  'need'})` shares a leg between its two corners by what each turn uses of
  it, not by halves; the bundle check keeps the halves. `detour` in
  `rack/solids.js` takes `room`. A path point can be `at: 'lead'`.

### Changed
- **A routed path leaves every turn room for the cable's bend radius**
  (`@portrayal/kit` 0.17.0, #973). On the owner's rack of #949, 86 corners of
  the sixteen paths had less room than OM4's 25 mm, and almost none was a
  real bend. A free span is now sampled evenly along its arc, a landing is
  laid as the tangent points of its two bends, and no hang is laid that
  leaves a corner short of the radius; an approach point stands the bend
  radius from its ring's band where the route turns there, and a cable from
  behind it is led square to it through a lead point; each move to a
  detour's plane is two bend radii long; and a cable whose first turn needs
  more leg than its plug gives runs on straight out of it. None of the 86 is
  left. What the kit's rules find no room for is still routed, and reported.
  **ONE-WAY: routed lengths change on saved racks.** On the owner's rack
  every cord is 10.9 to 179.2 mm longer and seven of the sixteen move from
  0.5 m to 1 m (c1 to c3 and c5 to c8; c4 stays 0.5 m, the lower leaf's
  eight stay 1 m). On one sample of 60 generated racks (1,803 cables of
  mixed media, `spec/tests/js/bend-room-sample.mjs`) a length moves by 113
  mm shorter to 297 mm longer, median 14 mm longer, 93 stock sizes up and 34
  down, and the corners short of their radius fall from 22,910 to 959, each
  a bend the kit's rules found no room for. A cable written the other way
  round does not always lay the same: 38 of those 1,803 measure differently
  from the other end (19 before), and 9 report a different number of bends.
  No cable runs in front of a zero-U part's outward face that did not
  before.
  A saved
  rack's routed lengths and stock sizes are re-measured the next time a page
  measures them; an entered length is never touched.
