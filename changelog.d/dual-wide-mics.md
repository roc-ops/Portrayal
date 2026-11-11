### Added
- **The two dual-wide Juniper MICs seat.** `juniper/mic-3d-40ge-tx@2` 2.1.0
  and `juniper/mic3-100g-dwdm@2` 2.1.0 state `slot-width: 2`, and the first MIC
  window of a carrier states `span: [mic1]`, the window beside it
  (`docs/pcie-two-slot-bays-design.md`). The MPC1E (`juniper/mpc1e-3d@3` 3.1.0)
  and the MPC2E (`juniper/mpc2e-3d@3` 3.2.0) list the 40-port RJ45 MIC in
  `mic0`, as the module reference's MIC/MPC compatibility tables for those
  cards do, and the MPC3E (`juniper/mpc3e-3d@3` 3.1.0) lists the DWDM MIC
  there, which it lost when that MIC was redrawn dual-wide. The MIC is drawn
  as one plate across both windows, with no seam, and the second window stays
  empty. No card lists a MIC the table does not: the 40-port RJ45 MIC has a dash
  under the MPC3E, and the DWDM MIC has no row for the MPC1E or the MPC2E.
- **The MX2010's `photographed` configuration seats the 40-port RJ45 MIC in
  LC1**, the card the vendor's front photograph shows carrying one plate of
  jacks across both windows: 20 rows of two are counted on it. The MX2008,
  MX2010, MX2020, MX240, MX480 and MX960 take a patch for the changed carriers.

### Changed
- **Lint L185 follows a span along the face as well as down it.** A bay whose
  neighbour sits beside it, as a line card's two MIC windows do, may span it:
  to the right at `rotate: 0` and to the left at 180, with the same limit on a
  gap and no step sideways. A span down the pitch is judged as before. The
  design note and the schema's description of `span` say so; no key is added and
  `format` stays 1.
- **BREAKING for DCIM data already imported:** in Nautobot the interfaces of
  the two dual-wide MICs are named `{module.parent}/{module}/port-0-0` and so
  on, the name every MIC seated in a carrier takes, where they were
  `{module}/port-0-0` while no carrier took the MIC. A module type already
  imported keeps the old names until it is imported again. NetBox's names do
  not change. The two MICs' module types, and the module types of the three
  carriers (a bay that spans says so in its description), gain a `Contract
  version` line, and `slot-width: 2` is listed among the MICs' facts. This
  closes no conformance row.
