### Changed
- **A cable that comes up from a device below a cable manager may rise through
  the open gap between the tray's floor and its rail, where it went round the
  tray's front edge** (#966, `kit/rack/solids.js`,
  `kit/rack/route.js`; docs/cable-lay-design.md 1.3). The router finds the gap
  from the floor boxes the tray publishes (`gapsOf`) and takes it, or the
  front edge, by length after the installed bend radius; a cable or bundle
  wider than the gap keeps the front edge, and a hand-edited route never
  uses the gap (no leg of it, those between its waypoints too, is offered
  one; nor is a bundle with a written trunk or a hand-edited member). It is
  used by the automatic route only: no saved key points at it.
  **Saved racks' routed lengths, stock sizes and everything read off them
  change for a cord that now rises through a gap** (on the FHD-CMP5DR
  reference rack, five of the lower leaf's eight cords, 122 to 198 mm shorter).
