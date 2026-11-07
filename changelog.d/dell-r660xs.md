### Added
- Dell PowerEdge R660xs (`dell/r660xs`, draft), the R660's lower-cost 1U sibling,
  from Dell's installation and service manual, technical guide and spec sheet:
  three fronts, each its own view - 10 x 2.5 inch, 8 x 2.5 inch (the vent block
  over the upper right) and 4 x 3.5 inch - with the security bezel fitted and
  hiding the drives; the rear for riser configurations 1 to 6 (R1a + R2a,
  R1a + R2e, R1a, R1a with two rear 2.5 inch drives, R1a + R2d, R1b + R2e), the two
  supplies side by side at the right; the top view with the system board, two
  heatsinks, sixteen DIMM slots, seven fans and the seated parts from above.
  Eighteen configurations, named `<front>-rc<n>-<risers>`. The no-backplane
  front and riser configuration 0 are not drawn: no Dell figure shows them.
- New components, all model-prefixed because the R660xs's parts differ from the
  R660's: `dell/r660xs-riser-1a`, `-1b`, `-2a`, `-2d` and `-2e` with their cages
  (`dell/r660xs-riser-1-cage`, `-2-cage`), plan forms (`-1-plan`, `-2-plan`) and
  the vented `dell/r660xs-riser-2-blank`; `dell/r660xs-boss-riser`;
  `dell/r660xs-lom-2x1g`; `dell/r660xs-system-board`; and `dell/r660xs-fan`.
- DCIM device types for the R660xs in the NetBox and Nautobot exports, and module
  types for its new modules.
