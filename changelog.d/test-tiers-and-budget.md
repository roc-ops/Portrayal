### Changed
- A push to a pull request runs the light tier of the suite, every test not
  marked `heavy`, on two shards; its verdict is the check `light suite`. The
  whole suite runs before a merge (`gh workflow run gates.yml --ref <branch>
  -f pr=<number>`, which tests the pull request's merge with main) and every
  night on `main`, and only that full run reports `build`, the check
  branch protection requires. A pull request from a fork runs the whole suite
  on every push.
- 264 test functions that a full run measured at five seconds or more are
  marked `@pytest.mark.heavy` (`spec/tools/dev/mark_heavy.py`).
- `shards.py` splits after `-m` deselects, so a light-tier shard records the
  tests it ran.

### Added
- `spec/test-budget.json` holds each tier to its summed seconds (light 1,550,
  full 9,700), with the runner's load divided out, and a new light-tier test
  function to under five seconds. `spec/tools/portrayal/suite_budget.py` fails
  the run past either. Raising a budget is a one-way door.
