### Added
- A configuration can turn a seated occupant: an `occupants:` mapping takes
  `turn:`, in degrees, relative to the seat, one of the turns its host allows.
  An interface in `spec/schemas/connectors.yaml` lists the turns it allows
  (`terminal-stud`: 0, 90, 180 and 270, so a ring lug turns freely on a ground
  stud), and a component's presented connection point may narrow them with
  `turns:` (`common/terminal-screw-34@1` and `-38@1` allow 0 alone: the
  barriers fix the pole). An interface that names none allows 0, so no other
  seat changes (#829).
- Where a configuration states no turn, the build chooses one for a seat that
  turns: the wire goes down, toward the nearer side edge of the face, the other
  side or up, the first direction in which the whole lug crosses no part, bay or
  other seat; running past the edge of the face is allowed and a printed legend
  is avoided where it can be. Across the library's 155 ring-lug seats on 63
  devices that is 103 down, 24 left, 22 right and 6 up, none across a part, and
  the ring lug no longer lies across LAN1 on the Supermicro SYS-111E-FWTR and
  SYS-111E-FDWTR, the ESD jack on the Juniper MX150, a fan bay on the Edgecore
  DCS500 or the second stud of a pair. A two-hole lug on a stud pair (#828)
  turns 0 or 180 only, and its 51 seats on 25 devices lead 45 down, 4 left, 1
  right and 1 up; two of them, on the MX150 and the MX480, cross a part either
  way and are recorded. No library configuration seats a lug, so no drawing
  changes (#829).
- `<device>.configs.json` publishes `turns` on every slot entry (the angles an
  occupant may take on top of `rotate`, null where there is no choice) and
  `seat-turns`, `{view: {slot key: {ref: turn}}}`, the turn the build seats a
  part at where its configuration states none; a seated occupant on a seat
  that turns carries `data-seat-turn`. `components.json` cages carry `turns`
  too (#829).
- The explorer offers a turn for a seated lug in the inspector, seats it the
  same way in 2D, in the faces it holds and in 3D, and writes the reader's
  turns to the share link in a parameter of its own, `turn=<key>~<deg>`, so a
  link written before it keeps its swaps. `kit/swap.js` gains `seatTurn`,
  `seatRotate`, `encodeTurns`, `decodeTurns`, `acceptTurns`, `builtTurns` and
  `turnOverrides`; `occupantAt`, `occupantTransform`, `seatOccupant`,
  `applyOccupantOverrides`, `applyFaceOverrides`, `seatFace`, `seatViews` and
  `viewsToRewrite` take the turns as a further, optional argument (#829).
- Lint L146: an occupant's `turn` is one its host allows. L147: a connection
  point's `turns` is a subset of the turns its part's interface allows, and
  only the presented point states one (#829).
