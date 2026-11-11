### Added
- `chassis.fins`: the ribs of a cast housing that states a `chassis.section`. A list of rib fields, each on
  the section's top or bottom edge, with a `span` along the length, a `rib` thickness and `gap`, and either a
  `core` (the height of the tallest rib from the casting's surface, the ribs inside the stated size) or
  `outside: true` with a `height` (the ribs stand out of the casting's edge, up to 60 mm beyond the box), and
  optional `steps` that lower the tips. The casting is cut back to its core and the ribs stand on it. The front
  and rear outlines follow the steps and the ribs are painted inside them, the top and bottom carry a stripe
  for each rib, and an end face shows a band where the casting is cut back. In 3D the body is the cut-back
  section with the ribs merged into one buffer, and the camera fit includes ribs that stand outside the box.
  `fins` is surface in the device lock, so retuning a height is a patch. New lint rules L208 to L216 judge it.
  `<device>.configs.json` carries the fields as written. No library device states `fins`, so no published build
  changes. An older validator refuses a file that states it. The open state of a ribbed housing is not part of
  this change.
