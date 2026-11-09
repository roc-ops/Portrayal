### Changed
- The ASR 9906 (`cisco/asr-9906` 2.2.0) draws the rest of its rear face from Cisco's stencil master "ASR-9906 Rear":
  the two hexagon vent fields (lower left and upper right), the power tray's rear plate with its six IEC receptacles
  (A and B for each of M0 to M2) and the DC output blade housing below it, the ESD jack with its legend, eight round
  screw heads and twenty-three plus marks, and the ears' span. The receptacles are drawn as paint and no inlet part is
  placed: Cisco's Overview and Reference Guide (Figure 66, "Version 3 Rear Panel") calls them "IEC input receptacles with
  retention brackets" and no held document names the type or gives a dimension. The ESD jack is `common/esd-jack@1` in
  a new `esd-rear` cutout. Every position is read off the master (no Cisco figure dimensions the rear) and the
  chassis says which were read from pixel edges and which by eye. Still not drawn, and named in the chassis' gaps:
  the DC housing's hexagon holes, the tray's printed legends, the fabric cage's own rails and backplane. The two-hole
  ground pad stays where it was; the master draws it 52 mm higher, and moving a placed id is a major version, so it is
  recorded rather than changed. No row of the issue's tables closes.
