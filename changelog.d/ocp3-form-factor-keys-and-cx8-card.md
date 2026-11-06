### Added
- **Four OCP NIC 3.0 card-slot keys** (`docs/cards-by-interface-design.md`).
  `spec/schemas/connectors.yaml` gains the interface keys `ocp3-sff`,
  `ocp3-tsff`, `ocp3-dsff` and `ocp3-tdsff`, each pointing at an entry of the same
  name in `spec/schemas/standards.yaml`. The entries carry the card outline from
  the OCP NIC 3.0 Design Specification, version 1.6.0, Table 5 (page 25):
  76.00 x 115.00 for SFF and TSFF, 157.55 x 115.00 for DSFF and TDSFF, at
  `confidence: verified`; the Z-heights (11.50 and 14.20) and the connector counts
  are in each entry's text, which has no key for them. The specification is
  published under the Open Compute Project Hardware License (Permissive) 1.0.
  The deprecated large form factor is not registered. A tall slot takes the
  small card mechanically (section 2.1.2, page 26) and a dual slot is two small
  slots with a removable guide rail (section 2.1.3, page 27); the key notes say so.
- **NVIDIA ConnectX-8 C8180P** (`nvidia/c8180p-ocp3-tsff`), the OCP 3.0 tall
  small form factor SuperNIC with one OSFP cage, 900-9X85E-00EX-MJ0. Drawn from the
  manual's figures; the partner-cooled card is a separate part number and is
  not modelled. It is seated in no device.

### Changed
- `spec/tests/test_cards_by_interface.py` and `spec/tests/test_connector_slots.py`
  expect the four OCP keys in the interface registry and still expect no EDSFF key.
- Dell states that the PowerEdge R660's OCP 3.0 slot is small form factor
  (technical guide, Table 11, page 21). The slot is not changed here: stating its
  key waits until the readers of a bay's list go through `manifest.offers`.
