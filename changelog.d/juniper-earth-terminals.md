### Changed
- The earthing terminal of the Juniper EX2200, EX2200-C, EX2300, EX2300-C, EX4100-F, EX4100-H and QFX5220-128C is a placed part
  and no longer panel art: two bare tapped holes a two-hole lug lands across, on the pitch of the lug the guide names. Five new
  generic parts carry it: `common/ground-hole-m5@1` and `common/ground-hole-10-32@1` (one dark hole each, the thread's nominal
  size) and the pairs `common/ground-hole-pair-5-8-m5@1`, `-5-8-10-32@1` and `-3-4-10-32@1`. The EX2300-24MP and -48MP place
  the one M4 screw the guide says is provided. `juniper/qfx5210-ground-plate@1` 1.0.0 to 1.1.0 is the same pair of bare holes,
  with the two screws drawn in its skin taken out. No guide states the spacing of an earthing terminal's holes: each device
  says that its pitch is inferred, from the lug the guide names and a figure or photograph, and keeps a gap that says so. The 22
  devices each take a minor and the QFX5210-64C a patch, with their locks and the drawing version line of their exported device
  types. The holes are drawn as before, dark and bare, at the thread's size instead of each figure's reading. The `qfx5210`
  row of the records file is gone and its `cap:` is 203.
