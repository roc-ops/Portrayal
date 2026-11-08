### Added
- **The two dual-wide Juniper MICs seat in the NG cards the module reference
  lists them for.** `juniper/mpc3e-3d-ng@1` 1.1.0 lists both
  `juniper/mic-3d-40ge-tx@2` and `juniper/mic3-100g-dwdm@2` in its first MIC
  window, which states `span: [mic1]`, as the MPC3E-3D-NG column of the MIC/MPC3
  compatibility table does. `juniper/mpc2e-3d-ng@1` 1.1.0 lists the 40-port RJ45
  MIC, as the MPC2E-3D-NG column of the MIC/MPC2 table does; that table has no
  row for the 100G DWDM MIC, so it is not listed. The MIC is drawn as one plate
  across both windows, with no seam, and the second window stays empty. The MX240,
  MX480, MX960, MX2008, MX2010 and MX2020 take a patch for the changed cards, and
  the module types of the two cards gain a `Contract version` line and a
  description for the bay that spans. No exported interface name changes: the
  two MICs' module types were not touched. This closes no conformance row.
