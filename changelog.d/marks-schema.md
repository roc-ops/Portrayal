### Added
- A JSON Schema for the marked-up drawing document,
  `spec/schemas/marks.schema.json`, so a client that sends one (an MCP tool, a
  script) can be told what to send. `normalise()` in `kit/marks.js` is tested
  against it: whatever it returns is a valid document.
