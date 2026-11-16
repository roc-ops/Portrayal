### Added
- **A housing seen from above.** `chassis.plan-outline` states the outline of a housing seen
  from above, which the end profile cannot give because it runs the whole width and so always
  makes a rectangle. It is a list of bands; each band is a range of heights down from the top and
  a closed polygon of `[x, y]` points in the top face's frame (x along the width from the left,
  y down the drawing with the rear at the top), clockwise with y down. The bands tile the height,
  slanted edges are allowed (a rounded corner is its arc in short steps, a lobe is its points),
  and a band has at most 512 points, a device at most 16 bands and 2048 points. The section is
  the most the housing can be and the plan only removes from it. Lint L220 to L225 check that a
  section is stated, the mounts and keys it cannot go with (a rack device, `bevel`, `rounded`,
  `shell: sheet`, `ears`, `overhang`, `kits`), that the bands tile, that each polygon is simple and
  clockwise with no edge under 0.1 mm, the caps, and that every polygon lies inside the box. The
  lock reads the key as shape, like `section`: stating it on a released device is a major.
  `<device>.configs.json` carries `chassis.plan-outline` as written. The key is additive and a
  device that does not state it builds byte for byte as it did; `contract` stays 2. A validator
  holding the earlier schema refuses a file that states it. Nothing is drawn or built from it
  yet, so no library device states it, and a test fails if one does. This closes no row.
