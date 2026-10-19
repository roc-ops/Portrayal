### Changed
- **A DAC's or an AOC's plug is rigid: a turn at its end has no leg in the
  plug, so the cable runs on straight before it turns** (#985,
  `kit/rack/route.js`, `kit/rack/route-path.js`). The bend measure counted a
  plug's whole reach as a leg a bend could use. Amphenol C-NDAAFR-0099 says the
  cable needs 45 mm after the head before it may bend, boot included, so the
  64.8 mm reach of a DAC or AOC is all rigid (`PLUG_SPLIT`, beside
  `PLUG_REACH`): a corner at the reach point has no room, and the first turn
  starts at a lead point past it. A route point `at: 'reach'` gains `rigid_mm`
  for such a plug, and `cornersOf` measures the leg into the first corner (and
  out of the last) from where the rigid part ends. **Saved racks' routed
  lengths, stock sizes and bend findings for DAC and AOC cords change at their
  next measure.** LC, copper RJ45 and power are "not split yet" and measure as
  before, as does any plug whose reach the page gives as a number
  (`plugReachOf`), which cannot say it is rigid.
