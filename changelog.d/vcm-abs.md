### Added
- **Two more FS vertical cable managers, both `rack-side`.**
  `fs/cmv-dfd45u5w`, the FS CMV-DFD45U5W (#63030), a 45U dual-sided ABS
  finger duct with hinged PVC covers on both faces, 2108 x 138.8 x 302 (the
  drawing; the table and the dimensioned render say 310, recorded as a
  `sources-disagree` gap), built hollow as two channels back to back across a
  25.6 mm spine. Its back and cover views are the CMV-SFD45U5W rasters byte for
  byte and its side view lands on the single-sided figures within half a
  millimetre, so every part is reused on both faces:
  `fs/cmv-sfd45u5w-base@1`, `-wall@1`, `-finger@1`, `-clip@1` and `-cover@1`.
  The middle is closed by plates sunk inside the side, top and bottom faces,
  as on `fs/cmh-dfd1u`. Capacity 5490 Cat6 (datasheet); the 16.80 kg product
  page weight is stated and flagged as suspicious, 3.5 times the single-sided
  4.75 kg.
  `fs/cmv-sfd42u9w`, the FS CMV-SFD42U9W (#188944), a 42U single-sided finger
  duct, 1866.9 x 88.9 x 152.6 in two 21U sections: a folded steel channel open
  at six rectangular windows (`fs/cmv-sfd42u9w-base@1`), two finger walls
  (`-wall@1`), 84 moulded T fingers at one rack unit (`-finger@1`) and a
  pullable cover a section (`-cover@1`), measured on the 600 dpi page render
  of its low-resolution drawing. The material (SPCC on the product page, ABS in
  the datasheet) and the cover (none in the specification, drawn and rendered)
  are `sources-disagree` gaps; the drawing and renders are modelled. No
  capacity is published for it.
