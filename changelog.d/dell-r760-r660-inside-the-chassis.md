### Fixed

- The Dell PowerEdge R760 (`dell/r760`, now 2.0.2) and R660 (`dell/r660`, now 5.2.1), and the R6615 and R6625 that
  share their riser cages (both now 0.1.1), no longer show parts outside their chassis in 3D. The riser cages' plates
  were built 20.0 mm past the rear wall, where the ISM's chassis table (R760 table 10, R660 table 12) puts nothing but
  the supplies' handles; they are 1.0 mm. The system cover's latch was built 2.0 mm above the top, 1.0 above the lid;
  it is 0.8 mm, under the lid as Dell's model has it. The R760's front bezel was built 19.7 mm out of the front where
  the ISM's table 10 gives 13.84 (35.84 with it, 22.0 without); it is 13.84, as the R660's already was. The supplies'
  handles stand 35.6 mm (R760) and 35.7 mm (R660) past the rear wall because the tables say so (Zc less Zb) and are
  not changed. A test reads every R760, R660, R6615 and R6625 drawing and fails on a part that stands out of its face further than
  that. Two parts are named in it that no Dell document gives a depth for: the return flange of a seated card's
  bracket (9.4 mm), and the metal of each riser cage that covers it, which stand past the rear wall as the hardware
  does while the rest of the cage stays inside. The cover is each cage's `flange-cover` node, drawn the way the R740xd
  draws its riser shroud: a column the flange ends sit behind, standing off the wall by a figure from Dell's service
  model where the model is held (the R660's riser 2A and 3A, 19.3 and 19.2 mm) and carried from it, as an estimate,
  to the cages of the other risers and of the R760; a filler's bracket gets it as a card's does. See the devices' gaps.
