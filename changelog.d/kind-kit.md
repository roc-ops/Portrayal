### Added
- `kind: kit`, a third kind of component contract, for a rail, bracket or
  slide kit (#905). A kit has no `class`, no `size` and no skin, and admits
  only `format`, `kind`, `name`, `version`, `description`, `provenance`,
  `unplaced`, `superseded-by` and the kit keys: `motion`, `travel`, `install`,
  `parts` (`{ref, id, count}`), `configurations` (`{id, racks, parts, depth,
  preset, tolerance, rail-depth}`, `depth` one `[min, max]` or one per hole
  type) and `accessories` (`{kind: cma|srb, ref, rail-depth, sides}`). A
  component or module still requires `class` and `size` and takes none of
  them. No kit is in the library yet.
- Lint L155 to L159 check a kit: each part ref resolves to a component that is
  not a kit and part ids are distinct; a configuration names only the kit's
  own part ids and has an id of its own; every depth range has min below max;
  `travel` only with `motion: sliding`; each accessory ref resolves to a
  component that is not a kit.
- `library/dist/kits.json`: every kit as its contract states it, written by
  `components_index.py` on every build (`{"kits": []}` while there is none). A
  kit is never an entry of `components.json`, and the component catalogue lists
  kits in a table of their own, outside its component count. The keys are
  documented in `docs/format-stability.md`.
