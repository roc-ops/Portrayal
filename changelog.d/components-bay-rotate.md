### Fixed
- `components.json` publishes a turned bay with its `rotate` (#718). Each
  component entry lists its own bays with `at`, `size`, `accepts` and
  `default`, and left out the turn, so a consumer placing a card by the index
  landed it wrong in a turned slot. The two slots of `dell/riser-3a-14g@2`
  carry `rotate: 180`. A bay that is not turned states nothing, as before.
  Additive; the `contract` number does not move.
