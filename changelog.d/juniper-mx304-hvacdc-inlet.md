### Changed
- `juniper/mx304-psu-hvacdc@1` (1.0.0 to 1.1.0), the high-voltage AC/DC supply of the Juniper MX304, composes the library's Anderson
  Saf-D-Grid inlet as the part `inlet` in place of the schematic cutout its skin drew. The MX304 hardware guide calls the connector
  "an AC anderson inlet" and its cord "Anderson APP-400", and the guide's cord-connection figure prints "Saf-D-Grid 2007G" on the
  housing, the receptacle type the MX960 guide gives for its own high-voltage supply. The supply now offers a place a cord lands, and
  the exported module type gains one power port, `{module}/inlet`, of type `saf-d-grid`. No exported port is renamed or removed.
  The guide prints no dimension for the inlet, so its place on the face (upright, right of the fan) is scaled from the guide's flat
  front figure and is an estimate, and the contract says so; the quarter turn is read from that figure. The skin keeps a bezel round
  the aperture; the drawn cutout is gone.
- The MX304, which places the supply in its HVAC/DC configuration, takes a patch, with its lock and the drawing version line of its
  exported device types. One row of the records file is gone.
