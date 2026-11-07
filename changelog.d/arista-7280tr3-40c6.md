### Added
- Arista, the 7280TR3-40C6 (`arista/7280tr3-40c6`, #1204, slice 1): 40 x 1/10GBASE-T RJ-45 in five blocks of four
  and 6 x 100G QSFP, the management ports stacked at the right of the front, two hot-swap supplies and two fan
  modules at the rear. The guide has no front figure for it, so the front is drawn from the data sheet's photograph and
  every front position is estimated to about 1 mm. Its orderable configurations are DCS-7280TR3-40C6-F and
  DCS-7280TR3-40C6-R (front-to-rear and rear-to-front air), with the DC build as a worked example; the PWR-511
  supplies and FAN-7011M fan modules are the ones the 7280SR3-40YC6 already seats, so no component is added.
- The 7280SR3E-40YC6-M shares the 7280SR3-40YC6's front panel, so it stays a configuration of
  `arista/7280sr3-40yc6` (DCS-7280SR3E-40YC6-M-F and -R) and is not a device of its own.
- The DCIM device types for the two TR3 configurations, in the NetBox and Nautobot exports.
