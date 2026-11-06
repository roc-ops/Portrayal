### Added
- The key `cisco-dc-block-2` for the two-socket DC power connector of the Cisco ASR 9000 fixed-port DC supplies, a shrouded body with two round
  sockets marked "+DC" above and "-DC" below (Cisco ASR 9000 Series Fixed-Port Routers Hardware Installation Guide, Figures 162 and 163).
  The guide names a maker for the cable and no series or part number for the connector, so the key claims none.
  `cisco/a9k-dc-header@1` presents it and `cisco/a9k-dc-plug@1`, the cable block of Figures 67 and 68, mates it; both are declared stand-ins
  with estimated sizes.

### Changed
- The Cisco ASR 9901 DC supply (`cisco/a9k-1600w-dc@1`, 1.0.1 to 1.1.0) and the ASR 9902 and 9903 DC supply (`cisco/pwr-1p6kw-dc@2`, 2.0.0 to
  2.1.0) compose that connector as the part `dc-header`, standing inside the connector their skins already draw, so each offers a place a cable
  lands. The two contacts and their roles (`pos` and `neg`, top to bottom, as the supply prints them) are recorded in their provenance and no DC
  port is stated. The skins are unchanged. The exported power port of each is `{module}/dc-header` of type `other` where it was `{module}/Inlet`
  of type `dc-terminal`.
- The Cisco NXA-PHV-350W HVAC/HVDC supply (`cisco/nxa-phv-350w@1`, 1.0.0 to 1.1.0) composes the library's Saf-D-Grid inlet as the part `inlet`,
  because the Cisco N9348GC-FX3 hardware installation guide names "the Anderson Power Saf-D-Grid connector" for it. Its turn and place are
  estimates, no figure showing the supply's inlet. The skin is unchanged. The exported power port is `{module}/inlet` of type `saf-d-grid`
  where it was `{module}/Inlet` of type `other`.
- The six devices that seat these supplies (`cisco/asr-9901`, `cisco/asr-9902`, `cisco/asr-9903`, `cisco/n9k-c92348gc-fx3`,
  `cisco/n9k-c9348gc-fx3` and `cisco/n9k-c9348gc-fx3ph`) take a patch, with their locks and the drawing version line of their exported device
  types; the three module types carry the new contract version and the new power port. Three rows of the records file are gone.
- The Nexus 9300 FX3PH test no longer pins its devices to the version they had.
