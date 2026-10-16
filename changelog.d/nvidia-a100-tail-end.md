### Added
- The tail end of `nvidia/a100-pcie-80gb@1`: the shroud is open at its far end
  with 18 heat-sink fins edge-on on a 5.0 pitch, the CPU 8-pin power connector
  stands at the corner by the top edge in a black housing, and two bosses take
  the thumbscrews of the straight or long offset extender. The card declares
  the connector as the `aux-power` port of its new rear face,
  `nvidia/a100-pcie-80gb-tail@1`. The port is a stand-in,
  `nvidia/a100-eps12v-standin@1`, that presents no interface; it is swapped
  for `std/eps12v-header@1` once that part and its `eps12v-8pin` interface
  are in the library.

### Changed
- `nvidia/a100-pcie-80gb@1`'s extender upright is a flat strip, 1.2 thick,
  like the rest of its plate, where it had stood 8.4 tall. It stops short of
  the 8-pin connector in x, so neither extender's strip cuts the connector's
  lower row from behind, and the connector housing is 10.85 high so its
  bottom is not in the plane of the cover's, which shimmered in 3D.
- `portrayal-lint` L71 refuses two body boxes that share a face plane where
  they overlap (they z-fight in 3D).
