### Added
- `cisco/nc5k-pdc-930w-dc-header@1`, the DC power connector of the Cisco NC5K-PDC-930W-BK and NC5K-PDC-930W-FR supplies: three grey cells in
  a column, drawn exactly as the supplies' skins drew them, under the existing key `cisco-dc-block-3`, so the cable connector
  `cisco/nxa-pdc-930w-dc-plug@1` mates it. It is the connector of the NXA-PDC-930W drawn at the size of the NCS 5000 supplies' housing, about
  10 by 30 mm where the NXA-PDC-930W's header is about 9 by 16 mm; both sizes are estimates. No guide names a maker or part number for the
  connector, so the part is a declared stand-in and the key claims none.

### Changed
- The Cisco NC5K-PDC-930W-BK and NC5K-PDC-930W-FR supplies (`cisco/nc5k-pdc-930w-bk@1` and `cisco/nc5k-pdc-930w-fr@1`, 1.0.0 to 1.1.0) compose
  that header as the part `dc-header`, and the NC57-1600W-DCFW supply (`cisco/nc57-1600w-dcfw@1`, 1.1.0 to 1.2.0) composes
  `cisco/nxa-pdc-930w-dc-header@1` as `dc-header` inside the dark block its skin draws, so each offers a place a cable lands. The Cisco NCS 5000
  hardware installation guide (Figure 21), the NCS 5700 fixed-port guide (Figure 93) and the Cisco N93108TC-FX3 guide (figure 504148) draw one
  connector: three cells in a column printed -DC, +DC and an earth symbol. The two NC5K supplies' faces are unchanged to the pixel, because the
  three cells moved from their skins into the part. The three contacts and their roles (`neg`, `pos` and `gnd`, top to bottom) are recorded in
  each supply's provenance and no DC port is stated, because the three poles are the contacts of one pluggable connector. Each supply's
  exported power port is `{module}/dc-header` of type `other` where it was `{module}/Inlet` of type `dc-terminal`.
- The five routers that seat them (`cisco/ncs-5001`, `cisco/ncs-5002`, `cisco/ncs-5011`, `cisco/ncs-57c3-mod-hx` and `cisco/ncs-57c3-mod-s`)
  take a patch, with their locks and the drawing version line of their exported device types; the supplies' module types carry the new
  contract version and the new port name. Three rows of the records file are gone.
