### Changed
- The CXP, CFP, CFP2 and CFP4 cages are now the panel opening each standard
  prints, as `std/sfp@1` and `std/qsfp28@1` are: the box is the opening, `d`
  the bezel to the connector, `relief.size` the interior behind it, with the
  one 1.0 collar (#802). `std/cxp@2` is SFF-8642 Rev 3.3's 23.50 x 12.10
  cut-out, 28.96 deep, with the 21.60 x 10.20 snout opening behind it;
  `std/cfp@2` the CFP MSA Mechanical Layout's 82.8 x 14.8 opening, about
  126 deep (derived from a scaled figure); `std/cfp2@2` the CFP2 Baseline
  Drawing's 14.30-high opening at the 41.50 module width, about 87.5 deep;
  `std/cfp4@2` the CFP4 Baseline Drawing's 11.30-high opening at the 22.10
  faceplate width, about 67.9 deep. The `cxp`, `cfp`, `cfp2` and `cfp4`
  entries in `spec/schemas/standards.yaml` carry the same figures and a
  `cavity`; the CXP pitch floor is SFF-8642's printed 27.00 (was 30.0, an
  estimate) and the CFP2 floor the 42.50 faceplate (was 45.0, which the
  drawing's two modules per 86.35 opening contradicted). Every card that
  composes one (fourteen Juniper MICs and MPCs, five Nokia MDAs and NT cards,
  the Edgecore AMX-3200 sled) composes the second major, each port kept on
  its centre; the seventeen devices that seat those cards take a patch. A
  seated generic CXP, CFP, CFP2 or CFP4 optic sits where it did.

### Removed
- `std/cxp@1`, the 27.0 x 10.0 x 92.0 estimate; use `std/cxp@2` (#802).
- `std/cfp@1`, the 82.0 x 13.6 faceplate-on-body envelope; use `std/cfp@2`
  (#802).
- `std/cfp2@1`, the 41.5 x 12.4 module body; use `std/cfp2@2` (#802).
- `std/cfp4@1`, the 21.5 x 9.5 module body; use `std/cfp4@2` (#802).
