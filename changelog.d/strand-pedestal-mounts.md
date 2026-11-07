### Added
- **Two more mounts, `strand` and `pedestal`.** `chassis.mount` takes `strand`, a box that clamps
  to the support strand or cable of an aerial plant, and `pedestal`, one that mounts on a pedestal
  or rod, and keeps `wall`. Each exports `u_height: 0` and `is_full_depth: false` with the
  comment "Strand-mounted; not rack-mounted." or "Pedestal-mounted; not rack-mounted.", lint L125
  names both, and the Rack Builder offers them as a strand-mount or pedestal-mount device. The
  values are additive: every file valid before stays valid. No device states either value yet, so
  no export changes, and the served device schema is republished with the first device that does.
  This closes no row of the port records.
