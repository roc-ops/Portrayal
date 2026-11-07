### Added
- **A lamp can be marked as a light whose colour the user chooses.** Some switches
  light each port in a colour set per port, VLAN or speed from a controller. A
  device's lamp group or a single placement now takes `programmable: true`, with
  `programmable-note` for the maker's own name for the feature (for example
  Ubiquiti's Etherlighting), as text only; a placement's word wins over its
  group's. This is a new key in the published format, and it is one-way: once a
  release carries it, its names and meaning cannot change without a format change.
  It is optional, so `format` is still 1 and every file valid before stays valid.
  The drawing rings the port a marked lamp belongs to in a neutral grey, under the
  port, and a lamp without the mark is drawn as before. The elements file gains
  `programmable` and `programmable-note` on the marked lamp's row, `devices.json`
  gains `programmable-light` on a device any of whose lamps is marked (derived by
  the build, never written in a manifest), and the DCIM comments of such a device
  gain one sentence. No device in the library carries the mark yet, so no drawing,
  index entry or export changes.
