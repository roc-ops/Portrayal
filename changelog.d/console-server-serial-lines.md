### Changed
- The serial lines of the Opengear CM8004, CM8004-C, CM8008 and CM8008-C and of the Vertiv Avocent ACS8008SAC-400, ACS8016SAC-400,
  ACS8032SAC-400 and ACS8048SAC-400 are console server ports. Opengear's Quick Start Guide gives its serial ports the default mode
  "Console Server"; Vertiv's Installer/User Guide gives its serial ports the Console Access Server profile by default. Each device's
  serial group now states `role: console-server`, so the NetBox and Nautobot device types list the 4, 8, 16, 32 or 48 serial lines
  under `console-server-ports` and not as interfaces. The USB-C console of the CM8000 and the RJ45 console of the ACS8000 stay
  console ports, and no other port group changes. Each of the eight devices takes a patch, with its lock and its two exported device
  types; no port, interface or id that was exported before changes. This closes no row of the conformance records.
