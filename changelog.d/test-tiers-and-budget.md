### Changed
- A push to a pull request runs the light tier of the suite, every test not
  marked `heavy`, on two shards; its verdict is the check `light suite`. The
  whole suite runs before a merge (`gh workflow run gates.yml --ref <branch>
  -f pr=<number>`, which tests the pull request's merge with main) and every
  night on `main`, and only that full run reports `build`, the check
  branch protection requires. A pull request from a fork runs the whole suite
  on every push.
- 973 test functions (2,320 tests) are marked `@pytest.mark.heavy`
  (`spec/tools/dev/mark_heavy.py`): five seconds or more in a full or a light
  run, every member of an xdist group with one that is, and every function of a
  file whose light tests inherited 20 s of shared fixture cost.
- `shards.py` splits after `-m` deselects, so a light-tier shard records the
  tests it ran.

### Added
- `spec/test-budget.json` holds each tier to its summed seconds (light 2,190,
  full 11,000), read in the units of the run each was set from
  (`spec/test-budget-reference.json`, file by file) so a slow runner is not a
  bigger suite, and a new light-tier test function to under five seconds.
  `spec/tools/portrayal/suite_budget.py` fails the run past either. Raising a
  budget or re-recording its reference is a one-way door.
