### Added
- The connector interface `latch-header-3`, the three-position keyed latching power header of the Oscilloquartz OSA 5420 and
  OSA 5421 -48 VDC supplies, printed "- Gnd +". The OSA 5420/5421 Installation and Commissioning Manual draws it and tables its
  pins (pin 3 the -48 VDC battery, pin 2 ground, pin 1 the return) and names no maker, series, pitch or dimension, so the key
  claims no standard.
- `oscilloquartz/osa542x-dc-header@1` (1.0.0), that header as the supplies carry it, drawn at the box their faces already showed
  (13.7 by 10.3, an estimate). No document names its part number, so it states none.
- `oscilloquartz/osa542x-dc-plug@1` (1.0.0), the cable connector of the manual's Figure 15, which mates it, wired battery, ground
  and return left to right as the supply prints them.

### Changed
- `oscilloquartz/osa542x-psu-dc-40w@1` and `oscilloquartz/osa542x-psu-dc-90w@1` (1.0.0 to 1.1.0) compose the header, so a cable
  plugs into the supply as a cord plugs into an AC supply's inlet, and say why they state no DC input port yet: a port on a
  connector the supply composes cannot be published at the connector. The roles from the manual's pin table are recorded in the
  contract for that port. Their drawn faces are unchanged. Their two records in the conformance records go.
- The four OSA 542x devices (`oscilloquartz/osa-5420-quartz`, `-5420-quartz-hq-plus`, `-5421-quartz-hq-plus-plus` and
  `-5421-rubidium`, 0.1.3 to 0.1.4) take a patch, with their locks and the drawing version line of their eight exported device
  types in NetBox and Nautobot. No port, interface or id of a device moves.
- The module types of the two supplies, in NetBox and Nautobot, export their power port as `{module}/dc-header`, of type other and
  labelled as the latching header, where they exported `{module}/Inlet` of type dc-terminal. A DCIM that imported the earlier type
  keeps the old port until it is re-imported.
- The exporter types the new header's power port `other` with its label, as it does the bus-bar clip.
