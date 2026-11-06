### Changed
- **Three Arista builds state their own figures in the DCIM export.** The DCS-7050DX4M-32S-F
  (`arista/7050dx4-32s`, configuration `m-f`, 1.0.0 to 1.0.1) states 423 W typical and 1208 W
  maximum power, MACsec on ports 1 to 8 and 25 to 32, the LIC-FIX-3-MACSEC licence group and a
  minimum EOS of 4.30.1, where its device type carried the DCS-7050DX4-32S's 353 W and 880 W. The
  DCS-7280CR3K-32D4A-F and -R (`arista/7280cr3-32d4`, configurations `k-a-f` and `k-a-r`, 0.1.0 to
  0.1.1) state 543 W typical and 865 W maximum, an eight-core CPU, 64 GB of memory and a minimum EOS
  of 4.27.2, where they carried 535 W and 851 W; the DCS-7280CR3K-32D4-F and -R (`k-f`, `k-r`)
  state their 64 GB of memory. Each figure is the quick start guide's or the data sheet's own, and
  the figures leave the configurations' description text. The three builds also take a description
  of their own, naming the DX4M or the 32D4A instead of the base switch. The device keeps the base
  figures, so the other types of both devices are unchanged but for the drawing version line, and
  the drawing is unchanged. The `config-scoped-device-attrs` gap closes on both devices (2 rows).
  A DCIM that already imported these types keeps the old description and figures until it
  imports them again; no model, slug, part number, port or bay name changes.
