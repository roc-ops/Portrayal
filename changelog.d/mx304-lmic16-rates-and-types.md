### Changed
- **The Juniper MX304 LMIC16 states each cage's native rates, and its module
  type exports each port by its rate.** Ports 0, 6, 8 and 14 publish
  `data-speeds="100g 400g"`, ports 1, 3, 5, 7, 9, 11, 13 and 15 publish
  `40g 100g`, and ports 2, 4, 10 and 12 stay single-rate, all from the hardware
  guide's port-speed table (breakout modes are not recorded). Every placement
  now states `media: qsfp-dd`, and `PART_MEDIA` gains the row
  `("qsfp-dd", "100g")`: a QSFP-DD cage placed at 100G takes a QSFP28 optic, so
  the twelve 100G ports of the NetBox and Nautobot module types export as
  `100gbase-x-qsfp28` instead of `400gbase-x-qsfpdd`. The four 400G ports and
  every port name are unchanged.
