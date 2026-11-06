### Changed
- The Smartoptics DCP-2 chassis (`smartoptics/dcp-2`, 2.1.5 to 2.1.6) and the DCP-M32-CSO-ZR open line shelf
  (`smartoptics/dcp-m32-cso-zr`, 4.0.3 to 4.0.4) now say what feeds each build. The DCP-2's `ac-f2b` build states `power: ac` and its
  `dc-f2b` build `power: dc`, from the input each supply is specified for in the user manual and the data sheet (DCP-2-PSU-AC-FB
  100-127 VAC and 200-240 VAC; DCP-2-PSU-DC-FB -40 to -72 VDC). The shelf has one build whose two bays take either supply, so it states
  `chassis.power: [ac, dc]`. A tool filtering by feed reads `configs[].power` and `options.power` instead of parsing the build's name.
  The two warnings for a device with supplies that states no feed are gone from the lint baseline. Nothing is renamed or removed, and
  no port, bay or drawing changes. The exported device types of both devices take the new drawing version. This closes no row of the
  port records.
