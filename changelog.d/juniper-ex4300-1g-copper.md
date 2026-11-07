### Added
- Juniper EX4300 1G copper switches, one device per front panel: `juniper/ex4300-24t`,
  `juniper/ex4300-24p`, `juniper/ex4300-48t` and `juniper/ex4300-48p` (#39). Each has its
  front and rear panels, and its power, airflow and spare-chassis builds as orderable
  configurations: the EX4300-24T, -24T-S, -24P, -24P-S, -48T, -48T-AFI, -48T-DC, -48T-DC-AFI,
  -48T-S, -48P and -48P-S.
- The EX4300's field-replaceable units, family-prefixed: the fan modules EX4300-FAN and
  EX4300-FAN-AFI, the power supplies JPSU-350-AC-AFO-A, JPSU-350-AC-AFI-A, JPSU-715-AC-AFO-A,
  JPSU-1100-AC-AFO-A, JPSU-550-DC-AFO-A and JPSU-550-DC-AFI-A, the power supply and uplink
  module slot cover panels, the mini-USB console port and the LCD panel buttons
  (`juniper/ex4300-*`).
- The DCIM device types for the eleven EX4300 part numbers, in the NetBox and Nautobot
  exports, and the module types for the supplies, fan modules and cover panels.

### Changed
- The DCIM exporter types the EX4300's mini-USB console port as a `usb-mini-b` console
  port. No existing export changes.
