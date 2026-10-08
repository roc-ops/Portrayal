### Added
- `library/dist/rack.json`: the rack catalogue, written by `rack_index.py` after
  the compiled faces exist. Each device carries its rack units, size, airflow,
  default configuration and configurations, and, only when it has them, its
  `mount`, `shell`, stated cable `capacity`, and the `guides` and `passes` ids a
  cable route can pass through on each view. `format` is 1; the keys are
  documented in `docs/format-stability.md`.
