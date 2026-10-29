### Added
- Cisco Nexus 9000 fixed switches, batch 4: `cisco/n9k-c9364d-gx2a` (Nexus 9364D-GX2A, 64 x 400G
  QSFP-DD and 2 x 10G SFP+) and `cisco/n9k-c9348d-gx2a` (Nexus 9348D-GX2A, 48 x 400G QSFP-DD and
  2 x 10G SFP+). Each is 2 RU with an out-of-band block (console, RJ-45 and SFP management, USB)
  on the port side, four fan modules and two power supplies on the other. The 9364D ships
  port-side intake with AC or DC supplies; the 9348D adds a port-side exhaust AC build. Two DCIM
  device types are exported: `N9K-C9364D-GX2A` and `N9K-C9348D-GX2A`. New components: the fan
  module `cisco/nxa-sfan-160cfm2` and the supplies `cisco/nxa-pac-3200w` and
  `cisco/nxa-pdc-3200w`, which add three DCIM module types. The two devices' L29 lint warning (the
  guides print no per-fan power) is recorded in `library/lint-baseline.json`.
