### Changed
- MX2000 upper cages on the guides' 1.7 in slot (#902). `juniper/mx2010` 3.0.0
  and `juniper/mx2020` 2.0.0 place CB-RE 0, SFB 0-7 and CB-RE 1 as ten 43.18 x
  412.1 mm slots (1.7 x 16.225 in, the guides' physical tables) over the
  line-card slots, as the front photographs show; they were 55- and 40-wide
  estimates, 405 high. `juniper/mx2008` 2.0.0 does the same at the photograph's
  182 mm height, y 109-291 (it was 170 high at y 143); its guide's SFB2 row reads
  16.23 in, the MX2010's figure, and is recorded as a disagreement.
- New majors at the new size:
  `juniper/mx2000-cb-re-v@2`, `mx2000-cb-re-128g-v@2`, `mx2000-cb-re-1800-v@2`,
  `mx2000-sfb-v@2`, `mx2008-sfb-v@2` and `mx2008-rcb-v@2`. Their faces are
  re-centred, not re-read; port ids are unchanged.

### Removed
- The six upper-cage majors the new sizes replace (#902), per #448:
  `juniper/mx2000-cb-re-v@1` (now `@2`), `juniper/mx2000-cb-re-128g-v@1` (now
  `@2`), `juniper/mx2000-cb-re-1800-v@1` (now `@2`), `juniper/mx2000-sfb-v@1`
  (now `@2`), `juniper/mx2008-sfb-v@1` (now `@2`) and `juniper/mx2008-rcb-v@1`
  (now `@2`). Nothing in the library seats them any more.
