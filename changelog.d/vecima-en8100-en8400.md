### Added
- The Vecima Entra EN8100 and EN8400 Remote PHY nodes (`vecima/en8100` and `vecima/en8400`, each 1.0.0, maturity
  `draft`, written `mount: strand`). Each is a finned cast housing that opens along its middle into a base half and a lid half, and
  states it under `chassis.halves`: the base's outer face, the lid's hinge side, the angle the figures draw it open at and how far
  each half stands. Every module bay of the open drawing belongs to the half of the one region that holds it, so the exported
  module bays say whether they are in the base or the lid. The open drawing shows the housing as the guide and the maker's drawing
  of the node show it: the rim with its gasket, ten bolts to a half, the hinge knuckles, the black finned strip of the lid, and on
  the amplifier modules the orange AC shunt connectors, the black connector blocks, the blue test-port leads and the RF circuit
  lines; the closed faces show the stepped fin fields, the three numbered closure bolts, the hinge and the strand clamps. Three
  arrangements are configurations: 2x4 with and without the forward injection module, and 1x2 with one access module. The EN8400
  is the same housing with its own two port entry modules (`vecima/en8400-pem-rf@1` and `vecima/en8400-pem-ac@1`, screwless
  seizures, rated to 1.8 GHz) and an orange 1.8 GHz label. Twelve components are new for the EN8100 and two for the EN8400. The
  external ports are drawn as the plugs that close them and the ports under the plugs are not modelled; no module size or part
  number is held for either node, so every one is declared an estimate. Twenty-six DCIM export files are new, none changed.
