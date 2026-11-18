### Fixed
- In the 3D view, a card plane on a flipped face (the underside) now reads the card's own art
  wherever the card stands. The plane was cut at the card's drawing rect. A flipped face has
  mirrored its canvas, so an off-centre card showed the face background. The rect is now
  mirrored on the face first. A centred card is its own mirror and is unchanged.
- A card plane on a flipped face keeps its orientation when a lamp, field or state is written
  on the card. The plane was cut again upright and turned over on the first write. The re-cut is
  now turned as the first cut is.
- A shape punch is a cavity or a seated module's shape. On an open-backed card's plane on a
  flipped face it is now mirrored within the plane, with its art turned. It was cut at its
  drawing coordinates and left the real pocket shut. A flat face and every other punch are unchanged (#1811).
