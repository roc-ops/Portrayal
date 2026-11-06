### Added
- `ufispace/psu-162-dc@2` and `ufispace/psu-202-dc@2` (both 2.0.0), the DC supplies of the UfiSpace S9600-30DX family and of the
  S9600-56DX family, redrawn from the vendor's installation guides: the terminal block projects from the rear face between three
  dark barrier bars, two poles one above the other, each pole a pale metal plate standing square to the face with two screws
  entering it from the left, one behind the other (four screws; version 1 drew one face-on screw to a row). Seen straight at the
  face, the bars and plates show edge-on and one screw of each pole shows side-on. Each supply composes its two poles as parts
  that present the 5/8 in. stud pair a two-hole lug lands across, standing on a relief facet 89 degrees off the face, the
  nearest statement the format has of a surface square to it, and states one DC input port: `batt` on the upper pole (the cable the guides mark -40 to -72) and `rtn` on the lower
  (the cable marked RTN), the cable size every guide of the supply prints (6 AWG) and the input current every datasheet of its
  devices prints (50 A, 60 A). The port states no voltage, because the documents give a range without a nominal. The block's own
  spacing, the screws' positions, how far the block projects and their height off the face are declared estimates, and each
  device that seats a supply says so in a `dc-terminal-height` gap that names the drawing wanted. The PSU-162's block is drawn
  wider than version 1's, and its legend of "+" over "-", which the guide does not show, is not drawn. The format has no seat
  that faces a side, so a lug landing from the side is still drawn face-on.

### Changed
- Nine devices take a minor: the S9600-30DX, S9600-32X and S9600-64X seat `ufispace/psu-162-dc@2` in their DC builds, and the
  S9600-56DX, S9610-46DX, S9610-48DX, S9700-23D, S9700-53DX and S9705-48D seat `ufispace/psu-202-dc@2`; every supply bay still
  accepts `@1` beside it. The build now publishes a DC port for each of these supplies; the locks and the drawing version line of
  their exported device types move with them, and the two supplies' module types carry contract version 2.0.0. Two rows of the
  records file are gone.
- `ufispace/psu-162-dc@1` and `ufispace/psu-202-dc@1` each take a patch and say `superseded-by` their `@2`. Their drawings are
  unchanged, the supply bays still accept them, and a manifest that pins `@1` still resolves to it; neither is exported as a
  module type any longer, because `@2` carries the same part number.
