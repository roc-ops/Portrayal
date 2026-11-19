### Changed
- Five Edgecore devices keep each port family's lamps in a group of its own, named for the family as the library names lamp
  groups elsewhere (`qsfp28-leds`, `qsfpdd-leds`). Their lamps of several port families sat in one group, `port-leds`, each
  family counting from its own port numbers, so members of the group shared a position. **A page, rack file or style that
  addresses one of these lamps by `port-leds` no longer finds it; the group name is written into the published faces
  (`data-group`) and into the device's record.** Each device takes a major version, with its record and the drawing version
  line of its exported device types. No lamp moves, changes shape or colour, or changes its id; no port, interface or bay
  name changes. This clears the five remaining lamp-position warnings (L144); the first family of each device keeps
  `port-leds`.
  - The AGR110 (`edgecore/agr110`, 8.3.0 to 9.0.0) and AGR130 (`edgecore/agr130`, 0.2.0 to 1.0.0): the 30 lamps of the QSFP28
    uplink ports move to `qsfp28-leds`; the dot lamps of uplinks 3 and 4 take their ports' numbers 3 and 4 (they held 2 and 3,
    and the lamp of uplink 2 already held 2).
  - The AGR560 (`edgecore/agr560`, 3.0.4 to 4.0.0): the lamps of the 24 QSFP28 ports move to `qsfp28-leds` and those of the 12
    QSFP-DD ports to `qsfpdd-leds`.
  - The CSR310 (`edgecore/csr310`, 2.0.0 to 3.0.0): the lamps of the four SFP28 ports move to `sfp28-leds`.
  - The ECS4120-28Fv2-I (`edgecore/ecs4120-28fv2-i`, 2.0.5 to 3.0.0): the lamps of the four combo RJ-45 ports move to
    `rj45-combo-leds`.
