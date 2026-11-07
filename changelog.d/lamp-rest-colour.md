### Added
- `common/led-rect@2` and `common/led-rect-sm@2`: the same parts as version 1 in
  every respect except the colour a lamp rests in. Version 1 rests dark green,
  so a lamp a photograph shows dark was drawn green; version 2 rests unlit
  grey (`#3a3938`, estimated from 27 unlit lamps in two product photographs,
  which disagree with each other, so the contract says the value should be
  looked at). Size, lamp, states, dome and every lit colour are version 1's,
  because a lamp lights through `--led-color` set by a `state-*` class and the
  skin names no lit colour. Version 1 and every device are unchanged, and no
  device seats a version 2 yet, so each carries `unplaced:`. A device adopts it
  by changing its placement `ref` to `@2`; the first device to do so removes the
  `unplaced:` line from that contract.
