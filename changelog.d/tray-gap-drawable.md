### Fixed
- **A cord is taken up through a tray's gap only where it can be drawn
  through it** (fixes #1185, `kit/rack/solids.js` `gapWays`,
  `kit/rack/route.js`; docs/cable-lay-design.md 1.3). The cord leaves its plug
  straight, to the reach point, and turns onto the rise with a bend of at least
  its cable type's minimum radius, all clear of the tray's floor plate; where
  the rise cannot stand that far beyond the reach point, the automatic route
  keeps the tray's front edge. **One-way: the gap is no longer taken where the
  bend cannot fit, and #1185's expectation for its reference cord c2 changes.**
  The FHD-CMP5DR reference rack's c2 goes round the front edge again (483.6 to
  610.6 mm, stock 0.5 to 1 m). A route that uses no gap is as it was; the
  general bend check still takes a plug's reach point as an ordinary corner
  (a known limitation, P-0218).
