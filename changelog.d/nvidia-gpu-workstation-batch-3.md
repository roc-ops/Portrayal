### Added
- Five NVIDIA Ada Generation workstation PCIe cards, the third batch of the
  workstation line (#877). Each is a module with a bracket face, a 3D body and a
  NetBox and Nautobot module type. None is seated yet: no bay lists them in its
  `accepts`, so each says `unplaced` and why.
  - `nvidia/rtx-6000-ada@1`, `nvidia/rtx-4500-ada@1` and `nvidia/rtx-5000-ada@1`,
    the actively cooled dual-slot cards (`slot-width: 2`), with four DisplayPort
    receptacles painted on the bracket, measured on PNY's straight-on photographs.
    Their rear faces are `nvidia/rtx-6000-ada-tail@1` and
    `nvidia/rtx-4500-ada-tail@1` (the 4500 and 5000 share it), each composing
    `std/12vhpwr-header@1` as `aux-power`: the cards take the 16-pin CEM5
    connector. The RTX 4500 Ada has a backplate drawn from its back photograph.
    PNY serves the RTX 4500 Ada's pictures under the RTX 5000 Ada's name, so every
    face of `nvidia/rtx-5000-ada@1` is estimated from the 4500's, and says so.
  - `nvidia/rtx-4000-ada@1`, one slot, on the standard full-height bracket, with
    `nvidia/rtx-4000-ada-tail@1` (`aux-power`, 16-pin) and a backplate with the
    blower's intake drawn from its back photograph.
  - `nvidia/rtx-2000-ada@1`, a low-profile dual-slot card with no power
    connector, drawn on its full-height support bracket (the straight-on picture
    held), with four mini DisplayPort receptacles painted on it.
- The DisplayPort and mini DisplayPort receptacles and the stereo and sync
  connectors are not seated parts: the registry has none of them. The RTX 4000
  SFF Ada and RTX 2000E Ada are not modelled (no photograph in the intake).
