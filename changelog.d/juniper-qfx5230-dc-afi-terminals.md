### Changed
- `juniper/qfx5230-jnp-2400w-dc-afi@1` (1.0.0 to 1.1.0), the 2400 W DC supply of the Juniper QFX5230-64CD, composes its two input
  terminals as parts, each a pair of studs on 5/8 in. centres that one two-hole lug lands across, and states one DC input port with
  `rtn` and `batt` poles, the roles the QFX5230-64CD hardware guide prints for its terminals (RTN and -48V/-60V), and a rating of
  60 A, the one figure the guide's Table 21 gives for this unit. The supply now offers a power end a DC feed can land on.
  The guide draws one DC supply with a terminal block under a cover for both of its DC units, but no held figure gives the studs'
  position on the face, which pair is which, any printed mark, or a spacing for the lug of this unit. So the stud positions, the order
  of the two pairs and the 5/8 in. pitch, taken from the 3000 W sibling's lug, are estimated and the contract says so. The port states
  no voltage, because the guide gives a range.
- The QFX5230-64CD, which places it in its DC AIR IN configuration, takes a minor, because the build now publishes a DC port for it,
  with its version file and the drawing version line of its exported device types; the supply's module type carries the new contract
  version. No port, interface or id moves. One row of the records file is gone.
