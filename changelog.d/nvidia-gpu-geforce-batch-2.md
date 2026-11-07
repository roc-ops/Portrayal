### Added
- Four more NVIDIA GeForce Founders Edition cards, the second batch of the GeForce
  line (#877). Each is a module with a bracket face, a 3D body and a NetBox and
  Nautobot module type. None is seated yet: no bay lists them in its `accepts`
  and no bay states `interface: pcie-fh`, so each says `unplaced` and why. None
  states `mates: pcie-fh` yet: the library has not begun that migration.
  - `nvidia/rtx-4080-super-fe@1` and `nvidia/rtx-4080-fe@1`, three-slot cards
    (`slot-width: 3`, 61 mm). The 4080's guide draws the 4080 SUPER's shell, so
    the 4080 borrows every figure of its broad side from the SUPER's and marks it
    `estimated`. They share `nvidia/rtx-4090-fe-tail@1` and
    `nvidia/rtx-4090-fe-top@1` (the 4090's, the same drawing), whose
    `std/12vhpwr-header@1` is the `aux-power` port on the top edge.
  - `nvidia/rtx-4060-ti-fe@1`, a two-slot card (`slot-width: 2`), modelled once
    (NVIDIA gives one power figure, 165 or 160 W, and no memory size for the
    Founders Edition). It shares `nvidia/rtx-4070-fe-tail@1` and
    `nvidia/rtx-4070-fe-top@1` with the 4070 pair: its guide draws the same
    shell. Its broad side was checked on a rectified 3/4 hero.
  - `nvidia/rtx-3090-fe@1`, three slots, with `nvidia/rtx-3090-fe-tail@1`
    and the library's plain plan face. Its 12-pin connector is a plain 3D box (the
    registry has no 12-pin interface) and its NVLink connector is painted; the card
    exports no power port.
- The bracket of every card is drawn from NVIDIA's guide drawings and the PCIe
  standard, as no straight-on view of a GeForce bracket exists. The DisplayPort
  and HDMI receptacles are painted, not seated parts: the registry has none.
