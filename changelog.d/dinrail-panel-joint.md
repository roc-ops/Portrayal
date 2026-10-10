### Added
- **common/pan-screw-m5@1**, an ISO 7045 M5 cross-recessed pan head, 9.5 across
  and 3.5 high, drawn where a document shows one (#971).

### Changed
- **FS DINRAIL2U and DINRAIL4U 1.0.0: the rail panel meets its side
  brackets** (#971). The datasheet's 400 mm is the rail; the panel is the
  width between the brackets' inner faces, so it no longer stands about
  10 mm clear of each bracket in 2D and 3D. fs/dinrail2u-panel@2 (421.2 wide)
  and fs/dinrail4u-panel@2 (419.7) replace the @1 majors, which are deleted.
  The joint is drawn as the side views show it: the brackets' edges are
  lowered between their ends, the panel's tabs lie on them, its flange shows
  through the slots and window, and two M5 screws a side stand in the slots
  at the default setback (a new `screws` group, four placements).
