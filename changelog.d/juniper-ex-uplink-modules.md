### Added
- The four uplink modules of the Juniper EX3200 and EX4200 switches, one component for each maker part number: `juniper/ex-um-4sfp@1` (four SFP
  ports), `juniper/ex-um-2x4sfp@1` and `juniper/ex-um-2x4sfp-m@1` (the SFP+ module and its MACsec variant: four cages, SFP+ in ports 0 and 2,
  with an operating mode lamp) and `juniper/ex-um-2xfp@1` (two XFP ports). Each states its cages as the library's own SFP and XFP ports and its
  lamps as the hardware guides draw them. The size is the uplink slot's, estimated; no weight or power draw is published, so each carries the
  missing-power warning, which stays in the lint baseline as the record that the figure is missing.

### Changed
- The uplink slot of the four EX3200 and seven EX4200 devices (`ex3200-24t`, `-48t`, `-24p`, `-48p`; `ex4200-24t`, `-48t`, `-24p`, `-48p`, `-24px`,
  `-48px`, `-24f`) takes the modules as well as its cover panel; the cover is still what ships. Each takes a minor, with its lock and the module-bay
  text and drawing version line of its exported device types. The EX3200-24T and EX4200-24T gain four `example` configurations, one for each module, so that a face
  shows it; they are illustrations and add no exported device type. The `uplink-modules` gap goes from every layout.
