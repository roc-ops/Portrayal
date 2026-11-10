### Changed
- The ports on ten generic transceiver shapes now join a port group named for the cage family, so a port on a module
  seated in a cage says what it is for. The groups are `sfp` (`sfp-lc`, `sfp-sc`, `sfp-sc-key-up`), `qsfp` (`qsfp-lc`
  major 2, `qsfp-lc-simplex`, `qsfp-mpo`), `qsfp-dd` (`qsfp-dd-lc` major 2, `qsfp-dd-mpo16`) and `osfp` (`osfp-lc`,
  `osfp-mpo16`), each with role `traffic`, media `fiber` and counted from 1. No group states a speed: a shape stands for
  every module of its kind, and rate, reach and watts stay on the vendor's wrapper. Part ids, positions and drawn
  geometry are unchanged; each contract takes a minor. No device, rack or lab places these shapes, so no device version
  moves. No conformance row is closed or opened.
