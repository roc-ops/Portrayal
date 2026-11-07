### Added
- Juniper (`juniper/ex9251`): the EX9251, a 1RU fixed core and aggregation switch with 8 SFP+ ports, 4
  QSFP28 ports, a GM/PTP SFP cage, the MGMT, CON, BITS and ToD RJ-45 jacks, a USB port and 10MHz and
  1PPS SMB connectors in and out. Three orderable configurations: EX9251-8X4C (AC), EX9251-8X4C-DC and the
  spare chassis EX9251-CHAS, with a base configuration and a single-supply example.
- Juniper (`juniper/ex9253`): the EX9253, a 3RU modular chassis with two Routing Engine slots, two line card
  slots, six power supply slots and four fan trays. Five orderable configurations: EX9253-BASE-AC and
  -BASE-DC (one Routing Engine, three supplies), EX9253-RED-AC and -RED-DC (two Routing Engines, four
  supplies) and the spare chassis EX9253-CHAS-3RU. The line cards (EX9253-6Q12C and -6Q12C-M) are not
  modelled; both line card slots show their blank panels.
- The EX9250 field-replaceable units, each its own component: the EX9251 fan tray
  `juniper/ex9251-fan-1ru@1` (JNP-FAN-1RU) and supply slot blank `juniper/jnp-pwr-blnk-1@1`
  (JNP-PWR-BLNK-1), the EX9253 Routing Engine `juniper/ex9253-re@1` (EX9253-RE), fan tray
  `juniper/ex9253-fan-3ru@1` (JNP-FAN-3RU), supplies `juniper/ex9253-jnp-pwr1600-ac@1` and
  `juniper/ex9253-jnp-pwr1100-dc@1` and blank panels `juniper/ex9253-re-blnk@1`, `juniper/ex9253-lc-blnk@1`
  and `juniper/ex9253-psu-blank@1`, and the EX9250 OFFLINE button `juniper/ex9250-offline-button@1`. The
  EX9251 seats the EX4600's `juniper/ex4600-jpsu-650-ac-afo@1` and `-dc-afo@1` supplies.
