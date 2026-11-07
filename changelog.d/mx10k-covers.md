### Added
- **Two MX10000 slot covers** (Refs #60). `juniper/jnp10k-pwr-blnk` is the
  power supply cover, JNP10K-PWR-BLNK, and `juniper/jnp10k-re-blnk` is the
  routing and control board cover, JNP10K-RE-BLNK. The MX10004, MX10008 and
  MX10016 accept both. Their faces are estimated; the sizes come from the
  apertures they fill.
- **`MX10016-PREMIUM` on the MX10016**, the redundant AC configuration with
  JNP10K-PWR-AC2 supplies: both boards, all ten supplies, both JNP10016-FAN2
  fan trays and a cover in each line-card slot.

### Changed
- **The MX10004, MX10008 and MX10016 base configurations ship the vendor's
  covers.** MX10004-BASE seats one board with JNP10K-RE-BLNK beside it, two
  supplies with JNP10K-PWR-BLNK in the third slot. MX10008-BASE seats one board
  with its cover, three supplies and three JNP10K-PWR-BLNK. MX10016-BASE seats
  one board with its cover, five supplies and five JNP10K-PWR-BLNK. Each keeps a
  JNP10K-LC-BLNK in every line-card slot, and each `source:` now says what it
  draws. The three devices go to 2.1.0. The switch fabric boards and their
  covers are inside the chassis and are not drawn; each device lists that as a
  gap.
