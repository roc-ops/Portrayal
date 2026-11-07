### Added
- Four more NVIDIA data-center GPU cards, the third batch after the A100 80GB
  pilot (#877): the older Tesla PCIe cards. Each is a module with a bracket
  face, a 3D body at the dimensions of NVIDIA's product brief and a NetBox and
  Nautobot module type. None is seated yet: no bay lists them in its `accepts`,
  so each says `unplaced` and why. NVIDIA published no photograph of any of
  them, so every bracket face is drawn from a line drawing and says `estimated`.
  - `nvidia/v100-pcie@1` and `nvidia/p100-pcie@1`, two slots wide
    (`slot-width: 2`), on one shared rear face `nvidia/v100-pcie-tail@1` (a CPU
    8-pin header, `aux-power`). Each is one component for both of its memory
    sizes (16 GB and 32 GB, 16 GB and 12 GB): a module has no `configurations`.
  - `nvidia/p40@1`, two slots wide, on the same rear face.
  - `nvidia/p4@1`, one slot, half height, on the standard low profile bracket
    `std/pcie-bracket-lp@1`, with no power connector.
- The A40 is not modelled: no held picture shows its bracket's three
  DisplayPorts.
- The three cards with a CPU 8-pin input export a power port, `aux-power`, type
  `other`, labelled with the connector.
