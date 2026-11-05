### Added
- `nokia/sr-12-dc-pole@1`, one row of a terminal well of the 7750 SR-12 and 7450 ESS-12 175A DC PEM-3: two studs on the 3/4 in.
  centres of the lug the guide names, a pair that one two-hole lug lands across (`stud-pair-3-4`, mate
  `generic/two-hole-lug-3-4@1`). The stud spacing is inferred from the lug, not stated by any document, and the part says so.
- The 7750 SR-12 and 7450 ESS-12 175A DC PEM-3 (`nokia/sr-12-pem-3@1`, 1.3.0) composes the four rows of its -48 VDC and RTN
  wells as four `nokia/sr-12-dc-pole@1` and states two DC input ports, `feed-a` on the upper row of each well and `feed-b` on
  the lower, each with `batt` and `rtn` as the guide's figure prints them. The ports state no voltage, current or wire size:
  the guide gives ranges, a breaker for the whole module and two wire sizes. Which row of one well goes with which row of the
  other is not stated, and the part says so.

### Changed
- The two screws that hold the 7750 SR-7 power filter safety panel (`nokia/sr-7-psf-safety-panel@1`) and the two D-ring screws
  of the Lightspan MF-8 horizontal front cover (`nokia/mf8-horizontal-front-cover@1`) are class `fastener`, no longer `screw`:
  they hold a cover on and take no cable. Both parts take a patch (1.0.1).
- The 7750 SR-12 (2.1.0 to 2.2.0) takes a minor, because the build now publishes DC ports for the module it seats; the 7750
  SR-7 (1.1.0 to 1.1.1) and the Lightspan MF-8 shelf (2.0.1 to 2.0.2) each take a patch. Their device files, locks and the
  drawing version line of their exported device types move with them, and the PEM-3's module type carries the new contract
  version. The PEM-3 drawing gains only the studs' small screw heads. Three rows of the records file are gone and its `cap:` is
  69.
