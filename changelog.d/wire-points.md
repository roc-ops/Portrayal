### Added
- **`cablePoints(svg, 'wire')` and `wirePoints(svg)` read the wires of a plug**
  (`kit/relief.js`, #805). A terminal plug leaves by one wire per pole, as the
  connection points `wire-1` to `wire-N`, and `cablePoints(svg)` reads only the
  points named `cable`, so no wire could be found. The new kind returns one
  point per wire, resolved as a cable point is (position, direction, the
  feature it sits on, the seat chain), each carrying its number as `wire`, a
  plug's wires together and in number order. `cablePoints(svg)` without a kind
  is unchanged and still returns the `cable` points only. Nothing routes a wire
  yet, and what a wire is in the cable model (a cable of its own or a conductor
  of one cable) is not decided by this.
