### Added
- The Eaton EVMA8365X, a Rack PDU G4 managed (0U, 41U, 1829 x 52 x 65 mm): a
  CS8365C cord on a 208 V delta input (40 A, 50 A plug, 14.4 kW), 42 outlets (24
  C13, 18 C39) in six sections A to F, a 20 A two-pole breaker per section with its
  `lines` from the drawing's one-line diagram (A and D on L1-L2, B and E on L2-L3,
  C and F on L3-L1), the eNMC network module, and two mounting buttons 124.0 from
  the cord end at the 1555.8 pitch. Its capability is `metering-scope: outlet` and
  `outlet-switching: true`, so its class is `managed` and every outlet declares the
  `[on, off]` states (#934, docs/pdu-model-design.md section 9.1).
- `eaton/g4-outlet-led@1`, the G4 outlet status lamp, placed beside each outlet
  with `for:`; the device states its `on` green and `off` red. A lamp with no state
  set draws unlit.
- `eaton/g4-cord-cs8365c@1`, the G4 fixed input cord with a CS8365C plug, exported
  as a `cs8365c` power port.

### Changed
- A DCIM outlet description names the fixed breaker it runs `through` as the unit
  prints it, `Through breaker A, lines L1-L2`, not by its placement id: the breaker
  placement's `attrs.label`, else its `attrs.section` (the G4 tile letter), else
  the id (decided 2026-10-09). The EVMI2130X re-exports with its outlet
  descriptions changed and takes a patch, 0.2.1.
