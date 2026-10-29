### Added
- Cisco Catalyst 2960-S, first batch (Refs #1275): the WS-C2960S-48FPD-L (`cisco/ws-c2960s-48fpd`), a 1RU stackable
  switch with 48 10/100/1000 PoE+ RJ-45 ports (740 W), two SFP+ slots, a USB Type A port, USB mini-Type B and RJ-45
  consoles and an Ethernet management port. Its AC supply is built in, so the rear has an inlet and no supply bay;
  it has a FlexStack module slot that seats a blank cover. One component is new: `cisco/c2960s-flexstack-blank`,
  which has no part number because none is printed. The device has two configurations: the `ac` base build and the
  orderable WS-C2960S-48FPD-L. The DCIM exports gain one device type per tool for WS-C2960S-48FPD-L and a module type
  per tool for the new component. The WS-C2960S-48LPD-L, -48TD-L, -24PD-L and -24TD-L follow in later batches.
