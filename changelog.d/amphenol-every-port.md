### Added
- Three estimated cable-end parts for the three connector keys the 300CB08 power panels and the Open Rack v3 trays present:
  `generic/wire-wrap-3-plug@1` (the housing the 300CB08 datasheet names as a mate of its alarm header),
  `generic/screw-terminal-5-plug@1` (the removable five-way nrgNET connector) and `generic/orv3-busbar-blade@1` (the blade of the
  rack's bus bar). Each is drawn at the outline of the part it seats on, says so, and names the maker drawing it wants.
- Three parts for the connectors the Amphenol Network Solutions centre blocks draw, `amphenol-ns/alarm-header@1`,
  `amphenol-ns/nrgnet-header@1` and `amphenol-ns/nrgnet-jack@1`, each the art the block already drew, moved out of its skin
  unchanged.

### Changed
- The Amphenol Network Solutions alarm card (`amphenol-ns/alarm-card-307608@1`, 1.0.0 to 1.1.0), nrgSMART centre block
  (`amphenol-ns/nrg-rear-block@1`, 1.0.0 to 1.1.0) and nrgILS centre block (`amphenol-ns/nrg-ils-rear-block@1`, 1.0.0 to 1.1.0)
  compose their connectors as parts that present the interface each one is: two `wire-wrap-3` alarm headers on the card and on
  the nrgSMART block, two `screw-terminal-5` nrgNET connectors on the nrgSMART block, and two `rj45` nrgNET jacks on the nrgILS
  block. The nrgSMART block's two alarm headers are drawn at the card's 11.0 by 5.5, the better-sourced drawing of the same
  header, centred in the boxes they had; nothing else on any of the three faces moves. The probe jack, the three small headers
  and the two nrgTEMP jacks stay panel art, because no document held names their connectors.
- `common/orv3-busbar-connector@1` (1.0.0 to 1.1.0) presents the `orv3-busbar` interface, so the Celestica DS6001 and the Juniper
  QFX5250-64OE-L each offer a power end a feed can land on. Its seating point is the centre of the blade slot.
- The 11 Amphenol Network Solutions 300CB08-family panels, the DS6001 and the QFX5250-64OE-L each take a patch, with their locks
  and the drawing version line of their exported device types. No port, interface or id moves. Six rows of the records file are
  gone and its `cap:` is 206.
