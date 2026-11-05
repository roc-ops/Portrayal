### Added
- `juniper/mpc2e-3d-ng@1` (MX-MPC2E-3D-NG, 474 W) and `juniper/mpc3e-3d-ng@1` (MX-MPC3E-3D-NG, 534 W): the
  MPC2E NG and MPC3E NG carriers, each with two MIC bays taking the MICs of its own column in the module
  reference's MIC/MPC compatibility tables (the MPC2E NG takes no MIC3 card; the MPC3E NG takes the four MIC3
  cards). Every slot of the MX240, MX480 and MX960 that takes the MPC2E or MPC3E now takes them too: each chassis
  takes a minor for the new cards and a patch on top for the changed MIC (now 6.4.1, 7.4.1 and 5.3.1); nothing
  placed moves. The cards are drawn from the reference's front
  views, not photographed, and the MX240, MX480 and MX960 list their faceplates as an open gap.

### Removed
- `juniper/mic-3d-10ge-sfp-e@1`, the retired major of the 10-port SFP+ MIC. Use `juniper/mic-3d-10ge-sfp-e@2`,
  which keeps the same part ids, port paths and names: a saved rack that names the `@1` is read as the `@2`,
  and `@2` now lists as seated, since the two new NG carriers take it. An outside manifest that pins the `@1`
  by ref no longer finds it.
