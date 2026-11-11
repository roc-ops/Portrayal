### Added
- Two more Panduit G5 intelligent rack PDUs, monitored and switched per outlet: the P36G18M (single phase, NEMA L6-30P cord, 30 IEC C13 and
  6 IEC C19 in six blocks of six, two double-pole breakers and a controller between the halves) and the P42G20M (three-phase delta, IEC 60309
  3P+E 9h cord, 21 C13/C15 and 21 C13/C15/C19 combination sockets in six blocks, six double-pole breakers across L1-L2, L2-L3 and L3-L1,
  and a controller). Every face the maker's drawings show is drawn: the outlet face, the rear with its two mounting buttons 1555 mm
  apart, the two long sides and the far end, whose marks are read from the sheets as unnamed estimated decor; the cord end is the cord
  gland alone, since no sheet shows it end on. No photograph of either unit is held, so no colour is checked against one. New parts:
  `panduit/g5-cord-l6-30p`, `panduit/g5-outlet-c13-c15` and `panduit/g5-outlet-c13-c15-c19`.
  The cord exports as an `other` power port labelled with the plug. The 16 A C13/C15/C19 socket presents the new `panduit-combo` connector
  key, which a C14 or a C20 plug mates, and exports as an `other` power outlet labelled with its name; `generic/c14-plug` and
  `generic/c20-plug` each gain that key in their mates, one minor version each. The 10 A C13/C15 socket is a C13 with the C15 extension,
  presents `iec-c13`, takes a C14 plug and exports as an IEC C13 outlet. The outlet numerals are not drawn: the P36G18M's sheet is a scan
  and the P42G20M's text layer holds none. The controller states no power draw, which lint reports.
