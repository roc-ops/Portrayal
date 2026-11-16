### Fixed
- **Nokia FGLT-E 1.4.2 no longer cuts the hazard triangles in 3D.** The card's
  `well` pocket now ends at the bottom of its last window (361.12 mm; it ran to
  367.05 over the tips of the ESD and hot-surface triangles, which start at
  365.0) and states the plate's back face as `wall`, so the lowest cage runs
  back under the plate's edge without coming out through a wall. The 12.0 mm
  wall is read from the card's own side elevation in the ETSI Unit Data Sheets
  guide (the centres of the plate's two full-height lines; no dimension line, so
  it stays an estimate). The wedge below the last window (`return-16`) is no
  longer a facet: it lay outside the window, in the plate's thickness. In 2D
  only the pocket's hairline outline below the last window changes. The shelves
  that seat the card take a patch each: Nokia 7360 ISAM FX-16
  (`nokia/nfxs-d-ba`), FX-8 (`nokia/nfxs-e-bb`) and FX-4 (`nokia/nfxs-f-bb`).
  The NGLT-A is not changed: its pocket is the recess its figure draws. No
  record of the conformance list is closed.
