### Changed
- The descriptions in the six JSON schemas say what each field is, what it
  takes and what it does, without citing repository paths, document sections,
  steps or issue numbers, and without the history of how a rule came about
  (#951). 132 of 553 descriptions changed; what validates did not. The reasons
  that history carried are in `spec/DESIGN.md`, under "Why some schema fields
  are shaped as they are". American spellings in the rack schema (millimeters,
  catalog) and in a few colour descriptions are now British.
- A test records each schema's shape with its descriptions removed
  (`spec/tests/fixtures/schema-shape.json`), so a change to what validates is
  re-recorded on purpose, with
  `python3 spec/tests/test_schema_descriptions.py --update`. Another rejects a
  description that cites a `.md` file, `spec/`, `docs/`, a section, a step or
  an issue number.
