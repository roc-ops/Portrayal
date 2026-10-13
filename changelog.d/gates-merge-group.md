### Changed
- **The gates run on a merge queue's `merge_group` event** (#1054,
  `.github/workflows/gates.yml`). `lint` and `build` both report on it, with the
  full suite as on a ready pull request, so a merge queue can be turned on
  without a head being updated by hand each time another pull request merges.
  Pull requests and pushes run as before.
