### Added
- The 3D viewer reports a lost WebGL context (#746). A viewer emits
  `contextlost` when the browser takes the context away and
  `contextrestored` when the scene is back, with the rebuild error or `null`,
  and `viewer.contextLost` says which state it is in.

### Fixed
- The 3D viewer survives a lost WebGL context (#746). The view went blank
  with no message and never came back. The viewer now lets the browser
  restore the context, then rebuilds the loaded device or component with its
  configuration, overrides, states, pulled parts, selection and marks, and
  leaves the camera where it was. While the context is lost the explorer says
  that 3D is paused, and when the browser refuses a new context it says to
  reload the page or close other tabs with 3D open.
