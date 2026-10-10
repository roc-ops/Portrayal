### Added
- Preflight has an eighth check, `prose`, and it only warns (#114). It reads
  each `device.yaml` and `contract.yaml` the diff changes and reports a
  sentence of more than 25 words that the merge base does not have, in a
  `description` (device, configuration or component) or a string under
  `attrs`. That is the prose a DCIM export carries. Text the base already
  holds is never reported, words quoted from a vendor are not counted, and gap
  notes and `provenance` are not read. A WARN leaves the exit status and the
  `ok` field of `--json` unchanged; a check's `status` in `--json` can now be
  `WARN` as well as `PASS` or `FAIL`. `CONTRIBUTING.md` states the rule: new
  and changed prose follows Simplified Technical English, and existing text
  is not rewritten.
