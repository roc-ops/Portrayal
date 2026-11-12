### Fixed
- The solids of the 20 Chatsworth Motive vertical cable managers (32610 to 32614 single-sided and 32620 to 32624
  double-sided, each in black and in Glacier White) and of the APC AR7722 lie inside the part. Their frames, guides, doors
  and rails were placed on the face with no well to stand in, so a rack or a 3D scene built from the build's `rack.json`
  stood them a part's depth in front of the part (and, on the rear face of a double-sided manager, behind it). Each part now
  has a base well as deep as its printed depth - 392 mm on a single-sided Motive manager, 201 mm a face on a double-sided
  one, on the front and on the rear, and 45 mm on the AR7722 - and its frame, guides, door and lengths are placed in it. The
  well draws no back plate, because the rear of each part is open. No face is drawn differently: the faces of the 21 parts
  are pixel for pixel what they were, and what moved is where the raised parts stand in depth.
- The 21 devices take a major version (the lock reads `in:` on the placements it moved), their lock, and the
  `Drawing version` line of their exported device types, and nothing else in them.

### Changed
- The frame of each Motive part number is no longer a well: `chatsworth/motive-32610-703-frame` and its 19 siblings drop the
  depth of their size and take a new major, `@2`; their relief, their elements and their skins are unchanged.

### Removed
- `chatsworth/motive-<part>-frame@1` for the 20 Motive part numbers (32610 to 32614 and 32620 to 32624, 703 and E03); each is
  replaced by the same name at `@2`, the same drawing without the depth that made it a well.

### Added
- Eleven base wells that the 21 parts stand in: `chatsworth/motive-vcm-base-ss-<w>` (150, 200, 250, 300 and 380 mm wide,
  392 deep), `chatsworth/motive-vcm-base-ds-<w>` (the same five widths, 201 deep, one face of a double-sided manager) and
  `apc/nsx-vcm-ar7722-base` (45 deep).
- A test that every rack-side or zero-U part's solids in the built `rack.json` lie within its own depth, from 0 to `d`.
