### Added
- `ufispace/psu-302-dc@2` and `ufispace/psu-132-crps-dc@2` (both 2.0.0), the DC supplies of the UfiSpace S9321-64E family and of
  the S9601-104BC, redrawn from the vendor's installation guides: each terminal block is two poles, each pole a pair of screws that
  one two-hole lug lands across (version 1 drew one ring to a pole on the PSU-302 and four pads 7.2 mm apart on the PSU-132 CRPS).
  The pitch is read from the lug each guide dimensions, whose two holes are .63 +/- .02 in. apart, which holds 5/8 in. Each supply
  composes its two poles as parts that present the stud pair a two-hole lug lands across, and states one DC input port with the
  input current every datasheet of its devices prints (80 A, 37 A). The PSU-302 states no polarity, because no held figure marks
  either pole, so its poles are `unstated` and each device that seats it says so in a `dc-polarity` gap; the PSU-132 CRPS takes
  `rtn` and `batt` from the letters of its guide's Figure 6. Neither port states a voltage, because the documents give a range
  without a nominal, and the PSU-132 CRPS port states no cable size, because its guide prints two. The block's spacing, the screws'
  ring size and their height are declared estimates.

### Changed
- Eight devices take a minor: the S9321-64E, S9321-64EO, S9610-36D, S9611-36D, S9710-76D, S9720-56ED and S9725-64E seat
  `ufispace/psu-302-dc@2` in their DC builds, and the S9601-104BC seats `ufispace/psu-132-crps-dc@2`; every supply bay still
  accepts `@1` beside it. The build now publishes a DC port for each of these supplies; the locks and the drawing version line of
  their exported device types move with them, and the two supplies' module types carry contract version 2.0.0. Two rows of the
  records file are gone.
- `ufispace/psu-302-dc@1` and `ufispace/psu-132-crps-dc@1` each take a patch (1.0.2 to 1.0.3) and say `superseded-by` their `@2`.
  Their drawings are unchanged, the supply bays still accept them, and a manifest that pins `@1` still resolves to it; neither is
  exported as a module type any longer, because `@2` carries the same part number.
