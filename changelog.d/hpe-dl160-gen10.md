### Added
- HPE, a new vendor, with the ProLiant DL160 Gen10 (`hpe/dl160-gen10`), a 1U
  two-socket server (#759). It has two fronts as variant views, four LFF bays
  (`front`) and eight SFF bays with a media bay (`front-sff8`), over one
  rear, and a top view of the interior. Its seven configurations are `base`,
  the orderable `sff8`, and five examples. The NetBox and Nautobot device
  types are named for the two chassis option numbers, `878972-B21` and
  `878973-B21`.
- The `hpe/` component namespace, 42 parts today (#759, #761, #778, #780):
  - drive carriers and blanks for both fronts, the 500 W and 800 W Flex Slot
    supplies and their blank, the fan, heatsink, system board and access
    panel;
  - the primary and secondary risers, `hpe/riser-primary-dl160@1` and
    `hpe/riser-secondary-dl160@1`, whose PCIe slots are bays behind a
    standard bracket window, so the cards the library already has seat in
    them;
  - the FlexibleLOM riser `hpe/riser-flom-dl160@1`, a second occupant of the
    primary riser bay, whose `flom` bay accepts `hpe/flom-blank@1` and twelve
    FlexibleLOM adapters, each named for its option number
    (`hpe/flom-817749-b21@1` is the 640FLR-SFP28);
  - `hpe/riser-blank-primary-dl160@1`, the plate fitted where no primary
    riser is ordered, seated by the `lff4-no-riser` example;
  - three Media Module adapters, the serial port option and their blanks.
    The adapters were renamed to their option numbers before any release, as
    the HPE entry under Removed records (#760).
- `common/rj45-eth-pinside@1`: a lamped RJ45 whose two lamps are in the side
  walls at the pin end, away from the latch notch (#781). It is
  `common/rj45-eth@1` with the lamps at the other end. It joins the RJ45
  family in lint and exports as `1000base-t` unless the placement states a
  speed. Three HPE adapters use it, the 562FLR-T, 535FLR-T and 533FLR-T.

### Fixed
- The faces of the HPE FlexibleLOM adapters are read from their own
  photographs (#764). `hpe/flom-817721-b21@1`, the 535FLR-T, was a copy of
  the 562FLR-T face: its P2 legend is between the jacks and it has no right
  vent field. The 640FLR-SFP28 has its features 1.0 mm further right, with
  ACT lamps that show activity only and LNK lamps that show link only.
