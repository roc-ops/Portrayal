### Added
- Four NVIDIA RTX PRO Blackwell workstation PCIe cards, the fourth batch of the
  workstation line (#877). Each is a module with a bracket face, a 3D body and a
  NetBox and Nautobot module type. None is seated yet: no bay lists them in its
  `accepts`, so each says `unplaced` and why.
  - `nvidia/rtx-pro-5000-blackwell@1`, the actively cooled dual-slot full-height
    card (`slot-width: 2`), for the RTX PRO 5000 (48 GB) and the RTX PRO 5000 72GB
    together: one board, one bracket, one shroud. Four DisplayPort receptacles,
    eleven vent slots and four screws on the bracket, a 56-blade blower and a
    backplate, measured on PNY's straight-on photographs. Its rear face
    `nvidia/rtx-pro-5000-blackwell-tail@1` carries the 16-pin power header
    (`std/12vhpwr-header@1`, port `aux-power`).
  - `nvidia/rtx-pro-4000-blackwell@1`, the single-slot full-height card on
    `std/pcie-bracket-fh@2`, with 18 vent holes, 25 slits on the broad side, a
    blower and a backplate, and its own rear face
    `nvidia/rtx-pro-4000-blackwell-tail@1` (`aux-power`).
  - `nvidia/rtx-pro-4000-sff-blackwell@1` and `nvidia/rtx-pro-2000-blackwell@1`,
    the low-profile dual-slot cards (`slot-width: 2`) that take no power cable:
    four mini DisplayPort receptacles and a 4 by 12 vent grid on a plate two slots
    across, a small blower and a backplate. The RTX PRO 2000 is drawn on its
    full-height support bracket, the only one photographed.
- The DisplayPort and mini DisplayPort receptacles are not seated parts: the
  registry has none. The RTX PRO 6000 Blackwell Workstation Edition, the 6000
  Max-Q, 5500 and 4500 are left for a later batch.
