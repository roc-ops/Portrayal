### Added
- A position is a field (#808, docs/switch-positions-design.md). A `choice`
  field may now MOVE a skin node (`data-move-from` and a `data-move` table of
  `option: dx dy [deg]`) or SHOW one (`data-show-from` and the options listed
  in `data-show`). The build applies both, the kit's `paintFields` applies the
  same two rules at runtime and `unpaintFields` puts them back, and in 3D a
  change to such a field rebuilds the scene, because a moved node stands
  somewhere else. An option the field does not declare fails the build. A
  placement may say what each position means in `positions:`, carried into
  the drawing as `data-positions`. Lint L148 holds a position's table to its
  field's options and L149 keeps a moved node on its part; L73 counts both
  attributes as wiring. `common/dip-switch-2@1` (1.1.0) is the first user:
  `sw-1` and `sw-2`, `off` or `on`, drawn `off` as before, so the ten AurCore
  devices that place it draw as they did and take a patch.
- The 300CB08 family's alarm DIPs (`amphenol-ns/alarm-dip-8@1`, 1.1.0) are
  the second user: `sw-1` to `sw-8`, `up` or `down`, drawn up as before. The
  eleven panels that place them say in `positions:` what each switch does
  (the alarm for breaker position A1 to B8; on the nrgILS, whether a circuit
  is held on out of software control), and their `populated` and
  `with-fuses` configurations set the switch of every fitted position down,
  as the installation guide requires. Each panel takes a patch.
