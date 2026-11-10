### Changed
- The ports on eleven versions of ten Juniper components now join a port group, so a port on a card seated in a
  slot says what it is for and, where the Interface Module Reference prints it, the rate it runs at. They are the
  100-Gigabit DWDM OTN MIC with CFP2-ACO, the 10-Gigabit Ethernet MIC with SFP+ and MACsec, each with its vertical
  author, and six DPCs: 40 SFP, 20 SFP with queuing, four XFP, two XFP, 20 SFP with two XFP, and 40 tri-rate. All 151
  port parts are `traffic`, numbered from 0 as the book labels them. A group states its cage as `media` and the
  rate the book prints for the port as `speed`: 100 Gbps for the DWDM port, "speeds up to" 10 or 1 Gbps for the SFP+,
  XFP and SFP ports, and the top of 10, 100 or 1000 Mbps for the tri-rate card; the SFP+ and tri-rate groups also list
  the rates the book says those ports take. The OTN line rate is a mode of the DWDM port and is not stated. Part ids,
  positions and drawn geometry are unchanged; each contract takes a minor, and the six chassis that seat them (the
  MX240, MX480, MX960, MX2008, MX2010 and MX2020) take a patch. Warnings in the baseline that no longer occur are
  removed from it. No conformance row is closed or opened.
