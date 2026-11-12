### Fixed
- In the 3D view, a card plane in an open-backed bay on a flipped face (the
  underside) is cut under a tilted facet's footprint where the wedge stands. The
  plane is cut from the face canvas, which a flipped face has mirrored, and the
  clear was replayed on it unmirrored, so the hole sat beside the wedge and the
  plane still cut across its cage wells. The clear is now mirrored within the
  plane's own rect, as the pocket-floor clear already is. A flat face, a plane
  that is not open-backed and every other punch are unchanged. A plane that is
  restyled afterwards (a lamp, field or state written on the card) is cut again
  from an unflipped raster and still shows the clear in its authored place (#551).
