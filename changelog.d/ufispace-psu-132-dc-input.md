### Changed
- `ufispace/psu-132-dc@1` (1.1.0 to 1.2.0), the DC supply of the UfiSpace S9300-32D family, composes its two terminal screws as
  parts, each a seat a ring lug lands on, and states one DC input port: two poles carrying the signs the vendor's installation
  guide prints under the two lugs (`neg` on the left, `pos` on the right) and the 40 A input current of the datasheet. The supply
  now offers a power end a DC feed can land on. Its terminal block is drawn as before, with a screw head at the centre of each
  clamp. The port states no voltage and no cable size, because the documents give a range without a nominal and name three
  different cable sizes.
- The eight devices that place it (the UfiSpace S9300-32D, S9301-32D, S9301-32DB, S9600-102XC, S9600-28DX, S9600-72XC,
  S9601-102XC and S9701-82DC) each take a minor, because the build now publishes a DC port for them, with their locks and the
  drawing version line of their exported device types; the supply's module type carries the new contract version. No port,
  interface or id moves. One row of the records file is gone and its `cap:` is 203.
