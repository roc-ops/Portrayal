### Fixed
- `test_the_stub_dist_carries_what_the_build_does` no longer fails when it runs after the CH3000
  guard in `test_midplane_depth_lint.py`. That guard edited the parse `load_yaml` shares with the
  whole process, so the stub read a CH3000 with an extra rear bay; the guard now edits a copy,
  and a test holds the shared parse equal to the file.
