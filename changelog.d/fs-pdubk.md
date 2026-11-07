### Added
- **FS FS-PDUBK** (#939, `fs/fs-pdubk`): the vertical PDU mounting bracket, FS SKU
  #78523, a `rack-side` part of 30 x 88.4 x 135 mm. Its two configurations are the
  quick start guide's two ways to fit it, `front` (the front of the post) and
  `rear` (its rear side). Each publishes three `pdu-button` slots in `configs.json`,
  26.3 mm up the plate, so a PDU now hangs on a library bracket: an Eaton EVMI2130X
  on two of them 35U apart fits, and 34U apart is refused with the distance. The
  bracket has no data sheet of its own; its figures are scaled off the product
  page's dimensioned drawing and marked estimated where they are.
- **`fs/fs-pdubk-keyhole@1`**: the keyhole slot of the FS-PDUBK plate, a part with
  `interface: pdu-button`, which `eaton/g4-mounting-button@1` mates. The bracket also
  adds `fs/fs-pdubk-plate@1`, `fs-pdubk-plate-face@1`, `fs-pdubk-flange@1`,
  `fs-pdubk-flange-face@1`, `fs-pdubk-edge@1` and `fs-pdubk-flange-edge@1`, the sheet
  it is cut in.
