### Added
- GPU power and NVLink connectors (docs/connectors-gpu-design.md). Five connector
  interfaces: `eps12v-8pin`, `pcie-8pin`, `pcie-12vhpwr`, `pcie-12v-2x6` and
  `nvlink-a100-pcie`. Four board headers that present the power ones
  (`std/eps12v-header@1`, `std/pcie-8pin-header@1`, `std/12vhpwr-header@1`,
  `std/12v-2x6-header@1`), three cable plugs that mate them
  (`generic/eps12v-8pin-plug@1`, `generic/pcie-8pin-plug@1`,
  `generic/pcie-16pin-plug@1`), the NVLink connector
  `nvidia/nvlink-a100-connector@1` and NVIDIA's two-slot bridge
  `nvidia/nvlink-bridge-a100-2slot@1`, which mates it at both ends. Nothing places
  them yet. Many figures are estimated and each says so.
- A card that composes a power header exports a power port: type `other`, the
  connector as its label, because NetBox and Nautobot have no type for these. No
  existing device or card changes.
