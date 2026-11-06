### Added
- `expand.py` repeats a strip PDU's outlets from a `layout.yaml`. An
  `outlet-run` block takes segments (one outlet kind on one pitch) and banks
  (the segments again, shifted). Each outlet gets its placement, its bezel
  moulding, its numeral and its lamp, and carries `fed-by`, `states` and, per
  bank, `through`. The Eaton PDUMV20HVNETLX is authored this way. It expands
  to the same outlets, so its version and its exports do not move.
  The change closes no conformance rows.
