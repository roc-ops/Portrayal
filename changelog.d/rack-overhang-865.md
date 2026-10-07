### Added
- `chassis.overhang: {left, right}` states how far a `rack` device's real parts
  reach beyond its rack face, in millimetres (#865). Such a device draws its
  front at the rack face with its ears, and a part beyond it is an ordinary
  placement at negative x or past the view's width. L150 refuses a placement,
  bay or cutout outside its face that the side's figure does not cover
  (optional placements and decor are not checked); L151 warns when no part
  reaches a stated figure. `<device>.configs.json` carries it as
  `chassis.overhang`, and the DCIM exports say it in the comments, since
  neither schema has a field for it. It is geometry to devicelock.
- `chassis.ears: behind` states that a rack device's ear folds are behind its
  body, so a 482.6 mm front is the part and L43 stands down (#865).
  `<device>.configs.json` carries it as `chassis.ears`; devicelock files it
  as surface.
- `fs/uscmh-sfdabsb2u` 0.1.0, the FS USCMH-SFDABSB2U 2U ABS finger duct, the
  width of the rack in front of its rails, from the FS Horizontal Single Sided
  Manager datasheet, with its parts `fs/uscmh-sfdabsb2u-base@1`, `-finger@1`,
  `-end-finger@1` and `-cover@1` (#865).
- `fs/cmh-6dr1u-end-ring@1` and `fs/cmh-6dr1u-ear@1`, the CMH-6DR1U's end
  ring, with a vertical `ring` guide, and its ear (#865).

### Changed
- `fs/cmh-6dr1u` 1.0.0 draws its front at the 482.6 mm rack face with its ears, and
  its two end rings 43 mm past each, where they were a gap; it states
  `overhang: {left: 43, right: 43}`. Its D-rings move 26.3 mm right on the
  wider face; the moved geometry takes the major. Its DCIM exports gain the
  overhang comment.
- `nokia/lmfs-f` 2.0.0 states `overhang: {right: 47}`, the reach of its horizontal
  front dust filter past the right flange, which it already drew in the
  front-cover configuration. `overhang` is geometry to devicelock, so stating
  it takes a major though nothing on the drawing moved. Its DCIM exports gain
  the overhang comment.
- A drawing bigger than its face (a part beyond it grows the viewBox) carries
  the face it declares as `data-face-w` and `data-face-h` on its root, and the
  3D viewer lays the face out on that rather than on the drawing's extent, so
  the face is centred and a part beyond it stands beyond the plate. A drawing
  that fits its face is unchanged. A sheet body's rack face builds no 25.4 mm
  plate (#865).

### Fixed
- The 3D front of `nokia/lmfs-f`'s front-cover configuration was laid out on
  the 528 mm drawing rather than its 481 mm face, so every part sat 23.5 mm
  left of where it is and the face was textured over a plate 528 wide (#865).
