### Added
- `juniper/ex4400-dc-header@1` (1.0.0), the D-sub 3W3 DC power connector of the Juniper JPSU-550-C-DC-AFO supply of the EX4400, as
  the supply carries it, drawn at the box the supply's face already showed (its size is an estimate). The EX4400 Switch Hardware
  Guide says its DC supplies "require a D-Sub 3W3- type connector", names the cable CBL-JNP-PWR-DSUB that the QFX10002 Switch
  Hardware Guide names for the same connector, and draws it on the supply (Figure 10). It names no maker or part number and prints
  no mark beside a contact, so the part states none and gives no contact a role.

### Changed
- The connector interface `dc-connector-3w3` now also covers the EX4400 supply's connector, and the cable connector
  `juniper/qfx10002-dc-plug@1` mates it too. No key is added.
- `juniper/jpsu-550-c-dc-afo@1` (1.0.0 to 1.1.0) composes its connector, so a cable plugs into the supply as a cord plugs into an
  AC supply's inlet, and says why it states no DC input port yet: a port on a connector the supply composes cannot be published at
  the connector. The connector is no longer drawn in the supply's own art; the part draws it in the same shapes and colours at the
  same place. One record of the conformance records goes.
- `juniper/ex4400-24t`, `-24x`, `-48f` and `-48t` take a patch, with their recorded component versions and the drawing version
  line of their exported device types in NetBox and Nautobot. No port, interface or id of a device moves.
- The module type of the supply, in NetBox and Nautobot, exports its power port as `{module}/dc-header`, of type other and labelled
  as the DC power connector, where it exported `{module}/Inlet`. A DCIM that imported the earlier type keeps the old port until it
  is re-imported.
- The exporter types the new header's power port `other` with its label.
