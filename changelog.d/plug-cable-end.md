### Changed
- **A plug that carries several wires ends one cable** (#805). The 21 plug
  contracts that name `wire-1` to `wire-N` now also name a `cable` point at their
  `mate` point, the end of the one cable that carries the wires, and say so in
  place of "not one cable": `amphenol-ns/p40-plug`, `generic/pla03-plug`,
  `generic/screw-terminal-2-plug`, the three `generic/terminal-508-*-plug`
  parts and the fifteen maker DC plugs. Each is a new minor of its part (a
  connection point is added) and no drawing changes. No device, rack or lab
  places one, so no device lock, export or drawing moves. A new test holds
  every contract that names wires to the same rule: numbered from 1 without
  a gap, each wire at a place of its own, one `cable` point where `mate` is.
  The wires are not routed yet, and the colour of each wire is not decided
  by this. Closes no row of the records.
