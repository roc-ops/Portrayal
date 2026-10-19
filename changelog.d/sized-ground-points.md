### Added
- **`common/ground-screw-m5@1`** (#918): an ISO 7045 M5 pan-head screw seen head
  on, following `common/ground-screw-m4@1`. The part is 10 mm across: a 9.5 mm
  head on an ISO 7089 M5 washer (10 across, 1.0 thick). A device places it where
  its documents name M5 screws that are not a lug pitch apart.

### Changed
- **`edgecore/dcs500` 4.0.0** (#918): its four grounding screws are
  `common/ground-screw-m5@1`, drawn at M5 instead of the nominal screw's
  about M3, on the same centres.
- **`ufispace/s9501-18smt` 4.0.0** (#918): its four grounding lugs are two
  `common/ground-stud-pair-5-8-m4@1` hosts, one per designated location, each
  centred on the two holes its own Figure 22 reads. The placements are
  `ground-screws-1` and `ground-screws-2`. It keeps its earth symbol above each
  lug, now as silkscreen marks on the case.
- **`common/ground-screw-m4@1` 1.0.1**: its provenance no longer says the screw
  is never placed alone. The eight UfiSpace devices that compose it take a
  patch for the changed part: `m3000-14xc` 4.0.1, `s9500-22xst` 3.0.1,
  `s9501-28smt` 4.0.1, `s9502-16smt` 2.0.1, `s9510-28dc` 6.0.1, `s9510-30xc`
  4.0.1, `s9511-20ct` 3.0.1 and `s9601-104bc` 4.0.1.
