### Added
- The Explorer shell's `pulled` event carries an optional `views` list on a
  device with more than one view: `views[i]` is the view `paths[i]` is off on.
  `paths` stay bare ids and a one-view device's event is unchanged.
  `shell.select`, `over`, `setPulled` and `pulledPaths` take an optional view,
  `shell.pulledViews()` is new, and `viewer.setPulled` and `relief.js`'s
  `setPulled` take the views beside the paths. A call with no view means what
  it did (#1002).

### Fixed
- In the Explorer's 3D mode, pulling a part on one view no longer hides the part
  with the same id on the other views, and selecting one no longer lights its
  row under every view. On `fs/dinrail2u`, selecting `side-right` takes only
  the right side's screws off (#1002).
