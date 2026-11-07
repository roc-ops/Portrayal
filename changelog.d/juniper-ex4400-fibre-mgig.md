### Added
- Juniper EX4400 fibre and multigigabit switches: `juniper/ex4400-24x`, `juniper/ex4400-48f`,
  `juniper/ex4400-24mp` and `juniper/ex4400-48mp`, each a 1RU switch with its front and rear drawn
  from the hardware guide's renders. The EX4400-24X has 24 SFP/SFP+ cages in 12 columns and carries
  its console, management, USB-A and two QSFP28 ports on the front. The EX4400-48F has 36 SFP and
  12 SFP/SFP+ ports. The EX4400-24MP and EX4400-48MP are the multigigabit PoE models, with 24 and
  48 RJ-45 ports (the 48MP has 36 at 2.5 Gbps and 12 at 10 Gbps). The 24X and 48F have orderable
  configurations `ac`, `afi`, `dc` and `dc-afi` (EX4400-24X, -24X-AFI, -24X-DC, -24X-DC-AFI and the
  48F equivalents), and the 48F adds `s` (EX4400-48F-S). The 24MP and 48MP have `ac` and `s`
  (EX4400-24MP, -24MP-S, -48MP and -48MP-S). Each device also has example configurations that
  seat an extension module and a second power supply. The parts are the ones the EX4400 copper
  switches already use, so no component is added.
- The DCIM exports gain one device type for each of the 13 orderable configurations of these four
  switches.
