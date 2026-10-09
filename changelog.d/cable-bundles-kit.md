### Added
- `@portrayal/kit` 0.7.0: cable bundles in the rack kit (#921,
  `docs/cable-bundles-design.md`). A rack's optional `bundles` holds cables
  combed into one run along a stored trunk, `{id, number, label, members:
  [{cable, a?, b?}], route, straps?}`; membership lives on the bundle only.
  `bundle.create`, `bundle.add`, `bundle.peel`, `bundle.update` and
  `bundle.remove` make and change them, each one undo step, with `{error}`
  refusals; with the routing context (`ctx.route`) `bundle.create` works the
  trunk out from where its cables run together and refuses a fork, a loop, a
  detour or groups that share nothing by name. `resolveRoute` follows a
  member's bundle and names its `bundle`, `join` and `leave`. A new module,
  `@portrayal/kit/rack/bundles` (with `@portrayal/kit/rack/bundle-route`),
  checks a bundle's size against the smaller of 2.5 in and each opening on
  its trunk (`bundleCheck`, `bundleChecks`, `pathwaysOn`; a duct running up a
  part and a duct beside the rack are estimated from their channel and depth),
  warning and never refusing, and places its straps every 12 in unless it
  says otherwise (`straps`). `inspect`, `describe` and `selectCables` know
  bundles; `BUNDLE_GONE` joins `GONE` and `CABLE_GONE`.
- `parseDoc(input, {notes})` repairs a file's bundles (an id another thing has,
  a member naming no cable, a cable in two bundles, a number used twice) and
  says so in `notes`, one sentence per repair naming its rack;
  `editor.loadDoc(doc, {notes})` returns them first in its `findings`.

### Changed
- **The rack file is `version` 3, a one-way change.** Migration from 2 is the
  identity, so every version-2 file opens as it was, but a page saves every
  document it opens as version 3, and a page or kit from before 0.7.0 refuses
  a version-3 file rather than opening it and losing its bundles.
  `rack.schema.json` describes version 3 and is published at
  `https://portrayal.dev/schemas/v2/rack.schema.json`; the `/v1/` schema, which
  describes version 2, stays as published (`docs/format-stability.md`).
- **Routed lengths change for a bundled cable**: it is measured along its
  bundle's trunk, not its own route, between where it joins and leaves.
- `cable.remove`, and `remove` with `cables: 'remove'`, take a cable out of its
  bundle in the same step and say so. A new cable's id, and a repaired one, is
  past every id a bundle still names, and an item id a trunk or peel point
  names is not handed to a new device. `cable.route` checks waypoints against
  `ctx.route.guidesOf` when given, and a flat `ctx.guidesOf` otherwise.
  `describe`'s refusal of an unknown section names `bundles`.
