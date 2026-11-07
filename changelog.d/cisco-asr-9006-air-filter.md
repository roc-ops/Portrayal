### Added
- `cisco/asr-9006-filter@1` (1.0.0), the Cisco ASR 9006 chassis air filter, ASR-9006-FILTER in the thermal infrastructure table of the
  ASR 9000 data sheet. The ASR 9006 right face now seats it in an `air-filter` bay, where it had an opening with nothing in it, so the
  opening no longer lints as an empty hole. Its width and height are the opening the chassis already drew and are declared estimates,
  because the one figure of the filter is a perspective drawing with no dimension lines; no depth is stated or carried.
- `cisco/asr-9006` takes a minor (3.3.4 to 3.4.0) and the drawing version line of its exported device types. No port,
  interface or id moves, and the `air-filter-position` gap stays open. One gap row, `openings-awaiting-components`, which named the
  filter as the last opening without a part, is gone.
