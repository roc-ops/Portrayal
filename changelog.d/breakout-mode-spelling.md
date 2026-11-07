### Added
- **Lint L195: a breakout mode is `<count>x<speed>`** (#536,
  `docs/lint-rules.md`). Every `interfaces[].breakout.modes` entry in a listing
  or a device is a count of one or more with no leading zero, the letter `x`,
  and a speed from `spec/schemas/speeds.yaml` in lower case (`4x25g`, `1x400g`),
  so a filter for ports that break out can read the count. It is an error, and
  no mode in the library fails it.

### Changed
- **The three S9600 lane-sharing keys are renamed.** `breakout` becomes
  `sfp28-sharing` in the `attrs.features` of `ufispace/s9600-28dx`, `s9600-32x`
  and `s9600-64x`, the name `s9600-56dx`, `s9610-46dx` and `s9610-48dx` already
  use. The four SFP28 cages share QSFP28 port 0's lanes; that is a constraint
  between two cages, not a mode. The wording and the provenance are unchanged.
  **A consumer reading `features.breakout` in a device type's `comments` finds
  `features.sfp28-sharing` instead.** Each of the three devices takes a patch
  bump (`s9600-28dx` 4.0.8, `s9600-32x` 3.0.7, `s9600-64x` 4.0.9). Fourteen
  exports change, in their `comments` only (the renamed key and the drawing
  version), seven in NetBox and seven in Nautobot: `UfiSpace/S9600-28DX`, `UfiSpace/S9600-32X`,
  `UfiSpace/S9600-64X`, `IP Infusion/S9600-28DX`, `IP Infusion/S9600-32X`,
  `IP Infusion/S9600-64X` and `Arrcus/S9600-32X`.
