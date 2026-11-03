### Added
- `nokia/sr-7-dc-pole@1`, one pole of the 7750 SR-7 and 7450 ESS-7 DC PEM-3 terminal block: two studs on the 5/8 in. centres
  of the lug the guide names, a pair that one two-hole lug lands across (`stud-pair-5-8`, mate `generic/two-hole-lug-5-8@1`).
  The stud spacing is inferred from the lug, not stated by any document, and the part says so.
- The 7750 SR-e -48/-60 VDC supply (`nokia/sr-e-psu-dc@1`, 1.1.0) composes its two terminal screws and its M4 earth screw as
  seats a ring lug lands on, and states one DC input port: the left screw is the return (`rtn`) and the right one the battery
  feed (`batt`), as the guide's figures, its terminal table and its connection steps print them. The earth screw stands beside
  the block and is a ground seat outside the port. The port states the guide's #8 AWG wire size and no voltage or current: the
  guide gives a rated voltage of -48/-60 VDC and a pair of currents, 40/30 A, and no one nominal.
- The 7750 SR-7 and 7450 ESS-7 DC PEM-3 (`nokia/sr-7-pem-3@1`, 1.2.0) composes its -48 VDC and RTN poles as two
  `nokia/sr-7-dc-pole@1` and states one DC input port with the guide's 100 A and no voltage or wire size.

### Changed
- The 7750 SR-1e, SR-2e and SR-3e (0.2.0 to 0.3.0) and the 7750 SR-7 (1.0.7 to 1.1.0) each take a minor: the build now
  publishes a DC port for the supply they seat. Their locks and the drawing version line of their exported device types
  move with them, and the two modules' types carry the new contract versions. The drawings gain only the seats' small
  screw heads. Two rows of the records file are gone and its `cap:` is 152.
