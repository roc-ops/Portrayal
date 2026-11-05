### Added
- The connector interface `juniper-dc-header-6`, the six-position DC power connector of the Juniper QFX524X-2RU-PWR-DO supply of
  the QFX5241-64OD and QFX5241-64QD. The QFX5241-64OD and QFX5241-64QD Hardware Guide draws it (Figures 22 and 25) as six round
  cells in two rows of three and shows the cord going in with a latch (Figure 35); it calls the cord connector a "six-pin
  female" 2x3 connector with pins P1, P2, S1, S2, P3 and P4. It names no maker, series, pitch or dimension and does not say which
  cell is which pin, so the key claims no standard.
- The connector interface `dc-connector-3w3`, the D-sub 3W3 DC power connector of the Juniper JPSU-1600W-DC-AFO supply of the
  QFX10002 and the QFX5220-128C. The QFX10002 Switch Hardware Guide draws it (Figure 31) as a vertical shell with three contacts
  between two standoffs and says the supplies "require a D-Sub 3W3-type connector". It names the cables, not a connector part,
  and no standard document for the layout is held, so the key claims none.
- `juniper/qfx524x-dc-header@1` and `juniper/qfx10002-dc-header@1` (1.0.0), those connectors as the supplies carry them, each
  drawn at the box the supply's face already showed (sizes are estimates). No document names a part number, so each states none.
- `juniper/qfx524x-dc-plug@1` and `juniper/qfx10002-dc-plug@1` (1.0.0), the cord and cable connectors of Figures 35 and 41, which
  mate them. The guides do not say which wire enters which contact, so neither draws a wire colour at a contact; the wire colours
  of the guides' tables are recorded in the contracts.

### Changed
- `juniper/qfx524x-2ru-pwr-do@1` and `juniper/qfx10002-jpsu-1600w-dc-afo@1` (1.0.0 to 1.1.0) compose their connector, so a cable
  plugs into the supply as a cord plugs into an AC supply's inlet, and say why they state no DC input port yet: a port on a
  connector the supply composes cannot be published at the connector. The roles the guides print for the wires are recorded in
  the contracts. Their drawn faces are unchanged. Their two records in the conformance records go.
- `juniper/qfx5241-64od`, `juniper/qfx5241-64qd`, `juniper/qfx10002-36q`, `juniper/qfx10002-60c`, `juniper/qfx10002-72q` and
  `juniper/qfx5220-128c` take a patch, with their locks and the drawing version line of their exported device types in NetBox and
  Nautobot. No port, interface or id of a device moves.
- The module types of the two supplies, in NetBox and Nautobot, export their power port as `{module}/dc-header`, of type other and
  labelled as the DC power connector, where they exported `{module}/Inlet`. A DCIM that imported the earlier type keeps the old
  port until it is re-imported.
- The exporter types each new header's power port `other` with its label, as it does the Oscilloquartz header.
