### Fixed
- **A rack device's shell grommet is judged on the cable's tube, not its
  centre line** (`kit/rack/solids.js`). The grommet's box is taken less the
  cable's radius across the hole, as a zero-U part's hole already is, so a
  6 mm cable whose centre is 2 mm inside the edge now crosses the wall instead
  of passing with a third of its tube in it. A cable as wide as the grommet's
  smaller side still passes through the middle. A route through a shell
  grommet, and its length with it, can change on saved racks.
