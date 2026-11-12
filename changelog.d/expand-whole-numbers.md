### Added
- A `layout.yaml` may say `whole-numbers: true` at its top level. `expand.py` then
  writes a position or size it computes as an integer when it is whole (`14`
  for `14.0`), so a layout that reproduces a hand-written device keeps that
  device's source hash. A layout without the key expands exactly as before, and
  the key is not written to `device.yaml`. No device changes, and the change
  closes no conformance rows.
