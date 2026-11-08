### Fixed
- **Nokia FGLT-B 1.4.2 no longer cuts the barcode label in 3D.** Its `well`
  pocket now ends at the bottom of window 8 (355.6 mm, it ran to 366.65 over
  the label's top 6.5 mm) and states the plate's back face as `wall: 12.0`,
  so the lowest cage runs back under the plate's edge without coming out
  through a wall. 12.0 mm is read from the card's own side elevation in the
  ETSI Unit Data Sheets guide (41.5 px at 3.457 px/mm) and stays an estimate:
  the figure has no dimension line. `return-8`, the wedge behind the bar below
  window 8, is no longer a facet: it lay outside the window and the plate hides
  it from the front. In 2D only the pocket's hairline outline below window 8
  changes, by a few pixels of grey. The shelves that seat it take
  a patch each: Nokia 7360 ISAM FX-16 (`nokia/nfxs-d-ba`) 1.0.4, FX-8
  (`nokia/nfxs-e-bb`) 1.0.5 and FX-4 (`nokia/nfxs-f-bb`) 1.0.4. The other
  walled-window cards (FGLT-D, FGUT-A, NGLT-C) follow separately.
