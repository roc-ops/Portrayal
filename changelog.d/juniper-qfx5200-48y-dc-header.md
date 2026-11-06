### Added
- The connector interface `juniper-dc-header-3`, the three-position DC power header of the Juniper QFX5200-48Y DC supplies. The
  QFX5200 Hardware Guide draws it (Figure 42) with its cells numbered 3, 2 and 1 and its wires labelled "Red: RTN", "Black: -36
  -72V" and "Green: Grounding", and shows the cable connector going in (Figure 85). It names no maker, series, pitch or dimension,
  so the key claims no standard.
- `juniper/qfx5200-48y-dc-header@1` (1.0.0), that header as the supplies carry it, drawn at the box their faces already showed
  (10.9 by 28.4, an estimate). No document names its part number, so it states none.
- `juniper/qfx5200-48y-dc-plug@1` (1.0.0), the cable connector of Figure 85, which mates it, wired red, black and green top to
  bottom as the supply numbers its cells.

### Changed
- `juniper/qfx5200-48y-dpsu-ai@1` and `juniper/qfx5200-48y-dpsu-ao@1` (1.0.0 to 1.1.0) compose the header, so a cable plugs into the
  supply as a cord plugs into an AC supply's inlet, and say why they state no DC input port yet: a port on a connector the supply
  composes cannot be published at the connector. The roles from the printed wire labels are recorded in the contract for that
  port. Their drawn faces are unchanged. Their two records in the conformance records go.
- `juniper/qfx5120-32c` (0.1.1 to 0.1.2) and `juniper/qfx5200-48y` (0.1.0 to 0.1.1) take a patch, with their locks and the drawing
  version line of their exported device types in NetBox and Nautobot. No port, interface or id of a device moves.
- The module types of the two supplies, in NetBox and Nautobot, export their power port as `{module}/dc-header`, of type other and
  labelled as the DC power header, where they exported `{module}/Inlet` of type dc-terminal. A DCIM that imported the earlier type
  keeps the old port until it is re-imported.
- The exporter types the new header's power port `other` with its label, as it does the Oscilloquartz header.
