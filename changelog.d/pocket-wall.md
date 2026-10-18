### Added
- **A relief `pocket` may state the thickness of the plate it is cut through**
  (#554): `pocket: {depth, wall}`, with `0 < wall < depth`. The walls stop at
  `wall`, the plate's back face; the floor stays at `depth`, and below the wall
  the pocket is open to the inside of the part, so a cage near a window's end
  may run back under the plate's solid edge. A plain number, `pocket: 28.38`,
  keeps its meaning (walls to the floor), and every existing pocket builds as
  it did. **This is one-way:** the wall is published as a new attribute,
  `data-wall-depth`, beside `data-depth` (`data-wall` is the walls' colour), and
  the schema's `pocket` is now a number or an object.
- **L117 checks a walled pocket**: `wall` must be shallower than `depth`, and a
  part on a sunk facet in the pocket may run out of the pocket's box only below
  the wall depth, never above it. A pocket with no `wall` checks nothing of its
  parts, as before.
- **The kit builds a walled pocket's walls to `wall` only** (`kit/relief.js`),
  and skirts a sunk tooth's side from its base up to the plate where the plate
  ends. `kit/swap.js` carries the attribute with the other pocket attributes.

### Fixed
- **Nokia FGLT-A 1.4.2 no longer cuts the barcode label in 3D.** Its `well`
  pocket now ends at the bottom of window 8 (355.6 mm, it ran to 366.65 over
  the label's top 6.5 mm) and states the plate's back face as `wall: 12.0`,
  so the lowest cage runs back under the plate's edge without coming out
  through a wall. 12.0 mm is the FGLT-B's measured plate depth, taken as an
  estimate for this card. `return-8`, the wedge behind the bar below window 8,
  is no longer a facet: it lay outside the window and the plate hides it from
  the front. The 2D drawing is unchanged. The shelves that seat it take a
  patch each: Nokia 7360 ISAM FX-16 (`nokia/nfxs-d-ba`) 1.0.2, FX-8
  (`nokia/nfxs-e-bb`) 1.0.2 and FX-4 (`nokia/nfxs-f-bb`) 1.0.2. The other
  walled-window cards (FGLT-B, FGLT-D, FGUT-A, NGLT-C) follow separately.
