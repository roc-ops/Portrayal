### Added
- The 3D explorer marks the far end of a selected fibre with a ring on the face
  that draws it, the way the 2D explorer rings it. The mark clears with the
  selection, on a return to 2D and when another device loads.

### Fixed
- Selecting a rear fibre in the 3D explorer marks that fibre. The rear
  connector is drawn only as a projection, which the scene's path index did not
  hold, so the whole front cassette was haloed instead. A projection is now
  indexed under the path it is of, only where no face draws that path as a part.
