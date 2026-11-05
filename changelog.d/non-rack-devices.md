### Added
- **A ceiling mount, and a powered device's PoE standard and draw, and the first two
  access points.** `chassis.mount` takes `ceiling`: a box that fixes to a ceiling or hangs
  below it, exported as `u_height: 0` and `is_full_depth: false` with the comment
  "Ceiling-mounted; not rack-mounted." and offered in the Rack Builder as a ceiling-mount device.
  `attrs.power` defines four keys for a device's PoE input: `poe-pd-standard` and
  `poe-pd-standard-min` (`802.3af`, `802.3at` or `802.3bt`), `poe-pd-class` (an integer from 0 to
  8, stated only where a source prints it) and `poe-pd-max-w` (a number above 0: the whole
  intake, including what the device hands on). Lint L198 relates them, and the two power-key
  lists a component refuses and the comparable facts name them. A DCIM comment reads "PoE powered
  device: 802.3at (runs on 802.3af), at most 25 W at the PD input." The new keys are additive:
  every file valid before stays valid. The ReadyLinks IPC-APWF6-POE-WP wall-plate access point and
  IPC-APWF7-POE-CL ceiling access point are modelled from their data sheets, each exporting
  `u_height: 0` and `is_full_depth: false` to NetBox and Nautobot. This closes no row of the port
  records.
- **A body with rounded plan corners and a smaller face.** `chassis.rounded` takes a corner
  `radius` and an optional `taper` (`face: front`, an `inset` and a `depth`): the body is the
  same cutting-plane solid a bevel makes, so the face drawings and the 3D viewer read it with no
  change, and it combines with `bevel`. The ceiling access point uses it, with ridges, a Wi-Fi
  mark and a slanted lamp on its face; the wall-plate access point uses `bevel` on its twelve
  edges. Additive: every file valid before stays valid.
