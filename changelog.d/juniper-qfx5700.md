### Added
- Juniper QFX5700 (Refs #39), as `juniper/qfx5700`: a modular 5RU, 12.8 Tbps data-centre switch with two Routing and Control
  Board slots and nine line-card slots (FPC 0 to 7 and the unsupported slot 8) on the port side, and four 3000 W supply bays
  over two fan trays at the rear, from the QFX5700 Switch Hardware Guide (2026-09-30) and the datasheet (1000719-009,
  September 2024). One device. Its AC build (QFX5700-BASE-AC), DC build (QFX5700-BASE-DC), the QFX5700E builds
  (QFX5700E-BASE-AC and QFX5700E-BASE-DC, which differ only in an internal board no face shows) and spare chassis
  (QFX5700-CHAS) are orderable configurations, and each exports as a DCIM device type. The base configuration ships one
  routing board, two supplies and a blank over every other slot. The line cards (QFX5K-FPC-16C, QFX5K-FPC-20Y and
  QFX5K-FPC-4CD) are not modelled yet: every slot shows its blank. New components under `juniper/`: `qfx5700-rcb`,
  `qfx5700-rcb-blnk`, `qfx5700-fpc-blnk`, `qfx5700-psu-blank` and `qfx5700-fan`. The supplies are the existing
  `qfx5230-jnp-3000w-ac-afo` and `qfx5230-jnp-3000w-dc-afo`, which carry the same Juniper part numbers.
