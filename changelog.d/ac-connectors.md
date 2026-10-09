### Added
- The other halves of the AC connectors, for rack PDUs (#933). Two outlet faces:
  `std/c19-outlet@1` (IEC 60320-3 sheet J, from SCHURTER 4710-5; its 3D well
  follows its R5 outline) and `std/nema-5-20r@1` (the T-slot receptacle, from
  Qualtek 739W-X2/30). Two jumper ends, drawn from the cable end like the C13 and
  C19 ones: `generic/c20-plug@1`, which mates the new `iec-c19` interface, and
  `generic/c14-plug@1`, which mates `iec-c13`, the interface `std/c13-outlet@1`
  presents. Four input plug faces: `generic/nema-l6-20p-plug@1`,
  `generic/nema-l5-20p-plug@1`, `generic/nema-5-20p-plug@1` (Leviton catalog
  drawings) and `generic/cs8365c-plug@1` (Hubbell M-6590).
- Registry entries for all eight parts, and the `iec-c19` connector interface.
- DCIM: `iec-60320-c19` and `nema-5-20r` join `OUTLET_TYPES` and `PART_OUTLET`;
  the four input plugs map in `PART_POWER` to `nema-l6-20p`, `nema-l5-20p`,
  `nema-5-20p` and `cs8365c`. Every slug is in both NetBox and Nautobot.
