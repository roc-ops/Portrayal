### Added
- Eaton (Tripp Lite series) SmartRack horizontal cable ducts, first slice of #1094 (part of #1091): the
  three 1U finger ducts, modelled as `rack-face` parts from the maker's own spec sheets and, for the
  SRCABLEDUCT1U, its submittal drawing. `eaton/srcableduct1u` (black steel, 482.6 x 43.69 x 67.71 mm
  from the drawing, which settles the conflict with a reseller's 1.77 x 3.9 x 19.13 in);
  `eaton/srcableduct1uhd` (the high capacity duct with a dual-hinge cover, sized from the spec sheet's
  inch row, whose centimetre row disagrees) and `eaton/srcableduct1ufc` (the yellow fibre, copper and
  coax duct with a snap-on cover and two pass-through windows in the rear, placed on the front or the
  rear face). Each has a `duct` guide with the counted finger pitch and gap, a slotted wall along the top
  and along the bottom with the fingers standing on the plate, and a cover that ships fitted and comes
  off in a `cover-off` configuration; the cover is a lid and no hinge is invented. Colour is a `finish`
  field the `base` configuration sets, so the yellow follows the kit's field and reads on both stages.
  No cable capacity or bend radius is recorded: no document states one. The 6 ft vertical
  SRCABLEDUCTVRT waits for the zero-U channel it hangs on.
