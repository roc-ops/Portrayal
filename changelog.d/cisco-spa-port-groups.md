### Changed
- The ports on 22 Cisco ASR 9000 shared port adapters (every `spa-*` adapter that composes a port
  part: the SONET/SDH and ATM adapters with SFP or XFP cages, the T3/E3 and channelized T3 adapters
  with coax jacks, and the 8-port T1/E1 adapters with RJ45 jacks) now join a port group, so a port
  on an adapter seated in a SIP subslot says what it is for. Each adapter declares one group,
  `traffic`, numbered from 0 as the SIP and SPA Hardware Installation Guide numbers its ports. The
  SFP, XFP and RJ45 groups state their cage as `media`, and so does the 2-port channelized T3/E3
  adapter's coax group, whose guide names the DIN 1.0/2.3 connector. The other coax groups name no
  media of their own: each jack declares one, and the guide calls that connector Siemax. No group states a speed: the guide prints SONET and T-carrier rates that the closed set
  of speeds has no word for, so each rate stays in the group's description as printed, and the two
  OC-3/OC-12 adapters state none because their cage takes both. Part ids, positions and drawn
  geometry are unchanged; each adapter takes a minor, and the ASR 9010, which accepts the two SIPs
  that seat them, takes a patch. The 24-port T1/E1/J1 and 4-port serial adapters compose no port
  part and are not changed.
