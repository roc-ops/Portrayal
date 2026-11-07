### Added
- Five NVIDIA workstation PCIe cards, the second batch of the workstation line
  (#877). Each is a module with a bracket face, a 3D body and a NetBox and
  Nautobot module type. None is seated yet: no bay lists them in its `accepts`,
  so each says `unplaced` and why.
  - `nvidia/rtx-a5500@1` and `nvidia/rtx-a4500@1`, the actively cooled dual-slot
    full-height cards (`slot-width: 2`), with four DisplayPort receptacles, the
    vent grid and four screws painted on the bracket and a 53-blade blower, measured
    on PNY's straight-on photographs. They reuse the rear face
    `nvidia/rtx-a5000-tail@1` (a PCIe 8-pin header, `aux-power`).
  - `nvidia/rtx-a2000@1`, the low-profile dual-slot card (`slot-width: 2`), for the
    RTX A2000 and the RTX A2000 12GB together: one board, one bracket, one shroud.
    Its plate is drawn, because `std/pcie-bracket-lp@1` is one slot across.
  - `nvidia/rtx-a1000@1` and `nvidia/rtx-a400@1`, the low-profile single-slot cards on
    `std/pcie-bracket-lp@1`, with a bare board in front of the shroud. The A400's
    figures are all estimated from the A1000's, whose pictures PNY serves under
    both names.
- None of the five takes auxiliary power except the A5500 and A4500. The NVLink,
  stereo and sync connectors and the DisplayPort receptacles are not seated
  parts: the registry has none of them.
