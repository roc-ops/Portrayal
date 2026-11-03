### Added
- The connector interface `positronic-pla03`, the three-position, one-row power connector of the Positronic PCS series, male on
  the panel. The Edgecore DCS204 quick start guide names the plug that takes it, PLA03F7000/AA, which the Positronic catalog's
  ordering code reads as the female cable connector.
- `common/pla03-receptacle@1` (1.0.0), that connector as the Edgecore supplies carry it, drawn to the catalog's face (28.60 by
  10.36, three pins on a 5.00 pitch). No document names its own part number, so it states none.
- `generic/pla03-plug@1` (1.0.0), the cable connector PLA03F7000/AA, which mates it, wired DC return, the -36 to -72 VDC feed and
  ground, top to bottom, as the guide wires it.
- `edgecore/psu-48v-650-f@1` and `edgecore/psu-48v-650-b@1` (1.0.0), the Edgecore PSU-48V-650-F (F0TZZ7632004A) and PSU-48V-650-B
  (F0TZZ7632003A), the 650 W -48 VDC supplies the DCS204 data sheet lists, one part each: front-to-back with a red latch and
  back-to-front with a blue one. Each composes the connector, so a cable plugs into it as a cord plugs into an AC supply's C14,
  and says why it states no DC input port yet: a port on a connector the supply composes cannot be published at the connector.
  The roles, 16 A maximum and #14 AWG from the guide are recorded in the contract for that port.
- Their module types, `Edgecore/PSU-48V-650-F` and `Edgecore/PSU-48V-650-B`, in NetBox and Nautobot, each with one power port,
  `inlet`, of type other, labelled as the Positronic connector.

### Changed
- The Edgecore DCS204 (`edgecore/as7726-32x`, 2.0.8 to 2.1.0) seats PSU-48V-650-F in its front-to-back DC build and PSU-48V-650-B
  in its back-to-front one, in place of `common/psu-dc-650@2`, and its two PSU bays accept both beside the generic supply (which they
  keep accepting: a bay that stops accepting a part is a major bump). The two DC builds no longer set attributes on the generic
  supply; the new parts carry their part numbers, colours and airflow. A minor, with its lock and the drawing version line and the
  two PSU bay descriptions of its exported device types (32 files in NetBox and Nautobot). No port, interface or id moves.
- The exporter types the new connector's power port `other` with its label, as it does the bus-bar clip.
- `common/psu-dc-650@2` is not edited: the AS5912-54X and AS7326-56X still seat it (no document held names the DCS203's DC supply),
  and its record in the conformance records stays, so `cap:` is 159.
