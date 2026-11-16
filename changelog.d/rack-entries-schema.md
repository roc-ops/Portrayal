### Added
- A rack product can state `enclosure.entries`: the places a cable may leave the rack (#1299).
  Each entry has an `id`, a `where` (`roof`, `floor`, `left` or `right`) and a `kind`
  (`brush`, `knockout`, `cutout` or `open`). It may have a `box` and a `source`.
  The id `any` is reserved. An `open` entry with no `box` is the whole part of `outer`.
  L193 holds each id once, each box inside `outer`, and an `outer` for an open entry with no box.
  An open frame may state `entries` alone; doors, panels and a roof stay on cabinets.
  `rack.json` `frames` carries the entries of a product that states them.
  `apc/ar201` and `apc/ar203a` state their open `top` and take version 1.1.0.
