### Changed
- The Juniper MX240 normal-capacity AC supply is redrawn as a new major, `juniper/mx240-psu-ac@2` (2.0.0), to the face its hardware
  guide's Figure 14 shows, and composes the C20 appliance inlet the guide names (`std/c20-inlet@1`, id `inlet`), so it offers a
  power end a cord lands on: a C19 cord end mates it. The inlet stands beside the input switch at the same height; the three
  lamps stand in a column at the right edge, labelled AC OK, DC OK and PS FAIL as the guide's LED table labels them; the vent
  slots run across the face; the pull handle lies along the foot under the inlet (the captive screws on the flange below the plate are
  outside the bay and are not drawn). Every position is read off a
  line drawing in perspective and is declared an estimate in the supply's `provenance`; the colours are the first drawing's, and no
  photograph of the AC variant is held. The first major, `@1`, is kept as it was and is `superseded-by` the new one. The module
  type gains one power port, `{module}/inlet` of type `iec-60320-c20`; no port that was exported before is renamed or removed.
  One row of the records file is gone (the C19 row of the first major, which no configuration seats any more).
- The MX240 (`juniper/mx240`, 6.4.6 to 6.5.0) seats the new major in its `ac` configuration and its four supply bays accept it
  beside the first, takes a minor with its device record and the drawing version line of its exported device types, and declares the AC
  supply's face a gap that a photograph would close. Its exports change in four files, in NetBox and Nautobot.
