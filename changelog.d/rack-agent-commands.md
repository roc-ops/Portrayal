### Added
- `@portrayal/kit` 0.4.0: `@portrayal/kit/rack` has commands and questions
  an agent can use without reading the code
  (`docs/rack-agent-commands-design.md`). `fit` seats, empties
  or restores one bay or cage; `field` sets one setting of one seated part;
  `cable.update` takes `a` and `b` to move an end and keep the cable.
  `cable.route` refuses a waypoint the rack lacks and judges only the new ones.
  `inspect` reads one device's bays, cages and part settings, or one cable's
  ends, route, routed length, slack and loose ends; `selectCables` turns "the
  cables on this device" or "every loose cable" into ids (saying when some ends
  could not be checked); `describe` takes a
  window (`section`, `offset`, `limit`); `catalog` filters by `kind`.
  `loadSlots(dist, refs)` in `rack/catalog.js` loads the parts lists that
  `editor.apply(cmds, {ctx})` and `editor.preview(cmds, {ctx})` check against,
  for that call only.
- `rack.json` gives every device a `kind`, a plain word for what it is
  (`switch`, `router`, `patch panel`, `cable manager`, `server`, `pdu`, ...),
  and `devices.json` carries each device's `profile`, which `kind` is read
  from. Both are additive: `rack.json` stays `format` 1 and `devices.json`
  stays `contract: 2`.
### Changed
- `patch` with a new `cfg` and no `swaps` or `fields` clears both. With parts
  lists loaded, `place` and `patch` refuse a configuration the device does not
  list, and `patch {swaps}` leaves out, and names, what a slot does not take.
- `describe` starts with a totals line (`Rack 1 (r1): 6 items, 40 cables.`);
  the frame follows on its own line.
- The command descriptions name no function and no page: `describe()`,
  `freePorts()`, `catalog()` and the Explorer are gone from them.
