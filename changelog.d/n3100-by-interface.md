### Changed
- **The first card seats by its form.** `ufispace/n3100-4c@1` 1.1.0 states
  `mates: pcie-fh`, and slot 1 of `dell/riser-1a-14g@2` 2.5.0 states
  `interface: pcie-fh` beside the list it already carries. The slot takes the
  union, so every card it seated still seats and a card that mates the key is
  taken without being named. The list the build publishes for the slot is the
  list the contract states, and `components.json` and the R740xd's
  `configs.json` now carry the slot's `interface` beside it. Slot 3 and every
  other riser keep their lists.
- **Ten devices take a patch** because the card they seat changed: the Dell
  R660, R6615, R6625, R740xd and R760, the HPE DL160 Gen10 and four Supermicro
  1U and 511E boxes. Nothing on their faces moves.
- **The NetBox and Nautobot module type of riser 1A** describes slot 1 by its
  interface. The description no longer names the first cards the slot takes.
  Bay names and positions are unchanged.
