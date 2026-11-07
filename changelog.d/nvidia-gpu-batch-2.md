### Added
- Six more NVIDIA data-center GPU cards, the second batch after the A100 80GB
  pilot (#877). Each is a module with a bracket face, a 3D body at the
  dimensions of NVIDIA's product brief and a NetBox and Nautobot module type.
  None is seated yet: no bay lists them in its `accepts`, so each says
  `unplaced` and why.
  - `nvidia/l40@1`, two slots wide (`slot-width: 2`), the L40S's sibling with four
    DisplayPort receptacles painted on its bracket. Its rear face is the L40S's
    `nvidia/l40s-tail@1` (a 12VHPWR header, `aux-power`). It has no extender: the
    brief says they are TBD.
  - `nvidia/a30@1`, two slots wide, on the A100 80GB's rear face
    `nvidia/a100-pcie-80gb-tail@1` (a CPU 8-pin header, `aux-power`), with the
    straight and long offset extenders.
  - `nvidia/a10@1`, one slot, on the standard full-height bracket, with
    `nvidia/a10-tail@1` (a PCIe 8-pin header, `aux-power`).
  - `nvidia/a2@1` and `nvidia/t4@1`, one slot, half height, on the standard low
    profile bracket `std/pcie-bracket-lp@1`, with no power connector. The T4's
    vent holes are measured on a straight-on photograph of its bracket.
  - `nvidia/h200-nvl@1`, two slots wide, on the H100 PCIe's rear face
    `nvidia/h100-pcie-tail@1` (a 12VHPWR header). Its NVLink cap is drawn, and no
    NVLink connector is composed: the registry has the A100's only.
- The A40 is not modelled: no held picture shows its bracket's three
  DisplayPorts.
- The cards with a 16-pin or 8-pin power input export a power port,
  `aux-power`, type `other`, labelled with the connector.
