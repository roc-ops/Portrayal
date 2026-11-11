### Changed
- The MaiaEdge Port Extender (`maiaedge/port-extender`, 3.0.2 to 4.0.0) names its port group `front-ports` instead of `ports`, as Arista,
  Juniper and Oscilloquartz devices already name the ports of a front panel. **A page, rack file or style that names the old group (`ports`) no longer finds it; the group
  name is written into the published face (`data-group`).** The device takes a major version, with its record and the drawing version line of its
  two exported device types. It stays one group: the vendor numbers the 48 SFP28 tenant ports and the 8 QSFP28 uplinks 1 to 56 in one space, and
  each port keeps its own media. No port, interface, bay or lamp id moves, no position changes and no pixel is drawn differently. This clears the
  last `ports` group warning in the library. No record row is closed by it.
