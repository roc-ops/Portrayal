### Changed
- The door of the Chatsworth Motive 32612 single-sided vertical cable manager (10 in, black and Glacier White) now draws
  what the maker's pictures show.
  It has two vertical seams that divide the front into three panels.
  It has a plate down its upper part, silver on the white part and a lighter grey on the black one.
  The plate's corners are rounded as each picture shows.
  The place of the maker's mark is reserved at the plate's top and left unpainted.
  The figures are estimates read from the data sheet's page 1 photograph of the right-hand manager.
  That manager is read as a 10 in part, because no page prints its width.
  The right seam is read from the picture, not mirrored from the left.
- The other eight doors (32610, 32611, 32613 and 32614) do not draw the plate or the seams.
  Three pictures show them, and measured in millimetres they do not agree at any listed width.
  Each of those devices names the gap.
- Five gaps on each device name what its own frame part draws in a following change.
  They are the end caps, feet, hinge tabs, side plate holes and track rungs.
- The tip of each handle shows at the door's edge on the front of all ten doors.
  The data sheet's render shows one dot, at the right edge.
  The left tip is built as the right tip, as no picture shows it.
- The back of each door is drawn on the part's rear, left and right faces.
  It shows the two blue latches the installation instructions describe: a housing and a round handle at each side edge.
  They sit about half way down the door.
  The housing is drawn at the proportion measured on the installation figure, 4.7 to 1.
  The rear housing is 17 by 80 and the side housing 15 by 70.5.
  The sizes are stand-ins.
- Each door component takes a minor version and each device a patch version.
  The `door-features` gap of each device is replaced by a `door-hook` gap.
  No held picture shows the hook on the inside of the front door.
- This closes no row of the cable-manager list.

### Added
- A test that the 10 in door skin draws the seams and the rounded plate at the places read from the photograph.
  It checks that the other widths do not draw them and name the gap.
  It checks that every door has both handle tips.
  It checks that the device draws the latches at the measured proportion, on the rear and on both sides.
  It checks that the hook stays a gap.
