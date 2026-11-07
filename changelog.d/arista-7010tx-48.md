### Added
- Arista as a maker, with its first device, the 7010TX-48 (`arista/7010tx-48`, #1204): a 1RU switch with
  48 10/100/1000BASE-T ports and four 1/10/25G SFP ports, its front and rear panels and its AC and DC
  rears. Its AC, DC, front-to-back and back-to-front builds are orderable configurations: DCS-7010TX-48-F,
  -R, -DC-F and -DC-R, and the 7010TX-48C part numbers of the same four.
- The 7010TX-48's field-replaceable fan module FAN-7010X, which reverses by turning, and its two-pole DC
  terminal block, family-prefixed (`arista/7010tx-fan`, `arista/7010tx-dc-terminal`). The power supplies
  are built into the chassis and are not bays.
- The DCIM device types for the four 7010TX-48 builds (DCS-7010TX-48-F, -R, -DC-F and -DC-R; the exporter
  writes one type per configuration), in the NetBox and Nautobot exports, and the module type for FAN-7010X.
