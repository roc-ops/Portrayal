### Changed
- The ports on four Juniper line cards and the Multi-Rate Ethernet MIC now join a port group, so a port on a card
  seated in a slot says what it is for and, where the hardware guide or the Interface Module Reference prints it, the
  rate it runs at. They are the MX10K-LC480 (48 SFP+), MX10K-LC2101 (24 QSFP28), MX10K-LC9600 (24 QSFP-DD), the
  MX10003 MPC (six fixed QSFP+ ports and its GM/PTP jack) and the JNP-MIC1 (12 QSFP28). The 114 cages are `traffic`; the
  GM/PTP jack is a `timing` group of its own with the role `management`. A group states its cage as `media` and the
  rate the page prints for that block as `speed`: up to 10 Gbps, up to 100 Gbps, up to 400 Gbps, 40 Gbps and
  100 Gbps; the groups whose pages list the rates a port takes also list them. The jack's group states neither,
  because the guide prints no rate or cage type for it. Breakout is a logical interface and is not stated. Part ids,
  positions and drawn geometry are unchanged; each contract takes a minor, and the four chassis that seat them (the
  MX10003, MX10004, MX10008 and MX10016) take a patch. No conformance row is closed or opened.
