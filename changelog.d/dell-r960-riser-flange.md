### Fixed

- The Dell PowerEdge R960 (`dell/r960`): the metal of riser 2 that covers a seated low-profile card's bracket flange
  stands past the rear wall with the flange, as the hardware does, while the rest of the riser stays inside. A seated
  card's flange (9.4 mm) stands past the wall, and the riser's `flange-cover` node over it is 10.26 mm, the flange's
  depth and one sheet: an estimate, as the ISM gives no depth for either. The chassis test names that node and the
  flange and nothing else of a riser.
