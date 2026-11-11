### Changed
- The MaiaEdge Port Extender (`maiaedge/port-extender`, 3.0.2 to 4.0.0) files its ports and lamps under the names of their port
  families. **A page, rack file or style that selects `data-group="ports"` or `data-group="port-leds"` for this device no longer
  matches; the group name is written into the published face (`data-group`).** The device takes a major version, with its record
  and the drawing version line of its exported device types. No port or lamp id moves and no pixel is drawn differently. This
  closes one row of the structural lint sweep: the last `ports` group name warning of the library.
  - `ports` becomes `sfp28` (`port-1` to `port-48`) and `qsfp28` (`port-49` to `port-56`), which keep the vendor's one numbering of
    1 to 56.
  - `port-leds` becomes `sfp28-leds` (`led-port-1` to `led-port-48`) and `qsfp28-leds` (`led-port-49` to `led-port-56`).
