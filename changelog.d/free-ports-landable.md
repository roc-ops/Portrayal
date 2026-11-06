### Changed
- `freePorts` marks a row it lists on the left, right, top or bottom panel with
  `landable: false` and a `reason` ("... is on the left of the device, and a
  cable end can be given on the front or rear only"), the words a saved cable
  on such a slot already reads. `cable.add` takes a `view` of `front` or `rear`
  only, so a consumer can now tell the rows a cable can be given from the ones
  it cannot, without trying. A row on the front or the rear carries neither
  key and reads as it did; no row is added or removed.
- A new test takes every power, ground and other end the kit lists for each
  device in each of its configurations as the end of a cable, and holds that
  `cable.add` accepts it and no panel reports it loose, or that the row says it
  cannot be given.
