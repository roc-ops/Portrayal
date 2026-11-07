### Added
- Juniper QFX5120-32C (`juniper/qfx5120-32c`) and QFX5120-48T (`juniper/qfx5120-48t`), the next two models of
  the QFX5120 line after the 48Y and 48YM (Refs #39). The 32C is a 1RU leaf switch with 32 QSFP28 and two SFP+
  ports, its management and console ports on the port side, one power supply at each end of the rear and six
  fan modules between them. The 48T is a 1RU access switch with 48 10GBASE-T and six QSFP28 ports, with the
  timing ports PPS OUT and 10M OUT at the rear. Each has its front and rear panels, and its AC and DC,
  front-to-back and back-to-front builds are orderable configurations: QFX5120-32C-AFO, -AFI, -DC-AFO and
  -DC-AFI, and QFX5120-48T-AFO, -AFI, -DC-AFO and -DC-AFI.
- The DCIM device types for those eight builds, in the NetBox and Nautobot exports. No component is added:
  the 32C seats the QFX5200-48Y's fan modules and supplies and the 48T the QFX5120-48Y's fans and AC supplies
  and the QFX5100's DC supplies, each by its Juniper part number.
