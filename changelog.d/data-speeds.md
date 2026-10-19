### Added
- **`data-speeds`: a multi-rate cage publishes every native rate, not just the
  highest** (#512, `spec/schemas/speeds.yaml`, `spec/tools/portrayal/lint.py`
  L110). A port group's `attrs` (or a placement's) may carry `speeds: [1g, 10g,
  25g]`, compiled to `data-speeds="1g 10g 25g"` and to a `speeds` list on the
  `<device>.<view>.elements.json` rows, so `[data-speeds~="10g"]` finds a
  1/10/25G SFP28 group. It is written per group from the vendor's own figure,
  lists native rates only (no breakout), and is absent on a single-rate port.
  L110 refuses a member outside the closed set, a duplicate, and a list whose
  highest member is not `speed`. First device: `ufispace/s9600-72xc`
  (SFP28 `1g 10g 25g`, QSFP28 `40g 100g`). Other devices follow.
