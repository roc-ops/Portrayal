### Changed
- `common/liquid-qd-coupler@1` 1.0.0 to 1.0.1: the valve of the quick-disconnect coupler is class
  `mechanical`, not `port`, and the part says it carries liquid and takes no cable, cord or lug,
  so the coolant valves of `celestica/ds6001` and `juniper/qfx5250-64oe-l` are no longer read as
  ports that present no interface. The built faces of the two devices carry
  `data-class="mechanical"` on those six elements, and each device takes a patch (0.1.2 to
  0.1.3) with its lock and the drawing version line of its exported device types. Nothing is
  drawn differently. Their two port rows of the records file are gone and its `cap:` is 212;
  the three rows that remain in that block now say which connector each port still needs.
