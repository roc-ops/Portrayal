### Added
- Juniper MX: two DPC cards, `juniper/dpce-q-40ge-sfp@1` (DPCE-R-Q-40GE-SFP and DPCE-X-Q-40GE-SFP, 365 W,
  forty SFP) and `juniper/dpce-q-4xge-xfp@1` (DPCE-R-Q-4XGE-XFP and DPCE-X-Q-4XGE-XFP, 330 W, four XFP).
  Every slot of the MX240, MX480 and MX960 that takes the 40-port DPCE-R card takes both. The cards are
  drawn on the faces of their photographed siblings; the module reference's figure shows no scale. Refs #34.

### Changed
- Juniper MX: `juniper/dpce-r-40ge-sfp@2` (2.3.0) also stands for DPC-R-40GE-SFP and DPCE-X-40GE-SFP, and
  `juniper/dpc-r-4xge-xfp@3` (3.2.0) for DPCE-R-4XGE-XFP and DPCE-X-4XGE-XFP: each pair prints the same
  watts and the same ports in the hardware guide's power table and the module reference. The drawing is
  unchanged. The MX240, MX480 and MX960 take a minor (6.7.0, 7.6.0, 6.3.0).
