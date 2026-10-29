### Added
- Juniper MX fabric boards: `juniper/scbe3-mx` (SCBE3-MX, up to 1 Tbps per slot, 1.5 Tbps with six planes; 425 W
  at most across the guides' per-slot tables) and `juniper/scbe2-mx` (SCBE2-MX, up to 480 Gbps per slot; 185 W).
  Each carries the OK/FAIL, FABRIC ACTIVE and FABRIC ONLY lamps, two SFP+ XGE cages with LINK lamps and the RJ-45
  EXT CLK jack, at the SCB bays' envelope; their faces are read off the guide's line drawings and every position
  is estimated. The SCBE3-MX's Routing Engine slot holds nothing (RE-S-1800 and RE-S-X6 are not modelled); the
  SCBE2-MX's bay takes `juniper/re-s-1300@2` and `juniper/re-s-2000@2`. Two DCIM module types are exported:
  `SCBE3-MX` and `SCBE2-MX`. The SCBE-MX follows.
- MX2000 and ASR 9000 fabric boards: `juniper/mx2000-sfb3-v` (MX2000-SFB3, up to 4 Tbps per slot; 540 W at most,
  385 W in the MX2010), `juniper/mx2000-sfb2-v` (MX2000-SFB2-S, up to 2 Tbps per slot; 295 W at most) and
  `cisco/a99-sfc2` (A99-SFC2, 230 Gbps per card; 165 W at most, 105 W in the ASR 9912). The SFB3 face is read off
  the guide's straight elevation, the SFB2-S face off a perspective drawing and the A99-SFC2 face off the data
  sheet's photograph, and every position is estimated; the SFB2-S draws no lamp. Three DCIM module types are
  exported: `MX2000-SFB3`, `MX2000-SFB2-S` and `A99-SFC2`.

### Changed
- Every SCB bay of `juniper/mx240` (6.1.0), `juniper/mx480` (7.1.0) and `juniper/mx960` (5.1.0) that took the
  SCB-MX accepts the SCBE2-MX and SCBE3-MX as well. Every bay, default and configuration is unchanged. That the
  board generations cannot be mixed and which Routing Engines each takes are recorded as gaps and not enforced.
  The DCIM device types of the three chassis differ only in the `Accepts:` text of their SCB module bays.
- The eight `sfb` bays of `juniper/mx2010` (3.1.0) and `juniper/mx2020` (2.1.0) accept the MX2000-SFB3 and the
  MX2000-SFB2-S beside the SFB, and the seven `fc` bays of `cisco/asr-9912` (2.3.0) and `cisco/asr-9922` (2.3.0)
  accept the A99-SFC2 beside the A99-SFC3 and the SFC110. Every bay, default and configuration is unchanged. That
  the MX2000 fabric boards cannot be mixed, and the ASR 9000 fabric generation pairing, are recorded as gaps and
  not enforced. The DCIM device types of the four chassis differ only in the `Accepts:` text of those bays.
