### Added
- `@portrayal/kit` 0.3.0 carries the Rack Builder's rules as `@portrayal/kit/rack/<module>`:
  the rack file, fit rules, cable managers, cables, routes, the export and DCIM
  rules, the catalogue loader (`loadCatalog(dist)`, which reads `rack.json`
  through `flatDist` or `packageDist`), and the command core: every edit as a
  named, validated command (`commands.js`), undo and redo (`history.js`), a
  headless editor with change events (`editor.js`) and queries that read a
  rack (`queries.js`). `kit/README.md` has a "Racks" section with an example
  that `spec/tests/js/rack-readme-example.mjs` runs.
- `spec/schemas/rack.schema.json`, published at
  `https://portrayal.dev/schemas/v1/rack.schema.json`: the schema of a rack file
  (`format: "portrayal-rack"`, `version` 2). It is the Rack Builder's file
  format, not a manifest, so it does not carry format 1.
