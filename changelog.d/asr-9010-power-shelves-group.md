### Changed
- The ASR 9010 (`cisco/asr-9010`, 1.2.3 to 2.0.0) no longer declares the group `power-shelves`: nothing was ever placed in it, the two
  shelves are drawn as the openings `shelf-0` and `shelf-1`, and the power modules that sit in them stay in `power-modules`. **A page,
  rack file or style that names the group no longer finds it in the device's published group list** (no drawn face carried it). The
  device takes a major version, with its record and the drawing version line of its exported device types; no port, interface, bay or
  placement name moves, and no pixel is drawn differently. The gap `bays-awaiting-components` now scopes the two openings instead of
  the group, and the shelf figures keep their provenance entry. Closes one structural lint finding (a group nothing joins) and its line
  in the lint baseline.
