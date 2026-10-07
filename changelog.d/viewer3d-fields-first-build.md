### Fixed
- The 3D viewer draws a part's fields on its first scene. `setFields` called
  before the first `load` - a host handing over a link's latch colour as it
  creates the viewer - was kept and never painted: the latch came up grey,
  and the same map again changed nothing. `build()` now loads the fields
  beside the lamp states and pulled parts, before any face is cut (#850).
