### Added
- `wetatronics/conx-sfp@1`, the Wetatronics ConX-SFP console server, a module of class `transceiver`
  that wraps `generic/sfp-rj45@1`, so it seats in any SFP cage the copper SFP seats in. It states its
  RJ45 jack as a serial console (`role: console`, `media: rj45-serial`), which the kit reads as a
  console end and the drawing writes as `data-role`. Its sizes are the generic's, declared borrowed,
  because no Wetatronics document gives a dimension; no draw is written, because the maker states
  only "under 1 W typical". The latch, the LEDs and the cable's look are recorded as not stated.
  `wetatronics` is registered as a maker, and the module type `Wetatronics/ConX-SFP` is exported
  for NetBox and Nautobot with no port rows: a part seated in a cage is not a module, and the
  console jack is not a row of the type. It closes no records rows and changes no device.
