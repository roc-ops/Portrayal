### Fixed
- **A body piece that shows a drawing paints it properly.** The clear areas
  of a plan, rear or side drawing were painted black on the piece, because the
  material had no alpha handling; it now has the handling the kit's other
  canvas materials have, so those areas are cut away. The crop is read under
  clamped wrapping, so a crop that reaches the drawing's edge no longer
  bleeds the opposite edge in. A drawing that will not load is reported once
  for the build, not once for each piece that shows it.
- **The standalone part view no longer draws an empty frame** while the art of
  a part's pieces loads: it resolves every piece's art, then replaces the
  scene.
- **A piece on a face drawn `flipLX` or `flipLY` is a plain box.** A piece's
  `axis` and `shows` are in the part's own frame, so a piece in a bay that
  turns, mirrors or tilts its occupant is built as the plain box it would have
  been without either key; a mirrored face was judged straight and placed its
  art mirrored, and now falls back the same way. `pieceIsStraight` takes the
  face's `[flipLX, flipLY]` as a third argument.

### Changed
- **L71 asks that a piece lies inside the drawing it shows.** A piece that
  shows `plan` or `rear` has to lie inside that part's size, as one that shows
  a side already had to lie inside its viewBox, and an `axis` outside `x`, `y`
  and `z` is a finding. No part in the library changes.
