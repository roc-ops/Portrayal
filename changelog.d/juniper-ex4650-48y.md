### Added
- Juniper EX4650-48Y (`juniper/ex4650-48y`), a 1RU 25 GbE campus core and aggregation switch (Refs #39). It has
  48 SFP28 and 8 QSFP28 ports on the port side, and at the rear the console, two RJ-45 management ports, a USB
  port, the four chassis lamps, five fan modules and two power supplies. Its AC and DC, front-to-back and
  back-to-front builds are orderable configurations: EX4650-48Y-AFO, -AFI, -DC-AFO and -DC-AFI.
- The DCIM device types for those four builds, in the NetBox and Nautobot exports. No component is added: the
  device seats the QFX5120-48Y's fan modules and AC supplies and the QFX5100's DC supplies, each by its Juniper
  part number.
