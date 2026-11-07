### Added
- Five NVIDIA GeForce Founders Edition cards, the first batch of the GeForce
  line (#877). Each is a module with a bracket face, a 3D body and a NetBox and
  Nautobot module type. None is seated yet: no bay lists them in its `accepts`
  and no bay states `interface: pcie-fh`, so each says `unplaced` and why. None
  states `mates: pcie-fh` yet: the library has not begun that migration.
  - `nvidia/rtx-3080-fe@1` and `nvidia/rtx-3080-ti-fe@1`, two-slot cards
    (`slot-width: 2`), drawn from NVIDIA's straight-on side elevation of the
    RTX 3080. Their rear face is `nvidia/rtx-3080-fe-tail@1`. The 12-pin power
    connector is a plain 3D box: the registry has no 12-pin interface, so these
    cards export no power port.
  - `nvidia/rtx-4070-super-fe@1` and `nvidia/rtx-4070-fe@1`, two-slot cards
    drawn from NVIDIA's straight-on elevation of the RTX 4070 SUPER. They share
    `nvidia/rtx-4070-fe-tail@1` and `nvidia/rtx-4070-fe-top@1`, whose
    `std/12vhpwr-header@1` is the `aux-power` port on the top edge.
  - `nvidia/rtx-4090-fe@1`, three slots (`slot-width: 3`, 61 mm), with
    `nvidia/rtx-4090-fe-tail@1` and `nvidia/rtx-4090-fe-top@1`. It has no
    straight-on picture: its shroud is the 4070 SUPER's, scaled to NVIDIA's
    stated 304 x 137 mm, and every figure of it that is not stated is estimated.
- The bracket of every card is drawn from NVIDIA's guide drawings and the PCIe
  standard, as no straight-on view of a GeForce bracket exists. The DisplayPort
  and HDMI receptacles are painted, not seated parts: the registry has none.
