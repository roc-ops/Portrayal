### Fixed

- The Dell PowerEdge R960 (`dell/r960`, now 2.0.0) no longer shows parts outside its 444.0 x 174.3 x 866.74 mm
  chassis in 3D. The two air shrouds, the support bar and the system cover were built 98.0, 80.7, 29.2 and 13.0
  mm above the lid (a black block over the middle of the chassis and a 13 mm slab for the lid); they now stand on
  the system board's floor like the heatsinks and top out where Dell's model has them, under the lid, and the lid is a
  plate 0.5 mm proud. The 86 mm supplies' handles were built 33.5 mm and their latches 14.7 mm past the rear wall
  where ISM table 7 puts the handle 2.455 mm past it; the face is recessed 30.9 mm in the machine and a bay cannot
  recess its occupant, so the handle is built 2.6 mm past the wall and the latch 1.0. The riser cages' plates were built
  20.0 mm past the rear wall by analogy with the R660 and are 1.0. A test reads every R960 drawing and fails on a part
  that stands out of its face further than the chassis allows. The 60 mm supplies seated in the supply adapter are the
  R660's part and still stand past the wall; see the device's gaps.
