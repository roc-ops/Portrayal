### Added
- **A cover says what it hides: `hides:` on a placement, `data-hides` on its
  group** (#642). A cover is a removable part that hides others, such as a
  bezel over drives or a filter cover over PSUs. A device placement lists the
  placements and bays on its face that the cover lies over, and the compiler
  writes them as `data-hides="<id> <id> ..."`, each a path a consumer finds in
  the same drawing, as with `data-covered-by`. One attribute says both "this is
  a cover" and what it hides, which `data-class` and `data-for` cannot (screws,
  ground studs and ESD jacks carry `data-for` too); `data-for` keeps its
  meanings. The elements file gains a `hides` list per row. L196 refuses an
  id that names nothing on the face, one on another face, and one the cover
  does not overlap. The C40G's PSU filter cover (its four PSUs) and the
  R660's bezel (its drives) carry it; the other covers follow.
