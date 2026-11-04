### Added
- The keys `edgecore-dcs-dc-block-3`, `edgecore-amx-dc-block-3` and `edgecore-agr-dc-block-2` for the DC power connectors of the
  Edgecore AS5835 (DCS201 and DCS202), AMX3200 and AGR560 48 VDC supplies: a green pluggable terminal with three cells and a label
  strip printed with an earth symbol, "-" and "+" (Edgecore AS5835-54T Quick Start Guide, "Connect Power"); a blue three-pin
  connector (Edgecore AMX3200 Quick Start Guide); and a shrouded two-socket connector (Edgecore AGR560 Quick Start Guide). The
  guides name no part number for any of them (the AGR560 data sheet names a maker and nothing more), so each key claims no maker,
  standard or pitch. `edgecore/dcs201-dc-header@1`, `edgecore/amx-3200-dc-header@1` and `edgecore/agr560-dc-header@1` present
  them and `edgecore/dcs201-dc-plug@1`, `edgecore/amx-3200-dc-plug@1` and `edgecore/agr560-dc-plug@1`, the cable connectors, mate
  them; all six are declared stand-ins with estimated sizes.

### Changed
- The three supplies (`edgecore/dcs201-psu-dc@1`, 1.1.0 to 1.2.0; `edgecore/amx-3200-48v-psu@1` and `edgecore/agr560-psu-dc@1`,
  each 1.0.0 to 1.1.0) compose their connector as the part `dc-header`, standing in the box their skin already reserves for it, so
  each offers a place a cable lands. The roles of the contacts are recorded in each supply's provenance (the AGR560's are not
  stated by any document) and no DC port is stated, because the poles are the contacts of one pluggable connector. No skin is
  edited. The AGR560's description now says two sockets where it said two studs: the guide's figure shows a shrouded connector
  and the data sheet's ring terminals are the far ends of its cable. Each supply's exported power port is `{module}/dc-header`
  of type `other` where it was `{module}/Inlet` of type `dc-terminal`.
- The four devices that seat them (`edgecore/dcs201`, `edgecore/dcs202`, `edgecore/amx3200` and `edgecore/agr560`) take a patch,
  with their recorded contents and the drawing version line of their exported device types; the supplies' module types carry the new
  contract versions and the new port name. Three rows of the records file are gone.
