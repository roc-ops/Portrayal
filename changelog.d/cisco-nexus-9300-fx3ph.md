### Added
- Cisco Nexus 9000 fixed switches, batch 5: `cisco/n9k-c9348gc-fx3ph` (Nexus 9348GC-FX3PH, 48 x
  PoE/PoE+/PoE++ copper, 40 at 10M/100M/1G and 8 at 10M/100M, 4 x SFP28 and 2 x QSFP28) and
  `cisco/n9k-c92348gc-fx3` (Nexus 92348GC-FX3, 48 x 10M/100M/1GBASE-T, 4 x SFP28 and 2 x QSFP28).
  Each is 1 RU with port-side intake and port-side exhaust builds: eight supply and airflow
  combinations for the 9348GC-FX3PH (350 W AC, 1900 W AC, 350 W PHV and 440 W DC) and six for the
  92348GC-FX3 (no 1900 W). Two DCIM device types are exported: `N9K-C9348GC-FX3PH` (ports 41 to 48
  typed `100base-tx`) and `N9K-C92348GC-FX3`. No new components: both reuse the supplies, fan module
  and kits of the 9348GC-FX3.
