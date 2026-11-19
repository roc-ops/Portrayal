### Added
- `lantronix/frrj451601@1` and `lantronix/frusb1601@1`, the 16-port RJ45 and the 16-port USB I/O modules of the Lantronix
  SLC 8000. No document gives a module a size: each takes the width and height of the rear bay it seats in and the depth
  of the same maker's LM83X serial module, all stated as estimates in the contracts. Port positions are read off the
  User Guide's figures. The USB ports are drawn with the white USB 2.0 tongue the guide's words call for.
- `lantronix/slc-8000` 0.4.0 seats them in four example builds that name the maker's part numbers in their
  sources: SLC80161201S, SLC80321201S, SLC80481201S and SLC81161201S. They carry no part-numbers key, so no device type
  is added or removed. The base build still leaves the bays empty. The Ethernet switch module and the 8-port
  RJ45 module are not modelled because no held document shows their faces. It closes no records row.
