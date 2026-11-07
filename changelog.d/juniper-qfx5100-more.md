### Added
- Juniper (`juniper/qfx5100-24q`): the QFX5100-24Q, a 1RU switch with 24 QSFP+ ports and two expansion
  module bays that ship with cover panels. Eight orderable configurations: QFX5100-24Q-AFO (the default),
  -AFI, -DC-AFO, -DC-AFI, -3AFO, -3AFI, -D-3AFO and -D-3AFI (the last four have a three-port management
  panel). Two example configurations seat two QFX-EM-4Q or two EX4600-EM-8F. The 650 W supplies and fan
  modules are the QFX5100-48S's, and the three bay modules are the EX4600's, reused by part number.
- Juniper (`juniper/qfx5100-96s`): the QFX5100-96S, a 2RU switch with 96 SFP+ ports and 8 QSFP+ ports.
  Four orderable configurations: QFX5100-96S-AFO (the default), -AFI, -DC-AFO and -DC-AFI. It has
  three fan modules and two stacked 850 W supplies, reused by part number from the QFX5120 (AC) and the
  QFX5200 (DC).
- The QFX5100-96S fan modules, each its own component: `juniper/qfx5100-96s-fanafo@1`
  (QFX5100-96S-FANAFO, front-to-back, gold handle) and `juniper/qfx5100-96s-fanafi@1`
  (QFX5100-96S-FANAFI, back-to-front, blue handle).
