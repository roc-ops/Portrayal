### Added
- Juniper EX9204, EX9208 and EX9214 (#39): the three EX9200 modular chassis, from their hardware guides (2025-08-12 and
  2025-07-28) and the EX9200 datasheet (Aug 2022), one device per chassis. The base, redundant, AC, DC, TAA, bundle and
  spare (-CHAS3-S) builds are configurations, each part number exporting as a DCIM device type. Each chassis seats the
  craft interface, the EX9200-SF, -SF2 or -SF3 Switch Fabric modules with their EX9200-RE or -RE2 Routing Engines, the
  2520 W AC and 2400 W DC supplies (EX9204, EX9208) or the 4100 W AC and DC supplies (EX9214), and blanks in the line
  card slots. The fan tray and air filter of the EX9204 and EX9208 are the MX240 and MX480 parts; the EX9214 fan tray and
  air filter tray are new. The EX9200 line cards are not modelled. New parts: juniper/ex9204-craft, ex9208-craft,
  ex9214-craft, ex9200-sf, ex9200-sf2, ex9200-sf3, ex9200-re, ex9200-re2, ex9200-lc-sf-blank, ex9200-pwr-mx480-2520-ac,
  ex9200-pwr-mx480-2400-dc, ex9214-pwr-mx960-4100-ac, ex9214-pwr-mx960-4100-dc, ex9214-ffantray-mx960-hc and
  ex9214-fltr-kit-mx960.
