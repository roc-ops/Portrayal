### Changed
- The Nokia 7750 SR-1 AC (`nokia/sr-1-ac`, 0.1.4 to 0.1.5), SR-1e, SR-2e and SR-3e (`nokia/sr-1e`, `nokia/sr-2e` and
  `nokia/sr-3e`, each 0.3.0 to 0.3.1) now state what feeds each build, from the supplies it seats and the vendor's installation
  guide. The SR-1 AC takes only the SR-1 AC PSU, in both of its builds, so the chassis states `power: ac`. The SR-e chassis takes
  an AC or a -48/-60 VDC supply, so each configuration states its own: `base`, which seats the DC supplies, says `dc`, and `ac`,
  which seats the AC supplies, says `ac`. Nothing is renamed or removed and no drawing changes; each face carries the feed in
  its `data-power` attribute and each device's `configs.json` lists it per configuration. Each device takes a patch, with its lock
  and the drawing version line of its exported device types (8 files in NetBox and Nautobot). Four rows of the lint baseline go,
  the unstated-feed entries of these devices; the three ASR 9000 chassis that seat a power module no document ties to AC or to
  DC keep theirs.
