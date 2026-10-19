### Fixed
- **The U-handle on `ufispace/psu-302-ac@1` and `edgecore/eps112-psu-ac@1` no
  longer paints over the art drawn inside it** (#498). `render.py` raises a node
  with a `uhandle` to the end of the drawing, which buried the PSU-302-AC's
  `handle-grip` and the EPS112 supply's `handle-screws`. The handle is now drawn
  with `fill-rule="evenodd"` and the inner art's outline as a hole (the pattern
  `common/mpo-flange-adapter@2` uses), so the grip and the screws show. Art
  only: no position, size, id or class changed. The device lock asked for a
  patch bump on each device that seats either supply: `edgecore/eps112` 2.0.1,
  `ufispace/s9321-64e` 2.0.6, `s9321-64eo` 1.0.17, `s9610-36d` 4.0.8,
  `s9611-36d` 4.0.8, `s9710-76d` 3.0.5, `s9720-56ed` 3.0.4 and `s9725-64e` 3.0.4.
  The `EXEMPT` rows for the two components are gone from
  `test_a_raised_node_does_not_bury_its_face.py`.
