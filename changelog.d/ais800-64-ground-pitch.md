### Changed
- **The grounding pair of the Edgecore AIS800-64D and AIS800-64O now rests on the maker's drawing of the lug the quick start
  guide names.** Both guides fix the grounding wire with two M6 screws through one Panduit LCDXN2-14AF-E lug or an equivalent.
  Panduit's part drawing of that lug prints two .27 in. holes .63 in. apart, tolerance .02 in., so the 5/8 in. (15.875 mm)
  pair the two devices already draw sits inside it, and the pitch is no longer an inference. Each device's `ground-pair`
  provenance now says so (its confidence moves from `estimated` to `datasheet`) and the `ground-pair-pitch` gap is gone. The
  drawing, the placement, the interface and the mate are unchanged. Each device takes a patch, with its lock and the
  `Drawing version` line of its exported device types. No exported port moves, and no row of the port-usable records is
  closed.
