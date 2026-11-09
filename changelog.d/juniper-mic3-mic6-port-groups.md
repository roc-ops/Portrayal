### Changed
- The ports on fifteen versions of eleven Juniper MIC components (the 10-Gigabit Ethernet MIC with SFP+, the
  40-Gigabit Ethernet MIC with QSFP+, the 100-Gigabit Ethernet MICs with CFP and CXP, each with its vertical author, and
  the MIC6 24-port 10-Gigabit SFP+ MIC and 100-Gigabit CXP and CFP2 MICs) now join port groups, so a port on a MIC seated
  in a bay says what it is for. All 72 port parts are `traffic`, numbered from 0, as the MX Series Interface Module Reference
  numbers them. Each group states its cage as `sfp-plus`, `qsfp-plus`, `cfp`, `cfp2` or `cxp` and its speed as `10g`,
  `40g` or `100g`, from the book's "speeds up to 10 Gbps", "up to 40 Gbps" and "up to 100 Gbps" for the port; the LAN-PHY,
  WAN-PHY and OTN line rates are modes of one port and are not stated. Part ids, positions and drawn geometry are
  unchanged; each MIC takes a minor, and the six MX routers that seat one (MX240, MX480, MX960, MX2008, MX2010,
  MX2020) take a patch. The 100-Gigabit DWDM MIC is not part of this change. This closes no record row.
