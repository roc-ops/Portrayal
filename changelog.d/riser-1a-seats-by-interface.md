### Changed
- **Dell riser 1A seats its full-height cards by form.** Its two connector slots
  (`slot-1`, `slot-3`) state `interface: pcie-fh` and no longer list the common
  full-height card or the 19 ConnectX full-height cards and the UfiSpace
  N3100-4C by name; those 21 modules state `mates: pcie-fh`, so a module that
  mates the key and fits is taken. Each slot takes the same parts as before. The
  filler, the two PCIe brackets and the three NVIDIA GPUs stay in `accepts`, and
  the middle opening, which has no connector behind it, stays a closed list.
- The DCIM bay descriptions of the riser's two connector slots now say the
  interface in words and then the parts listed by name. Ten devices that seat
  the common card or a ConnectX card (the Dell R660, R6615, R6625, R740xd and
  R760, one HPE and four Supermicro) take a patch version.
