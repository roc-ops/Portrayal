### Fixed
- The covers of the FS HD and UHD finger ducts show their four latches in 3D
  (#869): the plate and its clips are one raised group, so the clips are
  drawn on the face instead of left behind it, and the hinge rails end 0.1 mm
  behind the face. `fs/cmh-uhd-sfdabs1u-cover`, `-2u-cover`, `-3u-cover`,
  `fs/cmh-hd-sfdabs3u-cover` and `-4u-cover` 1.0.1; the five devices 0.1.1.
  The 2D drawings are unchanged.
- Four FS finger-duct covers reserve a `logo-zone` where FS prints its mark
  (#869), so a renderer has the box without the library drawing a vendor
  logo. Measured on FS's straight-on renders for `fs/cmh-sfds1u-cover` and
  `fs/cmh-dfds2u-cover`, estimated from an angled close-up for
  `fs/cmh-sfd1u-cover`, and borrowed from the SFDS1U for
  `fs/cmh-bs-sfds1u-cover`, of which no image exists; all four 1.1.0.
  `fs/cmh-sfds2u-cover` and `fs/cmh-dfds1u-cover` claimed a mark that no
  render or drawing shows; their provenance now says so, 1.0.1. The devices
  cmh-sfds1u, cmh-sfds2u and cmh-bs-sfds1u 0.1.1, cmh-dfds1u, cmh-dfds2u and
  cmh-dfd1u 0.1.2, cmh-sfd1u 0.1.3. The 2D drawings are unchanged.
