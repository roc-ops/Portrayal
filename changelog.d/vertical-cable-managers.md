### Added
- **Vertical cable managers, steps 1 and 2: `rack-side` mounting and `side`
  placements** (`docs/vertical-cable-managers-design.md`).
  `chassis.mount: rack-side` is a part that attaches to the side of a rack's
  upright and runs vertically beside the rack, outside the rails. It states
  `ru`, the rack units it runs beside (L125 warns without it, and
  `full-depth`, `overhang` and `ears` stay rack-only), and its DCIM export
  writes `u_height: 0` and `is_full_depth: false` with the comment line
  "Mounts on the side of a rack's upright, beside the rack; occupies no rack
  unit." Lint L152 (warning): a rack-side part's front is taller than it is
  wide, because it is drawn as it stands.
  A lab placement takes `side: left | right`. A rack-side part states it and
  is placed by `ru`, its bottom unit (default 1), on a `face` (default
  `front`); it takes no `on` or `unit`. A rack-face part narrower than the
  450 mm rack opening may state it too, and then claims its rack unit per face
  AND side, so a bracket on each rail shares a unit; any other rack-face part
  claims both sides (L142). Lint L153 (error): `side` only on those two, and a
  rack-side part has one. Lint L154 (error): a rack-side part fits the rack's
  height, and two on one side of the rack do not overlap. Every `labs.json`
  placement gains `side` (`left`, `right` or `null`); a new field only, and
  `contract` stays at 2.
  Two devices: `fs/cmv-sfd45u5w`, the FS CMV-SFD45U5W (#63033), a 45U
  single-sided ABS finger duct with hinged PVC covers, 2108 x 138.8 x 165.1
  (cover included; body 125.4), built hollow as a sheet body from the
  datasheet's back, side and cover views - the back plate as a well open at
  eight oval pass-throughs (`fs/cmv-sfd45u5w-base@1`), two finger walls
  (`-wall@1`), 92 fingers at one rack unit (`-finger@1`), 24 cover clips
  (`-clip@1`) and a pullable cover per 22.5U section (`-cover@1`), with a
  `duct` guide run down its height; and `fs/cmv-5u3w`, the FS CMV-5U3W
  (#64186), a 5U `rack-face` finger bracket 26 wide, 222 high and 84 deep on
  the rail face, from the datasheet's side and top views
  (`fs/cmv-5u3w-base@1`, `-fingers@1`).

### Changed
- **A `side` key on a lab placement is no longer refused by the lab schema**:
  it is checked by L153 instead. L142 claims a rack-face part's unit per face
  and side; a lab with no `side` anywhere resolves and checks exactly as
  before.
