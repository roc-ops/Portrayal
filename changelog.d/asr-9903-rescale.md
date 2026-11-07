### Changed
- **`cisco/asr-9903` is 439.9 mm wide, and every x on its front and rear moves**
  (#374). Figure 19 of the Cisco ASR 9000 Series Fixed-Port Routers Hardware
  Installation Guide dimensions the chassis 17.32 in, 439.9 mm edge to edge; the
  guide's Table 30 and the data sheet's 443.86 mm are read as an overall width
  and are recorded in the device's provenance beside it. `chassis.width` and the
  four faces' sizes are 439.9, every front and rear x is the old one times
  0.99108, and **every export position on the 9903 changes** (its drawn faces,
  elements and cutouts; the 18 tracked DCIM files for the two chassis and five
  parts change only in their drawing and contract version text, as they carry
  no coordinates). The A99-RP-F
  slots are on a 209.55 mm pitch (they were 211.44; the ASR 9902's is 209.58),
  and the SFP+ cage pitch on the fixed board is 14.23 mm against SFF-8433's 14.25.
  Five parts measured off the same two masters were re-derived on the corrected
  scale, each as a new major beside the old one: `cisco/a9903-20hg-pec@2`,
  `cisco/a9903-8hg-pec@2`, `cisco/asr-9903-fan@2`, `cisco/pwr-1p6kw-ac@2` and
  `cisco/pwr-1p6kw-dc@2`. The `@1` majors stay, marked `superseded-by`, so a
  saved rack or contract that names them still resolves. `cisco/asr-9903` and
  `cisco/asr-9902` are 2.0.0.
- **The PWR-1.6KW supply is 74.94 mm wide on both ASR 9900 fixed chassis, an
  estimate.** The ASR 9902's own rear master reads 74.94; the ASR 9903's reads
  74.02 once rescaled, and no source found online or in the document set settles
  the width to 0.5 mm. `cisco/pwr-1p6kw-ac@2` and `cisco/pwr-1p6kw-dc@2` carry
  74.94 marked `estimated`, both chassis' bays are 74.94, and a gap on each
  chassis names the Cisco power-module table or straight-on rear photograph that
  would settle it. No kit version changes.
