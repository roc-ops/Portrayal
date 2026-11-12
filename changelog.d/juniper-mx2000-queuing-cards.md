### Changed
- Juniper MX: the MX2000 line-card adapter (`juniper/mx2000-lc-adapter@1`, 1.2.0) also seats the five queuing
  and P carriers, `juniper/mpc1-3d-q@1`, `juniper/mpc2e-3d-q@1`, `juniper/mpc2e-3d-p@1`,
  `juniper/mpc2e-3d-ng-q@1` and `juniper/mpc3e-3d-ng-q@1`: nine maker numbers, each of which the Interface Module
  Reference's Table 4 prints a release for on the MX2008, the MX2010 and the MX2020. They are the MX240-form
  cards, turned 90 in the adapter's bay like the cards it already seats; no drawing changes. The MX2008, MX2010
  and MX2020 take a minor (3.1.0, 4.1.0, 3.1.0). Refs #34.
