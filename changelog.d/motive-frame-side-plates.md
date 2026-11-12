### Fixed
- The 3D view of the 20 Chatsworth Motive vertical cable managers (32610 to 32614 single-sided and 32620 to 32624
  double-sided, each in black and in Glacier White) no longer draws two faces on one plane where a side assembly and its
  guides met. A frame drew each side assembly as a solid the depth of the channel, 20 mm wide, in the space the T-shaped
  guides stand in, and the front of that solid lay on the plane of the front of every guide head, so the guides
  shimmered, most on the Glacier White parts. Each side assembly is now a thin plate under its guides, 1.5 mm thick
  (an estimate: no held page dimensions a side assembly), and the guides stand on it.
- The 20 devices take a major version (their placements name a new frame), their lock, one `side-assembly` gap each, and
  the `Drawing version` line of their exported device types, and nothing else in them.

### Changed
- The frame of each Motive part number, `chatsworth/motive-32610-703-frame` and its 19 siblings, takes a new major, `@3`:
  the two side assemblies are plates (a `lift` of 0.05 and an `out` of 1.55, drawn 19.9 wide inside the 20 of a guide, so no
  face of a plate lies on a plane of a guide) and not solids of the full depth. The central track, the colours and every
  other figure are as they were.

### Removed
- `chatsworth/motive-<part>-frame@2` for the 20 Motive part numbers (32610 to 32614 and 32620 to 32624, 703 and E03); each is
  replaced by the same name at `@3`.

### Added
- A test that a Motive frame's side assemblies are plates and that no two solids standing out of a built face of these parts
  have a face on one plane, facing the same way, over a patch they share.
