### Added
- **The site file, version 0: a design note and a schema, proposed and not yet
  decided** (#1297). `docs/site-file-design.md` describes `portrayal-site`, a
  document above the rack file holding a site's buildings, floors and spaces
  (IFC 4.3's names, with an IFC-style GUID and a file-wide id on every
  object), racks placed by reference to their rack files, walls and
  backboards, devices that are not in a rack, pathways as a graph, and cables
  whose two ends are not in one rack, each stored at the lowest level that
  holds both ends. `spec/schemas/site.schema.json` is its schema under
  `/schemas/v1/`, and `spec/tools/portrayal/sitefile.py` checks what the
  schema cannot: file-wide unique ids and GUIDs, references, the lowest-level
  rule, and a reader that refuses a newer version whole. A placed rack file
  is read and never rewritten. Section 12 of `docs/rack-file-v4-design.md`
  now gives rows, the room and cables between racks to the site file instead
  of a rack file version 5. No kit module reads the site file yet.
