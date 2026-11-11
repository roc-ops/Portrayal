### Fixed
- **Nokia FGLT-D, FGUT-A and NGLT-C 1.4.2 no longer cut printed art or run past
  their last window in 3D.** Each card's `well` pocket now ends at the bottom
  of its last window (FGLT-D 361.83 mm, it ran to 366.99 over the tips of the
  two hazard triangles; FGUT-A 359.53 mm, it ran to 364.65 over the same
  triangles; NGLT-C 204.32 mm, it ran to 214.7 over bare plate) and states the
  plate's back face as `wall`, so the lowest cage runs back under the plate's
  edge without coming out through a wall. The FGLT-D reads 13.5 mm and the
  FGUT-A 13.0 mm from the card's own side elevation in the ETSI Unit Data
  Sheets guide (a line at each face of the plate; no dimension line, so both
  stay estimates). No page of the NGLT-C's guides draws its plate edge-on:
  its 12.0 mm is borrowed from the FGLT-B and stays an estimate. The wedge
  below each last window (`return-16`, `return-16`, `return-4`) is no longer a
  facet: it lay outside the window, in the plate's thickness. In 2D only the
  pocket's hairline outline below the last window changes. The shelves that
  seat the cards take a patch each: Nokia 7360 ISAM FX-16 (`nokia/nfxs-d-ba`)
  1.0.5, FX-8 (`nokia/nfxs-e-bb`) 1.0.6 and FX-4 (`nokia/nfxs-f-bb`) 1.0.5. The
  NGLT-A follows separately. No record of the conformance list is closed.
