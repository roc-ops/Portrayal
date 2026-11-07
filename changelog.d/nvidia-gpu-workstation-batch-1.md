### Added
- Five NVIDIA workstation PCIe cards, the first batch of the workstation line
  after the data-center cards (#877). Each is a module with a bracket face, a 3D
  body and a NetBox and Nautobot module type. None is seated yet: no bay lists
  them in its `accepts`, so each says `unplaced` and why.
  - `nvidia/quadro-rtx-8000-passive@1` and `nvidia/quadro-rtx-6000-passive@1`, the
    passive dual-slot server cards (`slot-width: 2`), drawn from NVIDIA's product
    briefs PB-09763 and PB-09762 (figure 4, the card's dimensions, and figure 7,
    the CPU 8-pin end view). Their rear face is `nvidia/quadro-rtx-passive-tail@1`
    (a CPU 8-pin header, `aux-power`). The briefs' figures are the same, so the
    two cards share the body. The NVLink cap is drawn and no connector is
    composed; the extenders are not modelled.
  - `nvidia/rtx-a6000@1` and `nvidia/rtx-a5000@1`, the actively cooled dual-slot
    cards (`slot-width: 2`), with four DisplayPort receptacles painted on the
    bracket, measured on PNY's straight-on photographs. Rear faces
    `nvidia/rtx-a6000-tail@1` (a CPU 8-pin header) and `nvidia/rtx-a5000-tail@1`
    (a PCIe 8-pin header), each exporting `aux-power`.
  - `nvidia/rtx-a4000@1`, one slot, on the standard full-height bracket, with
    `nvidia/rtx-a4000-tail@1`. Its 6-pin PCIe connector is a plain 3D box: the
    library registers no 6-pin interface, so the card exports no power port.
- The NVLink connectors, the stereo and sync connectors and the DisplayPort
  receptacles of the three active cards are not seated parts: the registry has
  none of them.
