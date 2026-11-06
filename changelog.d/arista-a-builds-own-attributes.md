### Changed
- **The Arista 7280CR3K-36A and 7280SR3K-48YC8A builds state their own figures.** The `k-a-f` and `k-a-r` configurations of
  `arista/7280cr3-36s` and `arista/7280sr3-48yc8` carry `attrs` and an `export-description` instead of prose: the guide's typical and
  maximum power (262 W and 437 W for the 36A, 162 W and 338 W for the 48YC8A), the data sheet's eight-core CPU, a 120 GB SSD and a
  minimum EOS of 4.27.2, and a description that names the A model. The 48YC8's six orderable builds each state their memory, 8 GB for
  the base model and 64 GB for the K and A builds. The two gap rows `config-scoped-device-attrs` close, and the two devices take a
  patch to 0.1.1. The drawing, `devices.json` and the comparable facts are unchanged: they read the device, which still carries the
  base model's figures.
- **Exported text changes for eight Arista device types** (NetBox and Nautobot, 16 files): `DCS-7280CR3K-36A-F` and `-R` and
  `DCS-7280SR3K-48YC8A-F` and `-R` take their own `description` and the power, CPU, storage and minimum EOS lines of `comments`; the
  four other 48YC8 types (`DCS-7280SR3-48YC8-F` and `-R`, `DCS-7280SR3K-48YC8-F` and `-R`) take the memory line of their own build.
  No model, slug, part number, port or bay name changes. A DCIM that already imported these types keeps the old text until it
  re-imports them.
