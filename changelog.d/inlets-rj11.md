### Fixed
- The IEC inlets' cavities are as deep as the cord ends that enter them.
  `std/c14-inlet@1` (1.4.0) is 17.0 deep, shroud face to cavity floor, with
  its pins rising 15.0, both dimensioned on Adam Tech drawing S00087C rev D,
  where it was 13.0 and 12.2 estimated. `std/c20-inlet@1` (1.4.0) is 19.0 deep
  with 17.0 pins, still estimated (the C19 nose less 1, as the C13/C14 pair
  stands; no held drawing sections a C20 cavity), where it was 15.0. The cord
  ends seated in them, `generic/c13-plug@1` and `generic/c19-plug@1` (1.1.0),
  stand 4.0 less proud: 47.0 and 57.0 in front of the inlet face. The 126
  devices whose supplies or chassis carry one of these inlets take a patch
  (97 C14, 30 C20, `dell/r740xd` both); their DCIM exports change in the
  drawing version line only (#793).
- `common/rj11-jack@1` (1.2.0) is drawn as the six-position jack it is: the
  opening is 9.88 wide (TE C-1775675 rev C) in three tiers (body, latch
  shoulder, latch slot) recessed into a solid housing, as `std/rj45@2` draws
  its own, where it was the 11.6 RJ45 width; two contacts are loaded (6P2C);
  and it is 20.57 deep with a built cavity, where it stated no depth. Its
  body, `tel` and `mate` points are unchanged, so `generic/rj11-plug@1`
  (1.0.1, provenance only) seats where it did and now clears the opening by
  about 0.12 a side. `halny/hlx-tgv` takes a patch (#837).
