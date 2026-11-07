### Changed
- Six Dell servers name their front I/O and lamp groups for what each holds, as the R740xd does. **A page, rack file or style
  that names an old group (`ports`, `leds`) no longer finds it; the group name is written into the published faces
  (`data-group`).** Each device takes a major version, with its record and the drawing version line of its exported device
  types. No port, interface or bay name moves, no position changes and no pixel is drawn differently. This clears the six
  remaining `ports` group warnings that belong to these servers and leaves one (`maiaedge/port-extender`).
  - `ports` becomes `local-access` (the USB-A port, the iDRAC Direct micro-AB USB port and the VGA port of the front panel), and
    `leds` becomes `port-leds` (the iDRAC Direct lamp, which belongs to that port).
  - The PowerEdge R660 (`dell/r660`, 5.2.2 to 6.0.0), R660xs (`dell/r660xs`, 1.0.1 to 2.0.0), R6615 (`dell/r6615`,
    0.1.2 to 1.0.0), R6625 (`dell/r6625`, 0.1.2 to 1.0.0), R760 (`dell/r760`, 2.0.3 to 3.0.0) and R960 (`dell/r960`,
    2.0.2 to 3.0.0).
