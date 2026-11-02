### Changed
- `ufispace/psu-401-dc@1` (1.3.1 to 1.4.0), `ufispace/psu-201-dc@1` (1.0.1 to 1.1.0) and `ufispace/psu-751-dc@1` (1.0.1 to 1.1.0), the
  three-terminal DC supplies of the UfiSpace S7801-54XS, S8901-54XC, S9500-30XS, S9510-28DC and S9510-30XC (401); M3000-14XC,
  S9500-22XST, S9501-18SMT and S9501-28SMT (201); and S9110-32X and S9620-54DC (751), compose their three terminal screws as parts,
  each a seat a ring lug lands on, and state one DC input port: three poles carrying the legend the vendor's installation guides
  print under the screws (`rtn` on the left, `batt` in the middle, `gnd` for the earth symbol on the right), the input current of
  the datasheets (16, 8 and 28 A) and the one cable size of the guides (14, 14 and 10 AWG). Each supply now offers a power end a DC
  feed can land on. Its terminal block is drawn as before, with a screw head at the centre of each of the three clamps. The port
  states no voltage, because the documents give a range without a nominal, and the earth pole is no conductor of a feed.
- The eleven devices that place them each take a minor, because the build now publishes a DC port for them, with their locks and
  the drawing version line of their exported device types; the three supplies' module types carry the new contract version. No
  port, interface or id moves. Three rows of the records file are gone and its `cap:` is 183.
