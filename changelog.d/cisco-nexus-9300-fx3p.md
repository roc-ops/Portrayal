### Added
- Cisco Nexus 9000 fixed switches, batch 2: `cisco/n9k-c93108tc-fx3p` (Nexus 93108TC-FX3P, 48 x
  100M/1/2.5/5/10GBASE-T and 6 x QSFP28, with the 93108TC-FX3H as configurations of it) and
  `cisco/n9k-c9348gc-fx3` (Nexus 9348GC-FX3, 48 x 100M/1GBASE-T, 4 x SFP28 and 2 x QSFP28). Each is
  1 RU with port-side intake and port-side exhaust builds. Three DCIM device types are exported:
  `N9K-C93108TC-FX3P`, `N9K-C93108TC-FX3H` and `N9K-C9348GC-FX3`. New components: the supplies
  `cisco/nxa-pac-1100w`, `cisco/nxa-pac-1900w`, `cisco/nxa-pdc-715w`, `cisco/nxa-pac-350w`,
  `cisco/nxa-phv-350w` and `cisco/nxa-pdc-440w`, and the fan module `cisco/nxa-sfan-30cfm`. The
  Nexus 9348GC-FXP is not yet modelled.
