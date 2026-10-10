### Added
- `rackDiagram` in `@portrayal/kit/drawio` takes three optional keys (#724).
  A group may carry its own `faces`, so a page draws only the faces it names
  and a rack builder can make one page per face. A mounted device may carry
  its own `id`: cell ids are slugged from it and not from the name, so two
  devices of one model are two cells. A rack may carry its own `numDisp`, and
  `descend` prints U1 at the bottom. Without the three keys the output is
  what it was.
