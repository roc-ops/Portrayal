### Changed
- The APC by Schneider Electric NetShelter AP7821B and AP7921B 1U rack PDUs now draw the small round marks their data
  sheet photographs show. Two sit at each end of the outlet face. Six sit on the display end, in two rows of three.
  Every position is an estimate read off a 369 px photograph, and the devices say so. The AP7821B's display end borrows
  the AP7921B's pattern.
- Each outlet face now draws five small lamps and a small Reset hole at the display end. The lamps are drawn off, and
  the viewer lights them. The load lamps are `lamp-load-ok`, `lamp-load-warning` and `lamp-load-overload`, in one
  column above the display. The jack lamps are `lamp-jack-1`, the Link-RX/TX lamp, and `lamp-jack-2`, the Status lamp.
  Each lamp carries the states the maker's guide gives.
- The two jack lamps are small upright rectangles, because the guide draws the windows as rectangles. They use the
  existing small bar lamp, turned a quarter. The load lamps stay round.
- The guide's place for the jack lamps falls inside the library's wider jack, and the overlap check refuses it. Each
  lamp stands just outside the jack's right edge instead.
- The small bar lamp part, `common/led-rect-sm` version 2, drops its note that no device uses it yet. Its drawing and
  size are unchanged.
- The display, the round button and the two jacks are now named from the maker's guide. The upper jack is the 10/100
  network port and the lower jack is the RJ-12 serial port. The notes cite the guide pages.
- Each device goes from version 0.1.0 to 1.0.0, a major version, because existing lamps moved and an id was renamed.
  The old `lamp-status` id is gone from both devices. Its green lamp is now `lamp-load-ok`, about 8 to 9 mm to the
  right and about 3.5 to 4 mm up. `lamp-jack-1` and `lamp-jack-2` keep their ids and move about 2 mm left and 2 to 4
  mm up.
- The DCIM device types of both devices change in two places. The description names five lamps and a Reset hole. The
  drawing version line reads 1.0.0.
- Each device keeps eight gap rows. One is replaced and three are reworded. None is closed outright. The lamp-colours
  row is replaced by lamp-marks, because the lamp colours now come from the guide and the photograph. The jack-function,
  jack-speed and sides rows are reworded.
- The printed legends, the icons beside Status and Link, and the logo are not drawn. The maintainer has left marks to a
  later touch.
