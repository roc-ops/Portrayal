### Added
- `nokia/fx-16-dc-pole@1`, one dual-post terminal of the 7360 ISAM FX-16 shelf's power distribution unit: two studs on the 5/8 in.
  centres of the lug the installation manual names, a pair that one two-hole lug lands across (`stud-pair-5-8`, mate
  `generic/two-hole-lug-5-8@1`). The thread of the studs is not stated by any document held, and the part does not claim one.
- `nokia/fx-16-dc-terminal-block@1`, the four -48 VDC terminals TB1-1 to TB1-4 of that shelf, composed as four of those poles
  turned to the slant the shelf's elevation draws, with two DC input ports, `feed-a` (TB1-1 battery, TB1-2 return) and `feed-b`
  (TB1-4 battery, TB1-3 return), each stating -48 V nominal, 70 A and 2 AWG as the unit data sheet prints them.

### Changed
- The 7360 ISAM FX-16 shelf (`nokia/nfxs-d-ba`, 1.0.5 to 1.1.0, a minor) places that block instead of drawing the terminals as
  sixteen loose nut and post shapes in its front panel, so the shelf now offers two DC feeds a lug lands on. The drawing keeps the
  same nuts and posts and gains a small screw head on each of the eight studs. The lint warning about the decor terminals (L197)
  is gone for the shelf; twelve L21 warnings, for shroud outlines the block's nut boxes touch, are recorded in the lint baseline.
