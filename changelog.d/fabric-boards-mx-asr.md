### Added
- Juniper MX fabric boards: `juniper/scbe3-mx` (SCBE3-MX, up to 1 Tbps per slot, 1.5 Tbps with six planes; 425 W
  at most across the guides' per-slot tables) and `juniper/scbe2-mx` (SCBE2-MX, up to 480 Gbps per slot; 185 W).
  Each carries the OK/FAIL, FABRIC ACTIVE and FABRIC ONLY lamps, two SFP+ XGE cages with LINK lamps and the RJ-45
  EXT CLK jack, at the SCB bays' envelope; their faces are read off the guide's line drawings and every position
  is estimated. The SCBE3-MX's Routing Engine slot holds nothing (RE-S-1800 and RE-S-X6 are not modelled); the
  SCBE2-MX's bay takes `juniper/re-s-1300@2` and `juniper/re-s-2000@2`. Two DCIM module types are exported:
  `SCBE3-MX` and `SCBE2-MX`. The MX2000-SFB3, MX2000-SFB2-S, A99-SFC2 and SCBE-MX follow.

### Changed
- Every SCB bay of `juniper/mx240` (6.1.0), `juniper/mx480` (7.1.0) and `juniper/mx960` (5.1.0) that took the
  SCB-MX accepts the SCBE2-MX and SCBE3-MX as well. Every bay, default and configuration is unchanged. That the
  board generations cannot be mixed and which Routing Engines each takes are recorded as gaps and not enforced.
  The DCIM device types of the three chassis differ only in the `Accepts:` text of their SCB module bays.
