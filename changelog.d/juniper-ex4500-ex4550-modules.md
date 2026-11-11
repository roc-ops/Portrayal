### Added
- The five modules of the Juniper EX4550 and EX4500 switches, one component for each maker part number where the guide prints one:
  `juniper/ex4550-em-8xsfp@1` (eight SFP+ ports), `juniper/ex4550-em-8xt@1` (eight 10GBASE-T ports), `juniper/ex4550-em-2qsfp@1` (two QSFP+
  ports) and `juniper/ex4550-vc-128g@1` (two Virtual Chassis ports) for the EX4550, and `juniper/ex4500-uplink-sfp-plus@1` (four SFP+ ports,
  named by role, as the EX4500 guide prints no part number for it) for the EX4500. Each draws its face from the hardware guide's flat figure,
  with its cages and jacks as the library's own SFP, QSFP and RJ-45 ports, the Virtual Chassis ports as the EX4200's port part, and its lamps as the
  guide numbers them. Each states the weight the guide prints (the EX4500 module has none). No power draw is published, so each declares the figure
  as not published. No photograph of any module is held, so the colours are estimates.

### Changed
- The module bays of the EX4550-32F, EX4550-32T and EX4500-40F take the modules their guides list as well as the cover panel; the cover is still what
  ships. Each device takes a minor, with its lock and the module-bay text and drawing version line of its exported device types. The three devices
  gain `example` configurations, one for each module, so that a face shows it; they are illustrations and add no exported device type. The
  `expansion-modules` and `uplink-modules` gaps become a gap for the module's connector to the chassis, which no key or figure covers.
