### Added
- The key `ufispace-dc-block-6` for the six-position DC input connector of the UfiSpace PSU-242-DEERN supply, a body with two rows of
  three cells printed "V+" over "V-" (UfiSpace S9311-64D hardware installation guide, Figure 6). The figure prints "INPUT CONNECTOR
  PN:3072980925" and no document held joins that number to a maker's part, so the key claims no maker, standard or pitch.
- `ufispace/psu-242-dc-header@1` (1.0.0), that connector as the supply carries it, drawn at the box and in the shapes its face already
  showed (22.0 by 22.6, an estimate), and `ufispace/psu-242-dc-plug@1` (1.0.0), the cable connector of the guide's Figures 24 and 25,
  which mates it. Both are declared stand-ins with estimated sizes.

### Changed
- The PSU-242-DEERN supply (`ufispace/psu-242-dc@1`, 1.1.0 to 1.2.0) composes the connector as the part `dc-header`, standing over the
  block its skin draws, so it offers a place a cable lands. The roles the figure prints on the two rows (`pos` for "V+" and "DC+(+48V)",
  `neg` for "V-" and "DC-(0)") are recorded in its provenance, and no DC port is stated, because the six poles are the contacts of one
  pluggable connector. The skin is unchanged. The supply's exported power port is `{module}/dc-header` of type `other` where it was
  `{module}/Inlet` of type dc-terminal; a DCIM that imported the earlier module type keeps the old port until it is re-imported.
- The S9311-64D (`ufispace/s9311-64d`, 4.1.4 to 4.1.5) takes a patch, with its lock and the drawing version line of its exported device
  types; the supply's module type carries the new contract version and the new port name. One row of the records file is gone.
- The exporter types the new header's power port `other` with its label, as it does the other vendor connectors.
