### Added
- **Hubbell Premise Wiring horizontal cable managers** (#1101, part of #1091, vendor
  `hubbell`): the M-Series HM14C (1 RU), HM24C (2 RU), HM34C (3 RU) and HM144C (1 RU,
  4 in front and 4 in rear extension), the S-Series HS23C (2 RU, steel fingers) and the
  SD-Series HSD13 (1 RU, plastic fingers), each from the maker's own spec sheet. An M-Series
  part is a centre plate with four windows and five wire rings (`ring` guides) on each side;
  the HS23C and HSD13 are finger ducts (`duct` guide with the finger pitch and gap). The
  plate's windows are declared pass-throughs, the cover of each part is a removable lid, and
  a `cover-off` configuration shows the rings or fingers it hides. The HSD13's fingers are
  parts of their own, so each can be taken out. No part states a cable capacity: no sheet
  does. The rear extension of the HM14C, HM24C and HM34C, which the sheets' figure marks and
  no table gives, is estimated at the 4 in the HM144C states.
- **Hubbell components under `hubbell/`**: the centre plate, wire ring and replacement cover
  of each M-Series height (`hm-plate-1u`, `hm-ring-1u`, `hm1c`, and the 2u and 3u),
  the HS23C's plate, floor, finger, tab and cover (`hs2c`), and the HSD13's base, finger,
  end block and cover.
- **Hubbell art, after the first look**: an M-Series wire ring is a closed round-wire loop
  fixed to the plate (a root wire joins its two wires at the plate) and reads in a mid steel
  tone against the black plate; the side views draw it with bent corners (a stand-in radius,
  gap `ring-bend`). The covers draw a folded edge top and foot and a blank name plate
  (HM1C, HM2C, HM3C) or a rolled top edge, two slot marks and the plate (HS2C); the fold,
  slot and radius are stand-ins (gap `cover-face`). The HS23C's fingers have a rounded tip
  and folded rim in the top view, and its fingers, tabs and flange are drawn in steel
  tones so they read on the dark plate and on a light stage. The HSD13's cover has no
  face detail in any source, so it is unchanged.
