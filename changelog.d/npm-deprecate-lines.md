### Added
- `spec/tools/dev/npm_deprecate_lines.py` prints one `npm deprecate` line for
  each package npm holds under the scope that a build no longer ships, from a
  list of held names a maintainer makes. It runs nothing and asks npm nothing.
  `docs/maintainers.md` says when to use it (#526). It closes no conformance row.
