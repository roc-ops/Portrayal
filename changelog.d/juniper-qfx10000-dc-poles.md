### Changed
- The Juniper QFX10000-PWR-DC supply (`juniper/qfx10000-pwr-dc@1`, 1.0.0 to 1.1.0) composes each of its four DC input poles as a pair of
  studs on the 5/8 in. centres the QFX10008 and QFX10016 hardware guides print for the lug, the library's two-hole-lug landing
  `juniper/mx240-dc-pole@1`, and states two DC input ports of two poles each, the guides' `rtn` and `batt`, with the nominal voltage and the
  current their power table prints and no wire size, because the guides print two. The pair is a declared stand-in: the guides show the two
  studs one behind the other along the supply's depth, and the face can only lay them side by side across the barrel it draws. The drawn
  face is unchanged. The supply now offers a power end a DC feed can land on.
- The QFX10008 (`juniper/qfx10008`, 4.0.1 to 4.1.0) and the QFX10016 (`juniper/qfx10016`, 2.0.3 to 2.1.0) each take a minor, because the
  build now publishes DC ports for them, with their locks and the drawing version line of their exported device types (16 files in NetBox and
  Nautobot); the supply's module type carries the new contract version (2 files). No port, interface or id moves. One row of the records file
  is gone and its `cap:` is 47.
