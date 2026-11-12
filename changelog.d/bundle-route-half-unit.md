### Fixed
- **A bundle no longer hangs the page when a cable's route ends at a half
  unit** (`kit/rack/bundle-route.js`). Creating or checking a bundle of cables
  where one ran to a half-unit position, for example a half-unit panel in the
  upper half of a unit, stepped along the lane a unit at a time and never
  reached the end, so the tab ran out of memory. A run is now cut at its two
  ends and at every whole unit between them, so its first or last step may be
  a half unit; whole-unit runs are cut exactly as before.
