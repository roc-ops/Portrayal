### Added
- A test that every built face of a rack-side or zero-U part stands inside the part. It reads each compiled face
  (`data-z-out` and the summed `data-z-lift`) and fails for an element that covers anything outside the part's extent
  along that face's normal: its depth for the front and rear, its height for top and bottom, its width for left and right.
  The solids check of the built `rack.json` only sees what `rack.json` turns into a box, so a door or a guide drawn in
  front of its part, or a frame without a base well, was not caught there. 27 parts stand a control proud of a face
  (breaker plates, buttons, a ground stud nut, an LED lens, 0.3 to 7.5 mm); each is listed in the test by name with the
  distance, and the test fails for a part that is not listed, for a listed part that no longer stands outside, and for
  one that stands further out than listed. No library file changes.
