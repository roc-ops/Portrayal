### Added
- The connector interface `juniper-qfx5210-dc-header-3`, the three-position DC power header of the Juniper QFX5210 DC supplies. The
  QFX5210 Switch Hardware Guide draws it (Figures 19 and 32, where it is called the "Terminal block") as a keyed shroud with three
  round cells numbered 1, 2 and 3 and no pole printed at any cell. It names no maker, series, pitch or dimension, so the key claims
  no standard.
- `juniper/qfx5210-dc-header@1` (1.0.0), that header as the supplies carry it, drawn at the box their faces already showed (10.9 by
  29.9, an estimate). No document names its part number, so it states none.
- `juniper/qfx5210-dc-plug@1` (1.0.0), a stand-in for the cable connector, which no figure draws. It mates the header and its three
  wires are plain grey, because no document states a wire colour or which pole a cell carries.

### Changed
- `juniper/qfx5210-jpsu-1100w-dc-afi@1` and `juniper/qfx5210-jpsu-1100w-dc-afo@1` (1.0.0 to 1.1.0) compose the header, so a cable
  plugs into the supply as a cord plugs into an AC supply's inlet, and say why they state no DC input port yet: no cell has a
  printed role. Their drawn faces are unchanged. Their two records in the conformance records go.
- `juniper/qfx5210-64c` (0.1.3 to 0.1.4) takes a patch, with its lock and the drawing version line of its exported device types in
  NetBox and Nautobot. No port, interface or id of the device moves.
- The module types of the two supplies, in NetBox and Nautobot, export their power port as `{module}/dc-header`, of type other and
  labelled as the DC power header, where they exported `{module}/Inlet` of type dc-terminal. A DCIM that imported the earlier type
  keeps the old port until it is re-imported.
- The exporter types the new header's power port `other` with its label, as it does the other vendor headers.
