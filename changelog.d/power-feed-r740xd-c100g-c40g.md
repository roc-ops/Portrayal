### Changed
- `dell/r740xd` (30.0.0 to 30.0.1) and `casa/c100g` (1.0.5 to 1.0.6) state `chassis.power`: `ac` for the R740xd, whose every
  configuration seats the 1100 W AC supply, and `dc` for the C100G, whose one chassis the data sheet sells for DC power.
  `casa/c40g` (0.6.3 to 0.6.4) states `power` on three of its four orderable configurations: `ac-power` is `ac`, and
  `dc-power` and `docsis-non-redundant` are `dc`. Its `base` configuration seats neither supply and the vendor sells the
  chassis for AC or for DC, so it states nothing and the device keeps its entry in the lint baseline. Each device gains a
  `power-feed` provenance note naming the input rows its statement comes from. No drawing, port, bay or id changes.
  The three devices' `configs.json` carry the new `power` field; no export file is renamed, so this is not breaking.
  This closes two entries of the lint baseline (L119, for the R740xd and the C100G) and no row of the conformance records.
