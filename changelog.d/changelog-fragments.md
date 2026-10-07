### Changed
- A pull request records its change in a new file under `changelog.d/`
  instead of editing `CHANGELOG.md`, which every pull request used to edit at
  the same lines. Each file holds entries under `### Added`, `### Changed`,
  `### Removed` or `### Fixed`; `spec/tools/portrayal/changelog.py` checks
  them (a test runs it) and folds them into `## Unreleased` when a version is
  cut. Until then the unreleased record is that section followed by the
  fragments, and `changelog.py --show` prints the two together.
- `library/components/CATALOGUE.md` is no longer committed. `./build.sh`, and
  so `./publish.sh`, writes it at the same path, which is now gitignored, and
  `python3 spec/tools/portrayal/components_catalogue.py --library library
  --out library/components/CATALOGUE.md` writes it without a build. Its
  component total and its per-part device counts moved with nearly every pull
  request, so a committed copy conflicted as often as the changelog did. The
  test that compared the committed page with the generator now checks the
  generator: that it runs and that its page has a row for every component
  major.
