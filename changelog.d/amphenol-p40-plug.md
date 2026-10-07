### Added
- The P40 output plug, `amphenol-ns/p40-plug@1` (Amphenol PRM0400, 4 mm
  contacts), and the interface it mates, `p40`.
  `amphenol-ns/output-p40@1` presents it, so all sixteen outputs of the
  300CB08-C, 300CB08-SC and the four nrg300CB08 connectorized panels are
  connector slots that accept the plug. The plug is drawn from the wire side
  with a stub per pole (BATT, RTN), sized by `wire-od` and coloured by
  `wire-color`; no panel seats one by default.

### Changed
- `amphenol-ns/output-p40@1` is 1.1.0: it gains its interface and mate point,
  and its drawing does not change. The six panels that place it take a
  patch; their DCIM exports change in the drawing version line only.
