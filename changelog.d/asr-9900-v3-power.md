### Added
- `cisco/pwr-6kw-ac-v3@1` (PWR-6KW-AC-V3, 6000 W AC) and `cisco/pwr-4p4kw-dc-v3@1`
  (PWR-4.4KW-DC-V3, 4400 W DC), the version 3 power modules of the ASR 9906 and ASR 9910. Each is
  drawn once, horizontally, with two fan wheels, a latch and three lamps. Their width is the module
  pitch read off Cisco's stencil (139.0 mm AC, 104.7 mm DC), declared `drawing`; the guides state no
  dimension, depth or weight, so there is no `size.d` and no body. Refs #262.
- The ASR 9906 and ASR 9910 seat them: a `power-modules` group of AC bays (three per tray, base and
  `ac`) and DC bays (four per tray, `dc`) sharing each shelf's footprint, one tray on the 9906 and
  two on the 9910, and two example configurations, `ac` and `dc`, with no part number because Cisco
  lists no AC or DC chassis. Mixing AC and DC is not supported by the hardware and is not enforced.

### Changed
- `cisco/asr-9906` and `cisco/asr-9910` are 2.0.0 (`devicelock` asked for a major: the power shelf
  cutouts grew to the measured extent of the module stack, 46.0 x 418.8 on the 9906 and 418.8 x
  46.0 per shelf on the 9910, and the bays are new). The base configuration seats the AC modules.
  The `power-module-openings` gaps and the shelf provenance are restated, the DC input, output bus
  and per-tray counts join the `power` block, and the 9906's `rear-face` gap now says Cisco's
  stencil lists an ASR-9906 Rear master. The DCIM device types and the two module types are
  re-exported.
