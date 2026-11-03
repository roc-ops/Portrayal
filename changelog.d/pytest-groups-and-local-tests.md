### Fixed
- The `xdist_group` marks work again: the `test` extra pins pytest below 9.2,
  whose new test ids ignore the rename pytest-xdist 3.8 uses to keep a group on
  one worker. Since 9.2 reached CI, the tests that share one whole-library lint
  had run on separate workers at once, each billed for the same lint.
  `test_an_xdist_group_reaches_the_scheduler` now fails by name when a version
  breaks the rename.

### Changed
- A contributor runs the tests a change reaches, not the whole suite:
  `pytest spec/tests -k <vendor>/<model>` and the test files the change adds or
  edits. CI runs the whole suite on the pull request. The contributing guide,
  the pull request template, the modelling skill and `AGENTS.md` say so.
