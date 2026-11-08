### Changed
- The five Cisco Catalyst 2960-S fronts (`cisco/ws-c2960s-48fpd`, `-48lpd`, `-48td`, `-24pd` and `-24td`, Refs #1322)
  draw the console end as the model stencils do: the legend band's left end slopes, the dark panel's top-right corner
  is rounded, the console surround steps up over the RJ-45 jack so the second uplink's arrow stands below it on the
  panel, and the mini-B jack's lower corners show the surround's teal instead of the hole's black. No port, lamp or
  group id moves.
- The RPS connector part (`cisco/rps2300-connector@2`, seated by the same five devices) draws the chamfered lower
  corners of its 22 cavities, 0.4 mm across by 0.7 mm down, read off the rear photograph at 3.41 px per mm. The
  five rears pick it up with a patch bump of each device. This closes no gap row: the `rps-connector-part` row of each
  device now lists only the screw slot as undrawn.
