### Added
- Juniper EX4300-32F and EX4300-48MP, each with its own front panel (`juniper/ex4300-32f` and
  `juniper/ex4300-48mp`, #39). The 32F is the 32-port fibre switch: 32 SFP ports in four gangs of eight, four
  SFP+ uplink ports, two rear QSFP+ ports and a large uplink slot at the left end. The 48MP is the multigigabit
  switch: 24 10/100/1000BASE-T and 24 100/1000/2500/5000/10000BASE-T PoE++ ports and four dedicated rear QSFP+
  ports. Each has its front and rear panels and its builds as orderable configurations: the EX4300-32F,
  -32F-DC and -32F-S (the -TAA SKUs as extra part numbers of the first two) and the EX4300-48MP and -48MP-S.
- The EX4300-48MP's own field-replaceable parts, family-prefixed: the 1400 W AC power supply JPSU-1400-AC-AFO
  and the fan module EX4300-48MP-FAN (`juniper/ex4300-jpsu-1400-ac-afo`, `juniper/ex4300-48mp-fan-afo`), the
  uplink slot cover panels of both models (`juniper/ex4300-32f-uplink-blank`, `juniper/ex4300-48mp-uplink-blank`)
  and the 48MP's Factory Reset/Mode button (`juniper/ex4300-48mp-mode-button`). The other supplies and fan
  modules are the EX4300 parts already in the library.
- The DCIM device types for the five orderable builds, in the NetBox and Nautobot exports, and the module types
  for the new supply, fan module and cover panels.
