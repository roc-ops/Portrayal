### Added
- `din-rails.json` is a new file in the build: the DIN rail profiles as one
  table, `spec/schemas/din-rails.yaml`, compiled by `din_rails_index.py` and
  refused when a figure names no document or a page the document does not have.
  It states one profile, `ts35x7.5` (section, slot pattern, mass per metre, the
  finishes and the slotted and unslotted stock), each figure with the maker's
  PDF and page. `din_rails_index.slot_centres` works out where the slots fall on
  a rail of a given length. Nothing reads the file yet: no device, lab or lint
  rule names a profile, so no device lock, drawing or DCIM file moves. It is new
  at `contract: 2` and does not raise it. It closes no rows.

### Changed
- `docs/din-rail-design.md` reads the figures its drawings disagreed on against
  the makers' pages: the 7.5 mm crown (27 outside, 25 inside), the G32 lip (9 and
  6 are one figure) and the 15 mm rail's depth (5.5) are not disputes, and the
  35 x 15 crown stays open.
