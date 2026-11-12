### Changed
- The MaiaEdge PBC-2000 (`maiaedge/pbc-2000`, 8.0.2 to 8.0.3) records its console rate, 115.2 kbps, in the `management` section of its
  attributes, from the data sheet's console-port row ("RJ45 115.2 kbps"). The word "serial" in the recorded value names the kind of
  port, as the device's console jack already does; no frame format is added, because the data sheet states none. Only the record and
  the drawing version line of its two exported device types move; no port, interface, id or pixel changes.
