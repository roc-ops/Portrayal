### Added
- `std/rj11@1` (1.0.0), the six-position modular jack's plug opening, drawn from TE Connectivity customer drawing C-1775675
  rev C: the 9.88 width and the 20.57 depth are printed, the three tiers (body 9.88 x 6.85, shoulder 6.60 x 1.69, latch slot
  4.04 x 2.72) are scaled off the same front view, and two contacts are loaded. A maker's drawing is its source, and the
  contract says so: IEC 60603-7 governs the plug interface and was not consulted.

### Changed
- `common/rj11-jack@1` (1.2.0 to 1.3.0) composes `std/rj11@1` instead of drawing the opening itself. Its face, its housing
  size, its mate point and its `tel` point are unchanged, so the drawing of the devices that place it is the same. The
  warning that the opening was backed by nothing is gone.
- The `rj11` entry of the standards registry now claims the opening (9.88 wide, 11.26 high, 20.57 deep, three tiers) and no
  housing; it claimed none before. Its source line said the housing is 12.6 high; the drawing prints 12.6 for the housing's
  side lugs and 15.0 for the housing, and the line now says so.
- The Halny HLX-TGV's two rear panel cutouts, `tel-1` and `tel-2`, now restate the RJ11 opening (9.88 x 11.26) as the cutout
  rule requires; they were the whole 14.0 x 13.5 housing. They lie under the jack's housing, so the picture does not change.
  The device takes a major (3.0.0 to 4.0.0): a saved rack that pins it at version 3 no longer matches.
- The Lantronix SLC 8000 (0.3.0 to 0.3.1) and the WTI CPM-800-1, CPM-1600-1 and DSM-8 (each 0.1.0 to 0.1.1) take a patch,
  which is what the version check asks for a composed part that changed under them. This closes no row of the records file.
