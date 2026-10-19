### Added
- **`only-in` on a bay or cage entry of `<device>.configs.json`** (#1022,
  `render.py`, `docs/format-stability.md`). A bay or placement that a device
  gives to some configurations only (`only-in: [...]` in `device.yaml`) carries
  the same list in `bays[view][]` or `cages[view][]`, exactly as the device
  states it; the key is absent where the device states none. The drawing already
  left such a bay out of any other configuration, and the index now says so.
  Additive: a reader that does not know the key ignores it, and `contract` is
  unchanged. No export changes.

### Fixed
- **A bay a configuration does not have is no bay to the rack kit, and a bay it
  has is answered for** (#1022, `kit/rack/slots.js`, `kit/rack/ports.js`).
  `slotEnv` does not list a bay or cage whose `only-in` leaves out the item's
  configuration, and `holdsAt` gives `null` for it and for anything beneath it,
  a swap naming it included. So `inspect` and `fit` no longer offer such a bay
  (`fit` says it is not a bay of the item), where they offered the
  CH3000's double-width `slot-15-16` in a configuration that draws nothing
  there. `seatedPort` answers for a bay the configuration has and does not
  list, which holds what it ships with; it used to stay silent for any bay
  nothing named, and the `seen: true` option that heard a page for such a bay
  is gone. A cable end on a port of a part in such a bay is now settled from the
  catalogue, over a page that read it differently.
