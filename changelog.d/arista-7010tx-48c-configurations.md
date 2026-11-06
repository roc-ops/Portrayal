### Changed
- **The Arista 7010TX-48C builds are configurations of their own** (`arista/7010tx-48`, 0.2.0 to 0.3.0). The
  four -48C part numbers (DCS-7010TX-48C-F, -R, -DC-F and -DC-R) sat beside the 7010TX-48's in `ac-f`, `ac-r`,
  `dc-f` and `dc-r`, and a configuration exports one DCIM device type, so no -48C type existed. They move into
  `ac-c-f`, `ac-c-r`, `dc-c-f` and `dc-c-r`, which draw what their 7010TX-48 build draws and state their own
  `attrs` and `export-description`: 8 GB of memory against the device's 4 GB, and the minimum EOS release the
  data sheet prints for the build (4.31.1 for the -48C, 4.33.2 for the -48C-DC, against 4.26.0). The -48C's
  power stays the 75 W typical and 100 W maximum of the quick start guide, which the device already states; the
  data sheet's other figures stay in the `power-draw` gap. The device's own memory and release lines now name
  the 7010TX-48 alone. One gap row closes: `config-scoped-device-attrs`.
- **Merge danger for a DCIM that imported the 7010TX-48 types.** The DCIM export gains eight files, the NetBox
  and Nautobot device types DCS-7010TX-48C-F, -R, -DC-F and -DC-R, and the eight files of the four existing
  types DCS-7010TX-48-F, -R, -DC-F and -DC-R change in the text of `comments` (the configuration's description,
  the memory line, the minimum EOS line and the drawing version). No model, slug, part number, port or bay name
  changes. A DCIM that imported the 7010TX-48 types keeps the old text until it imports them again, and one
  that imports the new types keeps them after a revert.
