### Fixed

- The Dell PowerEdge R960 (`dell/r960`): the metal of riser 2 that covers a seated low-profile card's bracket flange
  stands past the rear wall with the flange, as the hardware does, while the rest of the riser stays inside. A seated
  card's flange (9.4 mm) stands past the wall, and the riser's `flange-cover` node over it is drawn the way the R740xd
  draws its riser shroud: a column the flange end sits behind, 19.3 mm out, carried as an estimate from the R660's
  service model (its riser 2A cover pieces reach 19.3 and 19.8) because the R960's own poses the riser short of the
  wall. A filler's bracket gets the cover as a card's does. Slot 9's flange has no cover: its estimated seat is
  unresolved, and the device's `riser-2-slot-9-flange-seat-unresolved` gap says so. The chassis test names that node,
  on riser 2 only, and the flange, and nothing else of a riser.
