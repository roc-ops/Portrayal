### Added
- Juniper QFX5110 switches, two devices (`juniper/qfx5110-48s`, `juniper/qfx5110-32q`, Refs #39): the
  QFX5110-48S (48 SFP+ and four QSFP28 ports) and the QFX5110-32Q (28 QSFP+ and four QSFP28 ports). Each has
  its front panel with the RJ-45 grandmaster clock jack and the 10 MHz and 1 PPS outputs, and its rear with the
  management panel, five fan modules and two power supplies. Their AC, DC, front-to-back and back-to-front
  builds are orderable configurations: QFX5110-48S-AFO, -AFI, -DC-AFO and -DC-AFI, and QFX5110-32Q-AFO, -AFI,
  -DC-AFO, -DC-AFI and the spare chassis QFX5110-32Q-CHAS, with its supply and fan bays open. The supplies
  already in the library are reused.
- Juniper fan modules for the QFX5110, one per model and airflow as the hardware guide's Table 11 lists them:
  `juniper/qfx5110-48s-fanafo`, `juniper/qfx5110-48s-fanafi`, `juniper/qfx5110-32q-fanafo` and
  `juniper/qfx5110-32q-fanafi`.
- The DCIM device types for the nine QFX5110 builds, in the NetBox and Nautobot exports.
