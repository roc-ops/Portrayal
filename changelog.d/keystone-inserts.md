### Added
- **Keystone inserts that seat one opening at a time in the FS FHD-FAPM6:
  `common/keystone-blank@2` and `fs/keystone-rj45-cat6@1`.** Both mate the new
  `keystone` connector interface. The blank is FS's blanking insert, the part
  `common/keystone-blank@1` already drew, now stated as an insert that fills an
  opening; it offers no port. The Cat6 RJ45 jack (FS #72818) offers one port,
  `rj45`, which a `generic/rj45-plug@1` cable end lands on like any
  patch-panel port; its punch-down rear is not modelled yet. Each of the
  panel's six openings takes either, chosen per opening, and ships empty as FS
  ships it. Sizes are the opening's; the jack's face and both colours are
  estimates, said so in the contracts (Refs #1069).
- **The kit reaches a port inside what a cage holds.** A cable end at
  `bay-1/module/clip1-occupant/rj45` (an enclosure bay, the panel, its clip, the
  jack seated in it, the jack's port) is now a port: `seatedPort` answers for
  it and for a blank or an empty clip, `cableEndPaths` lists it, and the agent's
  free-port answer offers it. A chained slot's own composed slots resolve in
  `kit/swap.js`.

### Changed
- **`common/keystone-clip@3`** presents the `keystone` interface at the same
  `mate` point and keeps `@2`'s size, window and skin, so each opening of the
  panel is a slot. **`fs/fhd-fapm6@1`** (1.1.0) composes it in its six openings
  and so publishes six slots; the seven enclosures that take the panel (FHD-1UBE,
  1UFCE, 1UFMT-N, 1UFMT-S, 1UME, 2UFCE and 4UFCE) take a minor each, with their
  locks. `common/keystone-clip@2` stays, now marked as superseded.
  `fs/fhd-fapm6-rj45@1` and `fs/fhd-fapm6-blank@1` stay as the panels that
  come loaded; the blank panel keeps `common/keystone-blank@1`.
