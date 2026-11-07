### Added
- APC Performance vertical cable managers for 2 and 4 post open frame racks (#1097, part of #1091), the
  first slice of APC's cable managers, modelled from APC's own data sheets and instruction sheet
  990-4576A-001: the single-sided `apc/ar8615` (6 in), `ar8635` (10 in) and `ar8665` (12 in) and the
  double-sided `ar8625`, `ar8645` and `ar8675`. Each stands beside a rack (`chassis.mount: rack-side`,
  `ru: 44`, so one part places beside both the 45U AR201 and the 44U AR203A) with a `duct` guide running
  down the height on each working face, 44 fingers a side at one rack unit's pitch, and a full-length
  door a face that ships fitted and comes off in a `doors-off` configuration. APC states no cable
  capacity for them, so none is recorded. The Valueline line, the in-cabinet NetShelter managers
  (AR7721, AR7722 and the AR7580A family) and AR7710 are not in this slice.
