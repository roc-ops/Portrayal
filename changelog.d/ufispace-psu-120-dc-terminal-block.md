### Changed
- The UfiSpace 120 W DC fixed dual-feed supply (`ufispace/psu-120-dc@1`, 1.0.1 to 1.1.0) composes its three terminal screws as
  parts, each a seat a ring lug lands on, and states one DC input port: three poles carrying the legend the panel prints under
  the block (`rtn` on the left, `batt` in the middle, `gnd` for the earth symbol on the right), the datasheet's input current of
  4.5 A and the guides' cable size of 18 AWG. The port states no voltage, because the documents give a range without a nominal,
  and the earth pole is no conductor of a feed. The supply's drawing is unchanged.
- The S9502-12SM takes a minor (3.1.1 to 3.2.0): it places that supply twice, so the build now publishes a DC port for each
  feed. The S9502-16SMT takes a minor (2.0.2 to 2.1.0): its six panel posts, drawn as decor, are now the same two supplies
  (the posts widen from 4.83 to 6.4 mm, the width the supply measures on the S9502-12SM render and near the 6.1 mm the S9502-16SMT
  photograph reads), and its note on the missing terminal-block part is reworded. The lock and the drawing version line of their
  exported device types move with them, and the supply's module type carries contract version 1.1.0. Three rows of the records
  file are gone and its `cap:` is 76.
