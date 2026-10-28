### Added
- Cisco Nexus 9000 fixed switches, batch 1: `cisco/n9k-c93180yc-fx3` (Nexus 93180YC-FX3, 48 x SFP28
  and 6 x QSFP28, with the 93180YC-FX3H as configurations of it), `cisco/n9k-c93180yc-fx3s`
  (Nexus 93180YC-FX3S) and `cisco/n9k-c93108tc-fx3` (Nexus 93108TC-FX3, 48 x 10GBASE-T and
  6 x QSFP28). Each is 1 RU with port-side intake and port-side exhaust builds on 650 W or 500 W
  AC, 1200 W HVAC/HVDC and 930 W DC supplies. Four DCIM device types are exported:
  `N9K-C93180YC-FX3`, `N9K-C93180YC-FX3H`, `N9K-C93180YC-FX3S` and `N9K-C93108TC-FX3`. New
  components: the fan modules `cisco/nxa-fan-35cfm` and `cisco/nxa-sfan-35cfm`, the supplies
  `cisco/nxa-pac-500w`, `cisco/nxa-pdc-930w` and `cisco/n9k-puv-1200w`, and the library's Nexus
  9300 rack kits, `cisco/nxk-acc-kit-1ru` and `cisco/nxk-acc-kit2-2ru`, each with its parts.

### Changed
- The DCIM export names a device type from the configuration that states no airflow of its own when
  no configuration is the default or the base, instead of the first one by name. Tests cover the
  ranking and the FX3H type's front-to-rear airflow.
