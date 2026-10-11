### Added
- **A device can declare a part that slides** (#950, steps 1 to 4 of
  `docs/adjustable-positions-design.md`). A new top-level `adjustments:` map
  states each one: its `label`, the `carrier` placement, the `axis` (`x`, `y`
  or `z`, in the frame of the device), a `range` in mm or named `stops` or
  both, the `default` and a `datum`. A placement, a bay and a decor entry say
  `moves-with: <id>`. Both keys are optional, so `format` stays 1. No library
  device states them yet: the lock asks no device for a bump, and every
  library device builds byte for byte as it did.
- **The compiled drawing says what moves.** On a device that declares an
  adjustment, the root of every face carries `data-adjustments` (the map, with
  `at`, the position the file was built at), and each member node carries
  `data-moves-with` and `data-moves-by="dx dy dz"`, the mm it moves for each mm
  of position. `<device>.configs.json` gains `adjustments` and, on each
  configuration, `positions`; a row of the elements file that moves gains
  `moves-with` and `moves-by`. These are new fields, so `contract` stays 2.
  A configuration may set a position
  (`component-attrs: {<carrier>: {<id>: <value>}}`, a number in mm or the name
  of a stop) and is then built moved. `docs/format-stability.md` has the
  fields.
- **Eleven lint rules, L173 to L183**, for an adjustment: it is well formed;
  its carrier is a placement every configuration has; each `moves-with`
  resolves; what stands on a member moves with it; the default is the position
  drawn; a member stays inside the device and collides with nothing at either
  end of the travel; the id is free on the carrier; a position a configuration
  sets is one the adjustment takes; the range has a `provenance` entry; and an
  attr that restates the adjustment (`<id>-mm`, `<id>-min-mm`, `<id>-max-mm`,
  with any words before the id; `min` or `max` may stand before the id too)
  equals it. All are errors.
- **The lock records each adjustment with its members.** Stating one at the
  position drawn, a wider range, a stop added or a member added is a minor. An
  id renamed or removed, a changed carrier, axis or default, a narrower range,
  a stop removed, renamed or moved, and a member dropped are a major. `label`
  and `datum` are a patch.
- **`@portrayal/kit` 0.19.0 takes a position as a field.** `fields.js` gains
  `adjustmentAccepts` (a value is a position, with the one spelling to keep,
  or a sentence saying what the adjustment takes), `adjustmentRows` (the rows
  of a control), `adjustmentsOf`, `paintAdjustments` and `positionsChanged`. `setFields` on the
  shell moves every member on every face when the field at a carrier's path
  is set, keeps the number for a stop name, takes an empty value as a reset,
  and now returns `{refused: [...]}`; a `fields=` link carries a position there and back. The
  3D viewer rebuilds the scene at the position: a well at the depth it gives,
  and what stands in it on that floor (`relief.js` `applyNodeAdjustments`).
  The Explorer has no control for a position yet.
