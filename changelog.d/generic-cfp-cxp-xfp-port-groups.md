### Changed
- The ports on nine generic transceiver shapes now join a port group named for the form factor, so a port on a module
  seated in a cage says what it is for. The groups are `cfp` (`cfp-lc`, `cfp-mpo`, `cfp-sc`), `cfp2` (`cfp2-lc`,
  `cfp2-mpo`), `cfp4` (`cfp4-lc`, `cfp4-mpo`), `cxp` (`cxp-mpo`) and `xfp` (`xfp-lc`), each with role `traffic`, media
  `fiber` and counted from 1. No group states a speed: a shape stands for every module of its kind, and rate, reach and
  watts stay on the vendor's wrapper. Part ids, positions and drawn geometry are unchanged; each contract takes a minor.
  No device, rack or lab places these shapes and no wrapper composes one, so no device version moves. No conformance row
  is closed or opened.
