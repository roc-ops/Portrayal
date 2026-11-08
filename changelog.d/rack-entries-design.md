### Added
- **A design note on rack cable entries and exits, proposed and put for a
  decision** (`docs/rack-entries-design.md`). It proposes where the `entries` key
  of `docs/rack-products-design.md` section 4 sits and what each entry holds,
  how an open frame's top is an exit, and the shape of the cables a caller
  passes in when they are stored outside the rack file, with what the kit
  returns for them. It proposes an optional `exit` key on the site file's rack
  end. No schema, tool, kit file or library product changes, and no rack file
  stores an outside cable.
