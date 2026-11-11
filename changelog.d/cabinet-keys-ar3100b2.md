### Added
- **Cabinets in the rack product format** (#935, #936,
  `spec/schemas/rack-product.schema.json`, republished under the same `$id`).
  A rack product may now state an `enclosure` (`doors` with `face`, `leaves`,
  `kind`, `open-area`, `hinge`, `reversible`, `swing`, `clearance` and `lock`;
  `panels`; `roof`), a `base` (`casters`, `levellers`) and `channels` (`id`,
  `point`, `where`, `slots` with `interface`, `first`, `pitch` and `count`, and
  `moves`). Every key is optional and additive: a product that states none is
  valid as it was, and a key the format does not hold yet (baying, options, the
  outside attachment points, roof and floor entries, anchors) is still refused.
  L193 holds what the schema cannot: an enclosure only on a cabinet form, a door
  face and a channel id once, a channel at a point its form has, and slots that
  present a registered mount. The product lock takes a channel as one entry of
  its own (a new one is a minor, a gone or moved one a major) and the enclosure
  and base as stated figures; no lock on file changes.
- **The APC NetShelter SX AR3100B2** (`library/racks/apc/ar3100b2`), the first
  cabinet: a 42U, 600 x 1070 mm four-post cabinet with its doors, side panels,
  roof, base and two rear zero-U channels. The slot positions of its channels are
  estimated from a dimension chain and say so in `gaps`.
- **A reseller lists a rack product** (#936). L56 resolves a listing's `hardware`
  to a device or to a rack product, and a rack product's listing sits under a
  reseller and says only `model`, `aliases`, `portfolio` and `source`. The first
  is FS.com's listing of the AR3100B2 (`library/devices/fs/ar3100b2`, FS item
  number 368069 as an alias), and `dcim_export.py --racks` files the cabinet
  again under the reseller: `FS.com/AR3100B2`, beside `APC/AR3100B2`, in the
  NetBox rack types and the Nautobot rack fields. A cabinet's doors, panels,
  roof, base and channels go in the type's comments, one line each.

### Changed
- **FS.com is registered as a maker and a reseller** (`spec/schemas/vendors.yaml`):
  its `role` is `[hardware, reseller]`. **A consumer of `vendors.json` that reads
  `role` as one word meets a list for `fs`.** The listing schema and L193 text
  say a listing may point at a rack product. It closes no row of the
  conformance records and no gap row: the AR3100B2 adds four gaps of its own.
