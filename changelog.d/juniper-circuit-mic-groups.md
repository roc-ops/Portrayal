### Changed
- The ports on the Juniper MICs whose ports are circuits (the channelized OC3/STM1 and OC12/STM4
  MICs with SFP, the 4-port OC3/STM1 circuit emulation MIC, the OC3/OC12/OC48 MICs, the ATM MIC, the
  DS3/E3 MIC and the E1/T1 circuit emulation MIC) now join a port group, so a port on a MIC seated in
  a carrier or a chassis says what it is for: `traffic`, numbered from 0 as the Interface Module
  Reference's figures print it. The SFP groups state the SFP media from each MIC's title, the DS3/E3
  group states coax from the connector row, and the E1/T1 group states none (the guide prints RJ-48).
  No group states a speed: the guide makes each cage or jack rate-selectable (OC3 or OC12, DS3 or E3,
  E1 or T1) and the speed vocabulary has no word for those rates. Part ids, positions and drawn
  geometry are unchanged; each MIC takes a patch, and so do the eight chassis that seat them
  (MX80, MX104, MX240, MX480, MX960, MX2008, MX2010 and MX2020).
