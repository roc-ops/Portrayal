### Changed
- **StarTech.com 4POSTRACK42 (`startech/4postrack42`, 1.0.0 to 2.0.0): the rear rail sets in one-inch steps** (#1109).
  The maker's user manual (revision 11/16/2023) has a Mounting Depth Chart that lists every inch from 22 to 40 in, so the
  rear rail's depth is now 558.8 to 1016.0 mm in 25.4 mm steps, and the Rack Builder offers those 19 settings instead of
  any depth in the range. A step on a rail is a figure a saved rack copies, so this is a major version: a saved rack that
  names `startech/4postrack42@1` keeps the range without a step. The product's sources are now the maker's data sheet and
  user manual; its outer box, weight and loads are unchanged. The manual prints a different size, 600 x 2045 x 662 mm
  (width, height, depth), from the data sheet's 80.3 in with casters and 3.7 ft length: the `outer-size` gap states
  what each prints and nothing is averaged. The description now names the 24 cable management hooks that screw on along
  the back, the grounding hole inside the base and its four grounding wires, with a `cable-management` gap because the
  rack product has no key for them. No export file changes: the rack type exports carry the outer box and loads and not
  the depth range.
