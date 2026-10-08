### Added
- `cable-types.json` in the published build: named cable types (OM3, OM4,
  OM5, OS2 and its G.657.A1 and A2 cords, Cat 6 and Cat 6A unscreened and
  screened, passive DAC by gauge, AOC, and C13 and C19 power cords), each with
  its media, a typical outside diameter and a minimum bend radius
  `{installed, loaded}` as a fixed figure or a multiple of the diameter,
  marked standard or convention, with its source. The source table is
  `spec/schemas/cable-types.yaml`. The bare type ids are the Rack Builder's
  cable media, so a cable's media names its type. The kit's new
  `@portrayal/kit/rack/cable-types` resolves a type's installed radius in
  millimetres (`radiusMm`, `installedRadiusMm`, `bendLookup`) and loads the
  file (`loadCableTypes`). A new file, so `contract` stays 2 (#919).
