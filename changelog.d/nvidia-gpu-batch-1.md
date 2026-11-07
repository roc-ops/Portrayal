### Added
- Five NVIDIA data-center GPU cards, the first batch after the A100 80GB pilot
  (#877). Each carries the pilot's frame: a bracket face, a 3D body at the
  dimensions of NVIDIA's product brief and a NetBox and Nautobot module type;
  the four larger cards also have an east-end face (the L4 has none). None is seated yet: no bay lists them in its
  `accepts`, so each says `unplaced`, and the one line a riser needs is named in it.
  - `nvidia/a100-pcie-40gb@1`, two slots wide (`slot-width: 2`), with its top
    edge face `nvidia/a100-pcie-40gb-top@1` (three NVLink connectors) and the
    80GB card's east end `nvidia/a100-pcie-80gb-tail@1`.
  - `nvidia/h100-pcie@1`, two slots wide, with `nvidia/h100-pcie-tail@1` (a
    12VHPWR header, `aux-power`) and `nvidia/h100-pcie-top@1`.
  - `nvidia/h100-nvl@1`, two slots wide, with `nvidia/h100-nvl-tail@1` (a
    12V-2x6 header) and `nvidia/h100-nvl-top@1`, whose cap places are measured
    on NVIDIA's top-edge drawing.
  - `nvidia/l40s@1`, two slots wide, with four DisplayPort receptacles painted
    on its bracket and `nvidia/l40s-tail@1` (a 12VHPWR header). It has no
    NVLink.
  - `nvidia/l4@1`, one slot, on its full-height bracket, with no power
    connector.
- The H100 PCIe and the H100 NVL compose `nvidia/nvlink-a100-connector@1` for
  their three NVLink connectors, because NVIDIA's briefs say their bridge is the
  A100's, 900-53651-0000-000.
- The four cards with a 16-pin or 8-pin power input export a power port,
  `aux-power`, type `other`, labelled with the connector.
