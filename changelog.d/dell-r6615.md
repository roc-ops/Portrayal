### Added
- Dell PowerEdge R6615 (`dell/r6615`), the 1U one-socket AMD EPYC 9004 server, as
  a draft. Five fronts, each its own view: 4 x 3.5 inch, 8 x 2.5 inch NVMe with
  its vent plate, 10 x 2.5 inch, 14 x E3.S and 16 x E3.S. The rear for each of
  the ISM's riser configurations 0 to 8, named as the R660's are
  (`sff10-rc1-2a3a`, `lff4-rc3-1q4p`), with the rear 2 x 2.5 inch module on
  configuration 5 and the rear 2 x E3.S module on configuration 7; 43 builds and
  four examples (populated, no LOM, the management interface card, Direct Liquid
  Cooling). The top view has the system board, the heatsink, twelve DDR5 slots
  named A1 to A12, the fans and the covers. The R660's 16th-generation 1U parts
  are reused where the R6615's manual shows the same part.
- The components the R6615 adds, each model-prefixed: `dell/r6615-system-board`,
  `dell/r6615-heatsink`, the risers `dell/r6615-riser-1q`, `-2a`, `-2t`, `-2u`,
  `-3a`, `-3p`, `-3s` and `-4p` (this server's slots sit on its one processor,
  where the R660's are wired to two) and `dell/r6615-riser-2-blank`.
- The DCIM device types and module types for them in the NetBox and Nautobot
  exports.
