### Added
- Panduit cable managers (#1092, part of #1091), with `panduit` added to the vendor registry (listed
  directly before `accton`). The NetManager High Capacity horizontals `panduit/nm1`, `nm2`, `nmf1`,
  `nmf2`, `nmf3` and `nmf4` (1 to 4RU, twelve T-shaped fingers a wall and a `duct` guide; the
  front-and-rear NM1 and NM2 also have five open D-rings on the rear, each a `ring` guide); the
  NetManager `panduit/ncmh2` (front and rear) and `ncmhf2` (front only), with the 9.5 mm finger
  spacing and 34.925 mm pitch Panduit states; the PatchRunner 2 horizontals `panduit/pr2hf3wh` and
  `pr2hf4wh` (seven fingers a wall); the PatchRunner 2 verticals `panduit/pr2vsd06`, `pr2vd08` and
  `pr2vd10` (45RU, 45 fingers a side of each face, four 3.0 in holes, doors that ship fitted); and the
  NetRunner vertical `panduit/wmpvhc45e` (eight oval holes, four covers). Every part has its
  pass-through windows or holes declared open, and a cover or door that ships fitted and comes off in
  a `cover-off`, `doors-off`, `door-off` or `covers-off` configuration. Cable capacity is the figure
  Panduit's bulletin or calculator states for the part, with its basis; the horizontals are `rack`
  parts that fill their rack units, the verticals `rack-side`. The PR2VSD06 states no capacity because
  no Panduit document does. The NM3, NM4, NCMHF1 and the PatchLink, Open-Access and strain-relief
  parts are not modelled.

### Fixed
- The 3D viewer's opening view is fitted to the chassis box (`kit/camera-fit.js`): the nearest distance
  at which all eight corners sit inside the frame for the lens and the frame's aspect, never nearer than
  the old two spans, with the dolly limit and the far plane moved to match. A 7 ft manager (`panduit/pr2vd08`,
  `wmpvhc45e`) used to open cut off at the top and the bottom, because the eye was asked for 4260 mm out and
  pulled in to the 2500 mm dolly limit; a box that was framed keeps the opening view it had.
- The 2RU NetManager covers (`panduit/nm-cover-2ru` and `nm-rear-cover-2ru`, 1.0.1, on the NM2 and NMF2)
  are no longer one flat slab: a panel sunk inside a raised rim, with five hinge knuckles along each of the
  top and bottom edges. The rim, the panel's thickness and the knuckles are estimated stand-ins, declared
  as such in the sources and on every feature; no Panduit view draws the cover's section or hinge.
- A test holds the fingers of every Panduit manager in front of the backbone and not through it: each
  finger rises from its well's floor to inside the face, and the front and rear wells leave the backbone
  between them.
