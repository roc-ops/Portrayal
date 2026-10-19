### Changed
- **One-way (format): a kit configuration may state a `preset` and no `depth`**
  (#904, decided 2026-10-18; `component.schema.json`, lint L157 and L158,
  `docs/rack-mounting-design.md` section 4). A configuration states at least
  one of `depth` and `preset`; one with neither is refused. A preset alone
  reads as "factory setting known, range unknown": `kits.json` and
  `<device>.configs.json` publish it with the `preset` and no `depth` key (never
  `null`, never `[preset, preset]`), and nothing derives a range from it. The
  kit gains a `gaps` list in the shape a device's has, published in `kits.json`
  as `gaps` (`[]` where a kit has none); L157 asks for an entry `what: depth`
  whose `scope` lists each configuration that has a preset and no depth, and
  still refuses a range whose min is not below its max. L158 now also refuses a
  `telescoping` kit that states no `preset` on any configuration. **A page that
  reads `depth` of a kit configuration must handle its absence, and a
  `kits.json` holding such a configuration cannot be taken back to a reader
  that cannot.** No kit in the library uses it yet, and this adds no kit
  version bump.
