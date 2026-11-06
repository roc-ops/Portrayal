### Changed
- Tests state what is true of the library, not what a change left alone. The
  lists of parts and records rows that "stay" (`STAY`, `STAYS`, `STAYING`,
  `NOT_TAKEN`) and the checks that a part a change did not take keeps its
  contract and its row are removed from the device tests. The checks that the
  findings a change closes have no row left, the version pins and the census
  counts stay.
- `preflight.py` has a `records` check, advice only. It warns when a row of
  `library/conformance-exceptions.yaml` is removed by a diff that touches neither
  that part's folder nor that device's, and when a test under `spec/tests/`
  adds a list called `NOT_TAKEN`, `STAY`, `STAYS` or `STAYING`.
