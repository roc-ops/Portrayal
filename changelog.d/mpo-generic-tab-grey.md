### Changed
- `generic/qsfp-mpo@1` and `generic/qsfp-dd-mpo16@1` (1.0.2) default the pull
  tab to the neutral grey `#6f6f6f`, not beige (#773). Beige is SFF-8679's code
  for 850 nm, and an MPO face is also the face of single-mode PSM4, DR4 and DR8
  optics, so the generic drew those as multimode. A vendor wrapper states the
  colour its wavelength calls for, as it does on `generic/qsfp-lc@2`; no
  wrapper in the library composes either generic yet.
