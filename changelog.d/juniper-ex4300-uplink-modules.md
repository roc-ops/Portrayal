### Added
- The five uplink modules of the Juniper EX4300 switches, one component for each maker part number: `juniper/ex-um-4x4sfp@1` (four SFP+
  ports, for the 24-port and 48-port models), `juniper/ex-um-2qsfp@1` and `juniper/ex-um-8x8sfp@1` (two QSFP+ ports and eight SFP+ ports, for the
  EX4300-32F) and `juniper/ex-um-2qsfp-mr@1` and `juniper/ex-um-4sfpp-mr@1` (two QSFP28 ports and four SFP+ ports, for the EX4300-48MP). Each draws
  its face from the hardware guide's flat figure, with its cages as the library's own SFP and QSFP ports and its lamps as the guide numbers them,
  and states the weight the guide prints. No power draw is published, so each declares the figure as not published. The EX-UM-4X4SFP's colours are
  checked against the maker's photograph of an EX4300-24T with the module fitted; the other four are estimates, as no photograph shows them.

### Changed
- The uplink bay of the six EX4300 layouts (`ex4300-24t`, `-24p`, `-48t`, `-48p`, `-32f`, `-48mp`) takes the modules its guide lists as well as its
  cover panel; the cover is still what ships. Each device takes a minor, with the module-bay text and drawing version line of its
  exported device types. The EX4300-24T, EX4300-32F and EX4300-48MP gain `example` configurations, one for each module, so that a face shows it;
  they are illustrations and add no exported device type. The `uplink-modules` gap goes from every EX4300 layout.
