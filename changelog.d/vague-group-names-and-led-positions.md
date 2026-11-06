### Changed
- Seven devices name their lamp and port groups for what each holds and give every member of a group its own position, so the
  tree's numbering is no longer ambiguous. **A page, rack file or style that names an old group (`leds`, `ports`) no longer finds
  it; the group name is written into the published faces (`data-group`).** Each device takes a major version, with its record and
  the drawing version line of its exported device types. No port, interface or bay name moves, and no pixel is drawn differently.
  - The R740xd (`dell/r740xd`, 29.0.3 to 30.0.0): `ports` becomes `local-access` (the two USB 2.0 ports, the iDRAC Direct port and
    the VGA port), and `leds` splits into `port-leds` (the iDRAC Direct lamp) and `system-leds` (the system identification lamp, now
    position 1). Seven rear furniture parts that shared a position with another part of the same configuration take their own: the bay
    screw tab (20 to 32), the right cage screw (22 to 33), the 3.5 inch drive label (19 to 21) and the four numbered drive plates
    (19 to 28, 29, 30 and 31).
  - The AS7326-56X (`edgecore/as7326-56x`, 3.0.9 to 4.0.0): `leds` becomes `system-leds`.
  - The AS7726-32X (`edgecore/as7726-32x`, 2.1.0 to 3.0.0): `leds` splits into `system-leds` and `sfp-mgmt-leds` (the lamp pair of the two
    management SFP+ ports, now position 1).
  - The COR580 (`edgecore/cor580`, 3.2.0 to 4.0.0): `leds` splits into `system-leds` and `oob-leds` (the two out-of-band SFP+ lamps,
    now positions 1 and 2).
  - The DCS510 (`edgecore/dcs510`, 2.0.10 to 3.0.0): `leds` splits into `system-leds` and `sfp-mgmt-leds` (the two management SFP+
    lamps, now positions 1 and 2).
  - The HLX-TGV (`halny/hlx-tgv`, 2.0.11 to 3.0.0): `leds` becomes `status-leds`, the name of the row the faceplate prints.
  - The S8901-54XC (`ufispace/s8901-54xc`, 4.1.0 to 5.0.0): the four lane lamps of each QSFP28 port, which shared the port's
    position, are numbered by port and then lane, 48 to 71. The 48 arrow lamps keep positions 0 to 47.
