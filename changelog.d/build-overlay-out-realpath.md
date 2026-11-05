### Fixed
- `build.sh --overlay-out` resolves the output folder through `python3`, not
  `realpath -m`, so an overlay build runs on macOS, whose `realpath` has no
  `-m` option. A test puts a `realpath` that refuses `-m` first on `PATH` and
  builds an overlay.
