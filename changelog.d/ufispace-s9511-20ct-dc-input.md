### Added
- `ufispace/s9511-dc-input@1`, the input of the S9511-20CT's fixed dual-feed DC supply: a three-screw terminal block whose
  screws are parts, each a seat a ring lug lands on, and one DC input port with three poles carrying the legend the panel
  prints under each block (`rtn` on the left, `batt` in the middle, `gnd` for the earth symbol on the right), the 8 A the
  datasheet gives for the DC input and the 14 AWG cable the guide gives. The port states no voltage, because the documents
  give a range without a nominal, and the earth pole is no conductor of a feed. The block is 31.1 x 15.8 mm and projects
  12 mm, the figure the guide gives for the power connectors; the supply states no output rating because neither document
  prints one. It is exported as one new module type.

### Changed
- The S9511-20CT takes a minor (3.0.2 to 3.1.0): its two terminal blocks, drawn as six panel posts, are now two placements of
  that part, `psu-0` and `psu-1`, so the build publishes a DC port for each feed. The posts widen from 3.81 to 6.4 mm and the
  block gains a dark frame and wire entries, as the guide's Figure 6 shows; the device's note on the missing terminal-block
  part is reworded. The lock and the drawing version line of its exported device types move with it. One row of the records
  file is gone.
