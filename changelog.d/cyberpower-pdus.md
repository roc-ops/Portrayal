### Added
- CyberPower PDU30BHVT8R and PDU81001G rack PDUs, each with six views. The PDU30BHVT8R is a 1U basic PDU, 445 x 44 x 38 mm: six IEC C13 and
  two C19 outlets in two banks on the rear, a breaker for each bank, an external site ground and a fixed 10 ft cord with a NEMA L6-30P plug, and
  a front with two bank lamps. The PDU81001G is a 1U switched metered-by-outlet PDU, 433 x 44 x 112 mm: eight NEMA 5-15R outlets with a lamp
  each, a fixed 12 ft cord with a NEMA 5-15P plug, a display, a navigation button, two USB jacks, two Ethernet jacks, and two further RJ45
  jacks printed ENV and Serial/Link. No document shows the PDU81001G's rear, which is left as stated unshown. Its positions are read off an
  angled photograph and are estimates; the PDU30BHVT8R's rear is read off a line drawing and its front off a straight-on photograph. This closes
  no row of the port records.
- Parts for them: `cyberpower/pdu-bank-led@1`, `cyberpower/pdu-cord-l6-30p@1`, `cyberpower/pdu-cord-5-15p@1`, `cyberpower/pdu-lcd@1` and
  `cyberpower/pdu-joystick@1`. Sizes no document gives are declared estimates in each contract. The maker is registered as `cyberpower`.

### Changed
- `std/nema-5-15r@1` is placed now, by the PDU81001G, so its note that no PDU seats it is removed.
