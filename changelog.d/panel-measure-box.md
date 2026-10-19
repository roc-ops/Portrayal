### Added
- `panel_measure.measure()` takes `box=(x0, y0, x1, y1)`, the face's bounds in
  image pixels, in place of `plate()`'s search for the widest dark band. The
  scale is the box's width against the face's known width, and the height check
  still refuses a box whose height misses the face's; a box outside the image or
  with no area is refused. Without `box` nothing changes (#247).
