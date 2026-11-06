### Added
- Three connector interfaces for the CH3000's front-panel and RS-232 connectors, each registered with no standard: `g-type`
  (the G-type male -20 dB test point of the CommScope AR3002E, AR3044H, AR3044L and DR3450N receivers), `g-type-female` (the
  DR3600N's) and `stereo-jack` (the RS-232 port of the CX3003C and CX3033N). Each has a port part that presents it
  (`common/g-type-male-port@1`, `common/g-type-female-port@1`, `common/stereo-jack@1`) and a cable end that mates it
  (`common/g-type-female-plug@1`, `common/g-type-male-plug@1`, `common/stereo-plug@1`). No data sheet held gives these
  connectors' dimensions, so every size is an estimate, said in the part. None of the three ports exports as a DCIM port.

### Changed
- The CH3000's 27 passive modules and back plates declare the adapter frames drawn in their skins as class `adapter` instead of
  `port`: the `std/sc-bore@1` openings composed beside them are the ports and present `sc`, so no drawn port stands on a face that
  presents no interface. The AR3002E, AR3044H, AR3044L, DR3450N and DR3600N compose a G-type port at their test point, the HT358xH
  composes `std/mcx@1` at its RF test point, and the CX3003C and CX3033N compose a stereo jack at their RS-232 port. The body
  drawn round each stays as it was, declared as class `bezel`; no id, position, size or skin moves. `commscope/ch3000` takes a
  patch with its lock, and one row of the part-conformance records is gone. The HT358xH module type now exports one interface,
  `rf-tp` (type `docsis`, label MCX), the type the exporter gives every MCX port: a DCIM that imports it again gains that
  interface.
