### Changed
- The Cisco ASR 9001-S states its own fabric bandwidth, 60 Gbps, in its configuration's `attrs` (the device keeps the ASR 9001's
  120 Gbps), and its own export description in place of the ASR 9001's first sentence, which ended "...and 120 Gbps of...". The
  configuration's text no longer says that it cannot mark SFP+ 2 and 3 as disabled or carry the 60 Gbps figure: its
  `component-attrs` and `attrs` now do. Its power stays the ASR 9001's, because the guide's power table has no -S column; the
  `config-scoped-device-attrs` gap row of the ASR 9001 is closed, and a `power-draw` row records that no held source prints a
  figure for the -S (3.0.1 to 3.0.2).
- The Arista 7280DR3AM-54 and 7280DR3AK-54 state their own export description, naming the TunnelSec build and the large-routes
  and TunnelSec build of the 7280DR3A-54 (1.1.1 to 1.1.2). The data sheet prints the same power, memory, CPU and software release
  for all three, so nothing else of the two is restated.
- The NetBox and Nautobot device types of these three builds (`ASR 9001-S Router with 2 x 10 GE`, `DCS-7280DR3AM-54-F` and
  `DCS-7280DR3AK-54-F`, six files) change in their `description` and in the `Drawing version` line of their `comments`, and the
  -S's `comments` also read 60 Gbps and no longer carry the stale sentence. The two devices' other types (`ASR 9001 Router` and
  `DCS-7280DR3A-54-F`, four files) change in the `Drawing version` line alone. No model, slug, part number, port or bay name moves;
  a DCIM that imported these types keeps the old text until it imports them again.
