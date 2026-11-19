### Changed
- `test_facet_render.py` draws each of its cards through `warmrender`, as the other build tests do, so
  the 20 facet tests no longer parse the whole library once per render. The same 20 tests make the same
  assertions; the module takes about half the seconds.
