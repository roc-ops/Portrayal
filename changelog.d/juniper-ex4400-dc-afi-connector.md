### Changed
- `juniper/jpsu-550-c-dc-afi@1` (1.0.0 to 1.1.0), the back-to-front 550 W DC supply of the Juniper EX4400, composes the D-sub 3W3
  connector part `juniper/ex4400-dc-header@1` that the front-to-back supply already composes, at the place that supply places it,
  so a cable plugs into this supply too. The connector is no longer drawn in the supply's own art; the part draws it in the same
  shapes and colours at the same place. The EX4400 Switch Hardware Guide gives the two 550 W DC supplies one set of figures and
  draws only the front-to-back unit, so the connector's size and place are borrowed from it and stay estimates. The supply states
  no DC port, for the reason the front-to-back supply gives. One record of the conformance records goes.
- `juniper/ex4400-24t`, `-24x`, `-48f` and `-48t` take a patch, with their recorded component versions and the drawing version
  line of their exported device types in NetBox and Nautobot. No port, interface or id of a device moves.
- The module type of the supply, in NetBox and Nautobot, exports its power port as `{module}/dc-header`, of type other and labelled
  as the DC power connector, where it exported `{module}/Inlet`. A DCIM that imported the earlier type keeps the old port until it
  is re-imported.
