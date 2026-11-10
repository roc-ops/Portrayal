### Added
- APC vertical cable managers for NetShelter SX cabinets (#1097, part of #1091), modelled from APC's own data sheets
  and installation sheets: `apc/ar7722`, a 23U and a 20U length for a 600 mm wide 45U cabinet (107 x 1911.35 x 45 mm,
  43 loops, one to each rack unit), and `apc/ar7580a`, two 20U lengths for a 750 mm wide 42U cabinet (97 x 1778 x 160 mm,
  40 fingers down each side of one channel). Each stands in a cabinet's zero-U space (`chassis.mount: rack-side`, a
  `duct` guide running down the height at one rack unit's pitch) and is drawn on all six sides. Four new `apc/` parts
  back them. APC states no cable capacity for either, so none is recorded. No NetShelter SX cabinet is in the library
  yet, so the cabinets that take each manager are stated by the maker's titles and not placed. AR7721, AR7502 and
  AR7710 are not in this change. It closes no row of the conformance records.
