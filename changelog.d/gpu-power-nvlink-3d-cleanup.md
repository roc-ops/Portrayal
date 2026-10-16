### Fixed
- The GPU power plugs and the NVLink bridge no longer flicker where two of their
  pieces shared a plane: a plug's rear wall is drawn inside its housing and ends
  short of the housing's rear face, its wires and stub start inside what they
  leave, its latch hook stands inside the arm, and the bridge's ends and steps
  start above its plate. A test holds all nine parts to it. The housings' side
  streaks were the rear wall and the housing drawing over each other.
- The four GPU power headers' cell walls no longer show a hairline of dark between
  a wall and the face: an exact `plate` skin 0.05 proud of the face, its cells cut
  0.03 smaller, covers the seam the raster face leaves.

### Changed
- The GPU power headers' latch ramp now slopes along the mating axis: a wedge on
  the outside of the side wall (the top wall on the 16-pin headers), from 0.3 out
  of the wall at the mouth to 1.4 at its far end. To say it, a relief feature that
  declares `profile` or `profile-y` may now have a negative `lift`, which starts
  it behind the face (component.schema.json). Nothing else in the library does.
  The ramp's node stands outside the skin's outline, so the 2D drawing no longer
  shows it; it is a side-wall feature.
