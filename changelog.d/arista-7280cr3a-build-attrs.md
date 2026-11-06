### Changed
- **Arista 7280CR3A-24D12, -48D6 and -72: each build states its own encryption
  and says what else it is.** The M and K builds of the three switches, and the
  24D12's K secure-boot builds, now carry their own `features` in `attrs` and an
  `export-description`, in place of the device's one line that named all three
  builds. Their NetBox and Nautobot device types (14 part numbers, 28 files) say
  "all ports" for encryption (MACsec, IPsec and VXLANsec, as TunnelSec), and their
  `description` names the build's own model and says "large routes" on the K
  builds and "secure boot" on the secure-boot builds. The data sheet gives the three
  builds of a model one power draw, memory, CPU, SSD, minimum EOS and licence
  group, so none of those is restated. This closes the
  `config-scoped-device-attrs` gap row of the three devices. Visible to anyone who
  imported these types: the `description` and `comments` text of those files
  changes; no model, slug, part number, port or bay name moves.
