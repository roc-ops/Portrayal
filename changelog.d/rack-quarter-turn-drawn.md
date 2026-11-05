### Added
- **A device rolled a quarter turn is drawn turned in the rack elevation** (#550, part 1).
  `roll: 90` turns the face clockwise as the face it is on shows it, `roll: 270` the
  other way, about the middle of the box the kit already fits it by: a 446.5 mm wide shelf
  stands 11 units tall and 355 mm across. It was an outline. Its 3D solid and its cables
  are still an outline, and the frame notice says so. The rack file is unchanged.
- **The brackets that hold a shelf stood on its side are drawn with it.** A new optional
  key, `chassis.ears.rolled`, lists the brackets a device is held by when rolled a quarter
  turn: a bar across the rack against each edge and an ear bolted to each post. The 7360 ISAM
  FX-8 shelf (`nokia/nfxs-e-bb`, now 1.0.3) states two, the shelf horizontal mount bracket
  under it and the top cross bracket over it, at the sizes the kit's unit data sheet prints;
  they are drawn alike at 90 and 270. The shelf's drawing is unchanged, and so is any device
  that states none. This key is one-way: configs.json publishes it and only the rack elevation
  reads it.
- **`nokia/fx8-vertical-air-intake-tray` and `nokia/fx8-vertical-top-baffle`**: the two
  parts of the 7360 ISAM FX-8 vertical shelf mount kit that take rack units, each placed
  as a device of two units under and over a shelf rolled 90. Sizes are from the kit's unit
  data sheet; the units are read from the installation manual's Figure 84.
  No record of the conformance list is closed.
