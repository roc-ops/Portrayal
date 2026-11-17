### Added
- **The kit can work out the coil a cable's stored spare makes on a tray.**
  `rack/coil.js` gives the cells of a tray between its rings, the shortest and
  longest turn of a cable in each, and how many turns a stack holds, and
  `spareCoils` in `rack/slack.js` gives the coil, with its two legs, of each
  tray loop a cable names. The legs and turns are spare the cable already
  stores, so no path, length, stock size, export or finding changes. This closes
  the geometry part of the issue on drawing a cord's spare; capacity of a real
  lacer, placing spare on its own and a part for a rack's spare stay open.
