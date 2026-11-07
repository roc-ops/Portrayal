### Changed
- `common/fan-module@1` 1.16.1 to 1.16.2: the captive screw on the mounting tab is class
  `latch`, as the part's handle and the MaiaEdge fan plate's thumbscrew are, so it is not read
  as a place a cord or lug lands. The built faces of `juniper/mx150` and of the three Edgecore
  devices that compose the part (`as5912-54x`, `as7326-56x`, `as7726-32x`) carry
  `data-class="latch"` on that element, and each takes a patch with its lock and the drawing
  version line of its exported device types. Nothing is drawn differently. The `mx150` row of
  the records file is gone and its `cap:` is 214.
