### Changed
- The ports on twenty versions of thirteen Juniper MIC components (the Gigabit Ethernet MIC with SFP, the MACsec
  Gigabit Ethernet MIC, the 2-port and 4-port 10-Gigabit Ethernet MICs with XFP, the 40-port Tri-Rate MIC, the
  OC192/STM64 MIC with XFP, and the multi-rate MIC and multi-rate MACsec MIC, each with its vertical author) now join
  port groups, so a port on a MIC seated in a bay says what it is for. All 249 ports are `traffic`, numbered from 0, as
  the MX Series Interface Module Reference numbers them. The SFP MICs state `sfp` at `1g` and the XFP MICs `xfp` at
  `10g`, from the book's "speeds up to 1 Gbps" and "speeds up to 10 Gbps"; the Tri-Rate MIC states `rj45` at `1g`,
  the top of its 10/100/1000 range. The MACsec Gigabit MIC puts its last two cages, which the book marks as 10-Gbps
  ports, in a group of their own at `10g` with `speeds` 1g and 10g. The multi-rate MICs state no speed, because a
  port's rate depends on its carrier, and the OC192 MIC states none, because the book prints a port name and no
  rate. Part ids, positions and drawn geometry are unchanged; each MIC takes a patch, and the eight MX routers that
  seat one (MX80, MX104, MX240, MX480, MX960, MX2008, MX2010, MX2020) take a patch. This closes no record row.
