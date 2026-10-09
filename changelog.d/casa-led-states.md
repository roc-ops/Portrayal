### Fixed
- Every Casa lamp now declares the states it can show and is drawn off (#940).
  The STATUS, ACTIVE and ALARM lamps on the line cards (BDM, BDM2, BDM2m,
  DS 8x8/8x96/8x192, US 16x4/16x8, CSC 8x10G) and the SMMs (2x10G, 8x10G,
  300G, 300GM) take `ok`, `active` and `alarm`, from the front-installed module
  LED tables of the C100G and C40G installation guides; STATUS and ACTIVE are
  no longer painted permanently green. The port lamps on the CSC 8x10G and
  SMM300G/GM take `link` and `activity` (blinking), and the SMMs' management
  jacks colour their lamps green. The C100G fan and PEM lamps take `ok`,
  `alarm` and a blue `high-speed` (fan) or `on` (PEM, which the guide marks
  "Not used"). The C40G AC PSU's status lamp is now a declared element,
  `casa/c40g-psu-ac@1` `status`, with `ok` and `alarm`; it was art painted
  green that no state reached. No element id changed. Each of the sixteen
  components takes a minor, and the C100G and C40G a patch.
