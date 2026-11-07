### Added
- Juniper QFX10002-36Q and QFX10002-72Q (Refs #39), as `juniper/qfx10002-36q` and `juniper/qfx10002-72q`: fixed 2RU
  deep-buffer spine and core switches with 36 or 72 QSFP+ ports (every second and sixth cage position of each
  six-port cage takes QSFP28), a management panel with RJ-45 management and console ports, two SFP ports, 1PPS and
  10 MHz connectors, a USB port and four status lamps, and a rear with four power supply bays and three fan modules,
  from the QFX10002 Switch Hardware Guide (2026-02-11). Each model is one device. Its AC build, its DC build
  (QFX10002-36Q-DC and QFX10002-72Q-DC) and its spare chassis (QFX10002-36Q-CHAS-S and QFX10002-72Q-CHAS-S) are
  orderable configurations, and each exports as a DCIM device type. The 36Q ships two supplies and two blanks. New
  components under `juniper/`: `qfx10002-jpsu-1600w-ac-afo`, `qfx10002-jpsu-1600w-dc-afo`, `qfx10002-fan-afo` and
  `qfx10002-pwr-blnk`. The QFX10002-60C is not modelled yet.
