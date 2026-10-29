### Added
- Cisco Catalyst 2960-S, second batch (Refs #1275): four 1RU stackable switches with a built-in AC supply and two
  SFP+ uplinks, each with a USB Type A port, USB mini-Type B and RJ-45 consoles, an Ethernet management port, a
  FlexStack module slot that seats the existing blank cover and an RPS connector. The WS-C2960S-48LPD-L
  (`cisco/ws-c2960s-48lpd`, 48 10/100/1000 PoE+ ports, 370 W), the WS-C2960S-48TD-L (`cisco/ws-c2960s-48td`, 48
  ports, no PoE), the WS-C2960S-24PD-L (`cisco/ws-c2960s-24pd`, 24 PoE+ ports, 370 W) and the WS-C2960S-24TD-L
  (`cisco/ws-c2960s-24td`, 24 ports, no PoE). No component is new: the slot's blank cover is
  `cisco/c2960s-flexstack-blank`. Each device has two configurations, the `ac` base build and one orderable named
  for its only SKU, eight in all. The DCIM exports gain one device type per tool for each of the four SKUs.
