### Added
- **A housing with a stepped end.** `chassis.section` states the end profile of a cast or
  extruded housing as a closed polygon of `[x, y]` points in the right end face's frame: the
  outline of the whole housing, clockwise with y down, every edge horizontal or vertical,
  touching all four sides of the `depth` by `height` box with one edge on the top and one on the
  bottom. The right face is drawn as the polygon and the left face as its mirror, each with
  transparent corners, and keeps the id `chassis-faceplate` as a `<path>`; the front, rear, top and
  bottom are drawn as before. Lint L204 to L207 check the polygon, the box, the mounts and keys it
  cannot go with (a rack device, `bevel`, `rounded`, `shell: sheet`, `ears`, `overhang`, `kits`
  and `halves`) and the parts on an end, top or bottom face. The lock reads `section` as shape,
  like `bevel` and `rounded`: stating it on a released device is a major. `<device>.configs.json`
  carries `chassis.section`. The key is additive: every file valid before stays valid, a device
  that does not state it builds byte for byte as it did, and `contract` stays 2. A validator
  holding the earlier schema refuses a file that states it. Ribs, the 3D body and the open state
  of such a housing are later changes. This closes no row.
