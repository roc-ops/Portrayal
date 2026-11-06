### Changed
- `celestica/es1000` (1.0.2 to 1.0.3): each of its twelve orderable configurations states its own figures, from the hardware
  guide and the datasheet. The six non-PoE builds (`-24`, `-48`, `-48C`, each front-to-back and back-to-front) state a
  maximum power of 550 W where the device says 3200 W; the `-24P` builds state a PoE budget of 1550 W where the device says
  2910 W; each build states its own CPU, memory and storage (the `-48C` and `-48CP` list the 16 GB and 64 GB options) and
  an export description that names its own model, port count, PoE, supplies and airflow. The device's own `attrs` are
  unchanged, so no drawing, `devices.json` entry or comparable fact moves. The non-PoE builds still export the device's PoE
  budget, because a configuration cannot remove a device key; the `config-scoped-device-attrs` gap row stays on the device,
  narrowed to that.
- `celestica/ds4000` (0.2.2 to 0.2.3): each of its six orderable configurations states its own CPU, memory and storage as
  the installation guide's chassis table gives them (Xeon D-1627 four-core or D-1649N eight-core; 16 or 32 GB DDR4; 64, 128
  or 256 GB SSD) where the device said "per SKU". The two illustration fronts name no SKU and state nothing.
- The NetBox and Nautobot device types of both devices (12 and 6 types, 36 files) change in their `comments` text, and the
  ES1000's in their `description` too: no model, part number, slug, port or bay name moves. A DCIM that already imported these types keeps
  the old text until it imports them again. This order closes no gap row.
