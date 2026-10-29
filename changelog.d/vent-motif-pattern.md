### Added
- A decor rect can draw its own vent tile: `pattern: motif`, with `pattern-cells`, the dark cells of one tile
  as closed polygons of three or more `[x, y]` points in mm from the tile's top-left corner, and
  `pattern-pitch`, which is required with `motif` and IS the tile (`[w, h]` in mm; nothing is scaled). It is
  for a vent whose openings no fixed tile draws: slanted slots, alternating chevrons, slots woven at plus and
  minus 45 degrees. Each cell is filled with the dark of the `vent` pattern's cells and has no stroke; a rect
  with the same cells and pitch shares one `<pattern>`, `pattern-offset` shifts its phase without scaling it,
  and `vent:` still makes the rect an air aperture. Additive to format 1; `vent` stays the hexagon lattice and
  no existing drawing changes. What validates differently: `pattern: motif` without `pattern-cells` and
  `pattern-pitch` is refused, and so is `pattern-cells` on any other pattern. A point outside the tile is
  refused by the renderer, which names the rect.
