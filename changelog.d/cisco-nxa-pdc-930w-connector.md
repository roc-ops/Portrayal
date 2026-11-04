### Added
- The key `cisco-dc-block-3` for the three-position DC power connector of the Cisco NXA-PDC-930W supply, a body with a clip and three
  cells printed "- DC", "+ DC" and an earth symbol (Cisco N93108TC-FX3 hardware installation guide, figure 504148). The guide names no maker or
  part number for it, so the key claims none. `cisco/nxa-pdc-930w-dc-header@1` presents it and `cisco/nxa-pdc-930w-dc-plug@1`, the cable
  connector of the figure, mates it; both are declared stand-ins with estimated sizes.

### Changed
- The Cisco NXA-PDC-930W supply (`cisco/nxa-pdc-930w@1`, 1.0.0 to 1.1.0) composes the connector as the part `dc-header`, standing inside the
  inlet window its skin already draws, so it offers a place a cable lands. The three contacts and their roles (`neg`, `pos` and `gnd`, top to
  bottom, as the supply prints them) are recorded in its provenance and no DC port is stated, because the three poles are the contacts of one
  pluggable connector. The skin is unchanged. The supply's exported power port is `{module}/dc-header` of type `other` where it was
  `{module}/Inlet`.
- The three switches that seat it (`cisco/n9k-c93108tc-fx3`, `cisco/n9k-c93180yc-fx3` and `cisco/n9k-c93180yc-fx3s`) take a patch, with their
  locks and the drawing version line of their exported device types; the supply's module type carries the new contract version and the new
  port name. One row of the records file is gone and its `cap:` is 144.
