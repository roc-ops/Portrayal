### Added
- **A box that opens in two halves.** `chassis.halves` describes a node that mounts on a
  strand or a pedestal and opens like a clamshell: exactly two entries, `base` (`outer`,
  `stands`) and `lid` (`hinge`, `angle`, `stands`), with bare numbers and the source of each in
  `provenance` keyed by path (`halves.lid.angle`). A region of the open drawing names its half
  with `half`, and a bay belongs to the half of the one region whose box holds its centre. Lint
  L200 to L203 check the two entries, the hinge, the angle, the regions, the bays and the sum of
  the `stands` against the chassis. The lock reads the halves: stating them on a released device is
  a minor, changing the base's `outer`, the lid's `hinge` or the half a bay is in is a major. The
  compiled face of such a view carries `data-half` on each bay, `<device>.configs.json` carries
  `chassis.halves` and `half` on each bay, and the NetBox and Nautobot module-bay description
  begins `In the base.` or `In the lid.`. Both keys are additive: every file valid before stays
  valid, a device that states neither builds byte for byte as it did, and `contract` stays 2. A
  validator holding the earlier schema refuses a file that states either key. This closes no row.
- **The `vecima` vendor.** `spec/schemas/vendors.yaml` lists Vecima Networks as a hardware
  vendor, so a device or a part can be filed under `vecima`.
