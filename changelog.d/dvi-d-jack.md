### Added
- The connector key `dvi-d`, the DVI-D video receptacle (three rows of eight contact cells and the flat blade slot, no analogue pins),
  and `std/dvi-d-jack@1`, the standard-library part that presents it, with a `dvi-d` entry in the standards registry. No DVI
  standard document is held, so the part's size and its contact layout are read off the labelled rear photograph in the Raritan
  Dominion SX II data sheet and declared estimated. No plug or cable part comes with the key.
- DCIM: the exporter records why a video jack is not a DCIM port, as it does for VGA.

### Changed
- The Raritan DSX2-32 (0.1.0 to 0.2.0) places the jack between its two thumbscrews and no longer lists the DVI-D jack as a gap, with
  its lock and the drawing version line of its exported device types. Its exported ports and interfaces do not move.
  This closes no row of the port records, and adds one: the jack's slot has no plug part to mate it yet.
