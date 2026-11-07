### Added
- Arista 7050SDX4-48D8 (#1204, slice 1): a fixed 1RU switch with 48 100G SFP-DD ports and 8 400G QSFP-DD ports, front and
  rear (`arista/7050sdx4-48d8`), the first device to use the SFP-DD cage. Its -F (front-to-rear) and -R (rear-to-front) builds
  are orderable configurations (DCS-7050SDX4-48D8-F and -R), and a DC build of each is shown as a worked example with no part
  number. It seats the parts other Arista models already carry (PWR-1011 supplies and the FAN-7011M-F and FAN-7011H-R fan
  modules); no new component is added. The DCS-7050SPX4-48D8 (48 DSFP) is left out: the library has no DSFP cage.
- The DCIM device types for the two orderable 7050SDX4-48D8 builds, in the NetBox and Nautobot exports.
